"""
riot_api_client.py
A robust client for interacting with the Riot Games API with proper rate limiting.
"""
import aiohttp
import asyncio
import logging
import time
import sys
from typing import Dict, Optional, Any, List, Tuple
import json
from collections import defaultdict, deque

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class RateLimitBucket:
    """
    A bucket for tracking rate limits for a specific endpoint.
    """
    def __init__(self, limit: int, duration: int):
        self.limit = limit
        self.duration = duration
        self.tokens = limit
        self.last_refill = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """
        Attempt to acquire a token from this bucket.
        
        Returns:
            bool: True if a token was acquired, False otherwise.
        """
        async with self.lock:
            self._refill()
            if self.tokens > 0:
                self.tokens -= 1
                return True
            return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time since last refill."""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed > self.duration:
            self.tokens = self.limit
            self.last_refill = now
        elif elapsed > 0:
            # Partial refill based on elapsed time
            new_tokens = int((elapsed / self.duration) * self.limit)
            if new_tokens > 0:
                self.tokens = min(self.limit, self.tokens + new_tokens)
                self.last_refill = now

class RiotAPIClient:
    """
    Client for making requests to the Riot Games API with proper rate limiting.
    """
    def __init__(self, api_key: str, region: str, platform: str, 
                 app_rate_limit: str = "20:1,100:120",
                 retry_attempts: int = 3,
                 cache_ttl: int = 60):
        """
        Initialize the API client.
        
        Args:
            api_key: Riot API key
            region: Region code (e.g., 'NA1')
            platform: Platform routing value (e.g., 'americas')
            app_rate_limit: Default application rate limit as specified by Riot
            retry_attempts: Number of retry attempts for failed requests
            cache_ttl: Time-to-live for cached responses in seconds
        """
        self.api_key = api_key
        self.region = region
        self.platform = platform
        self.retry_attempts = retry_attempts
        self.cache_ttl = cache_ttl
        
        # Parse app rate limits and create buckets
        self.app_rate_limit_buckets = []
        for limit in app_rate_limit.split(','):
            requests, seconds = map(int, limit.split(':'))
            self.app_rate_limit_buckets.append(RateLimitBucket(requests, seconds))
        
        # Method-specific rate limit buckets (populated dynamically)
        self.method_buckets = defaultdict(list)
        
        # Cache for API responses
        self.cache = {}
        
        # Session for API requests
        self.session = None

    async def initialize(self):
        """Initialize aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _wait_for_rate_limit(self, endpoint: str) -> bool:
        """
        Wait until a request can be made according to rate limits.
        
        Args:
            endpoint: The API endpoint being accessed
            
        Returns:
            bool: True if request can proceed, False if rate limited
        """
        # Check app-wide rate limits first
        for bucket in self.app_rate_limit_buckets:
            if not await bucket.acquire():
                logger.debug(f"App rate limit reached. Waiting for tokens to refill.")
                return False
        
        # Check method-specific rate limits if they exist
        if endpoint in self.method_buckets:
            for bucket in self.method_buckets[endpoint]:
                if not await bucket.acquire():
                    logger.debug(f"Method rate limit reached for {endpoint}. Waiting for tokens to refill.")
                    return False
        
        return True

    def _update_rate_limits(self, endpoint: str, headers: Dict[str, str]) -> None:
        """
        Update rate limit buckets based on API response headers.
        
        Args:
            endpoint: The API endpoint
            headers: Response headers containing rate limit information
        """
        # Parse method rate limit if present
        if 'X-Method-Rate-Limit' in headers:
            self.method_buckets[endpoint] = []
            for limit in headers['X-Method-Rate-Limit'].split(','):
                requests, seconds = map(int, limit.split(':'))
                self.method_buckets[endpoint].append(RateLimitBucket(requests, seconds))

    def _get_cache_key(self, endpoint: str, params: Dict[str, Any] = None) -> str:
        """
        Generate a cache key for the given endpoint and parameters.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            str: Cache key
        """
        if params:
            param_str = json.dumps(params, sort_keys=True)
            return f"{endpoint}:{param_str}"
        return endpoint

    def _get_cached_response(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """
        Get a cached response if available and not expired.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Optional[Dict]: Cached response or None
        """
        cache_key = self._get_cache_key(endpoint, params)
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if time.time() - entry['timestamp'] < entry['ttl']:
                logger.debug(f"Cache hit for {cache_key}")
                return entry['data']
            else:
                # Expired
                del self.cache[cache_key]
        return None

    def _cache_response(self, endpoint: str, params: Dict[str, Any], data: Dict, ttl: int = None) -> None:
        """
        Cache an API response.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            data: Response data
            ttl: Time-to-live in seconds, defaults to the client's default
        """
        cache_key = self._get_cache_key(endpoint, params)
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl or self.cache_ttl
        }

    async def request(self, endpoint: str, method: str = 'GET', 
                     params: Dict[str, Any] = None, region_override: str = None,
                     use_platform: bool = False, cache: bool = True, 
                     force_refresh: bool = False) -> Dict:
        """
        Make a request to the Riot API with rate limiting and caching.
        
        Args:
            endpoint: API endpoint (without base URL)
            method: HTTP method
            params: Query parameters
            region_override: Override the default region
            use_platform: Use the platform URL instead of the region URL
            cache: Whether to cache the response
            force_refresh: Force a refresh even if cached
            
        Returns:
            Dict: API response as JSON
        """
        await self.initialize()
        
        # Determine base URL
        base = self.platform if use_platform else (region_override or self.region)
        url = f"https://{base}.api.riotgames.com{endpoint}"
        
        # Set headers with API key
        headers = {
            'X-Riot-Token': self.api_key,
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Charset': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        
        # Check cache if enabled and not forcing refresh
        if cache and not force_refresh:
            cached = self._get_cached_response(endpoint, params)
            if cached:
                return cached
            
        # Log the request for debugging (but mask most of the API key)
        masked_key = self.api_key[:8] + "..." + self.api_key[-8:] if len(self.api_key) > 16 else "***masked***"
        logger.debug(f"Making request to: {url} with key: {masked_key}")
        
        # Wait until we can make a request
        can_proceed = await self._wait_for_rate_limit(endpoint)
        if not can_proceed:
            # If we can't proceed immediately, sleep and try again
            await asyncio.sleep(1)
            return await self.request(endpoint, method, params, region_override, use_platform, cache, force_refresh)
        
        # Make the request with retries
        for attempt in range(self.retry_attempts + 1):
            try:
                async with self.session.request(method, url, params=params, headers=headers) as response:
                    # Update rate limits based on headers
                    if 'X-Method-Rate-Limit' in response.headers:
                        self._update_rate_limits(endpoint, response.headers)
                    
                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 1))
                        logger.warning(f"Rate limited. Retrying after {retry_after} seconds.")
                        await asyncio.sleep(retry_after)
                        continue
                    elif response.status == 400:
                        logger.error(f"Bad request (400) for URL: {url}")
                        return {'status': {'status_code': 400, 'message': 'Bad request - check endpoint and parameters'}}
                    elif response.status == 403:
                        logger.error(f"Forbidden (403) for URL: {url} - Check API key permissions")
                        return {'status': {'status_code': 403, 'message': 'Forbidden - check API key permissions'}}
                    
                    # Handle other errors
                    if response.status >= 400:
                        if response.status == 404:
                            logger.warning(f"Resource not found: {url}")
                            return {'status': {'status_code': 404, 'message': 'Not found'}}
                        elif response.status >= 500:
                            if attempt < self.retry_attempts:
                                wait_time = 2 ** attempt  # Exponential backoff
                                logger.warning(f"Server error {response.status}. Retrying in {wait_time}s.")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                logger.error(f"Max retries reached for {url}. Status: {response.status}")
                                return {'status': {'status_code': response.status, 'message': 'Server error'}}
                        else:
                            logger.error(f"Request failed: {url}, Status: {response.status}")
                            return {'status': {'status_code': response.status, 'message': 'Request failed'}}
                    
                    # Parse response
                    data = await response.json()
                    
                    # Cache if enabled
                    if cache:
                        self._cache_response(endpoint, params, data)
                    
                    return data
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < self.retry_attempts:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request error: {str(e)}. Retrying in {wait_time}s.")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Max retries reached for {url}. Error: {str(e)}")
                    raise
        
        # This should never be reached due to the return statements in the loop
        return {'status': {'status_code': 500, 'message': 'Unknown error'}}

    # Convenience methods for common Riot API endpoints
    
    async def get_summoner_by_name(self, summoner_name: str, region: str = None) -> Dict:
        """Get summoner information by name."""
        endpoint = f"/lol/summoner/v4/summoners/by-name/{summoner_name}"
        return await self.request(endpoint, region_override=region)
    
    async def get_match_list(self, puuid: str, count: int = 20, start: int = 0, queue: int = None) -> List[str]:
        """Get match list for a player."""
        endpoint = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {'start': start, 'count': count}
        if queue is not None:
            params['queue'] = queue
        return await self.request(endpoint, params=params, use_platform=True)
    
    async def get_match(self, match_id: str) -> Dict:
        """Get match details."""
        endpoint = f"/lol/match/v5/matches/{match_id}"
        return await self.request(endpoint, use_platform=True)
    
    async def get_puuid_by_summoner_id(self, summoner_id: str, region: str = None) -> Optional[str]:
        """Get PUUID from summoner ID."""
        if not summoner_id:
            return None
            
        endpoint = f"/lol/summoner/v4/summoners/{summoner_id}"
        summoner_data = await self.request(endpoint, region_override=region)
        
        if 'puuid' in summoner_data:
            return summoner_data['puuid']
        return None
    
    async def get_current_game(self, summoner_id: str = None, puuid: str = None, region: str = None) -> Dict:
        """Get current game information using PUUID if available, or summoner ID."""
        # Validate that we have at least one ID
        if not puuid and not summoner_id:
            logger.warning("Neither summoner ID nor PUUID provided")
            return {'status': {'status_code': 400, 'message': 'ID required'}}
        
        # If PUUID is not provided, try to get it from summoner ID
        if not puuid and summoner_id:
            puuid = await self.get_puuid_by_summoner_id(summoner_id, region)
            if not puuid:
                logger.warning(f"Failed to get PUUID for summoner ID: {summoner_id}")
                return {'status': {'status_code': 404, 'message': 'PUUID not found'}}
        
        # Use v5 endpoint with PUUID
        endpoint = f"/lol/spectator/v5/active-games/by-summoner/{puuid}"
        logger.info(f"Making spectator request with PUUID: {puuid}")
        
        return await self.request(endpoint, region_override=region)
    
    async def get_league_entries(self, summoner_id: str, region: str = None) -> List[Dict]:
        """Get league entries for a summoner."""
        endpoint = f"/lol/league/v4/entries/by-summoner/{summoner_id}"
        return await self.request(endpoint, region_override=region)