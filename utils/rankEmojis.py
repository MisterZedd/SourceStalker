RANK_EMOJI_MAPPING = {
    'IRON': '<:iron:1284608066456785006>',
    'BRONZE': '<:bronze:1284608075579392081>',
    'SILVER': '<:silver:1284608087323574282>',
    'GOLD': '<:gold:1284608093887533119>',
    'PLATINUM': '<:platinum:1284608101382623275>',
    'EMERALD': '<:Emerald:1316528052494274740>',
    'DIAMOND': '<:diamond:1284608108546494604>',
    'MASTER': '<:master:1284608116922519645>',
    'GRANDMASTER': '<:grandmaster:1284608123524616212>',
    'CHALLENGER': '<:challenger:1284608131212640276>'
}

# Function to get the emoji for a specific rank
def get_rank_emoji(tier):
    return RANK_EMOJI_MAPPING.get(tier.upper(), '')  # Fallback to an empty string if no match
