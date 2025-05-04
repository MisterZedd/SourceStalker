import sqlite3
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Connect to the SQLite database (this will create the database file if it doesn't exist)
conn = sqlite3.connect('rank_tracker.db')

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

# Create a table to store rank data
cursor.execute('''
CREATE TABLE IF NOT EXISTS rank_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT UNIQUE,
    queue_type TEXT,
    tier TEXT NOT NULL,
    rank TEXT NOT NULL,
    lp INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
''')

# Commit the transaction and close the connection
conn.commit()
conn.close()

logger.info("Database and table created successfully!")
