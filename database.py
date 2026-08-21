import sqlite3
from datetime import datetime
from config import DB_PATH
import os

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create downloads table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                url TEXT,
                post_type TEXT,
                filename TEXT,
                file_size INTEGER,
                quality TEXT,
                status TEXT,
                downloaded_at TIMESTAMP,
                caption TEXT
            )
        ''')
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                total_downloads INTEGER DEFAULT 0,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, first_name):
        """Add or update user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, datetime.now(), datetime.now()))
        
        conn.commit()
        conn.close()
    
    def log_download(self, user_id, url, post_type, filename, file_size, quality, caption):
        """Log a download"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO downloads
            (user_id, url, post_type, filename, file_size, quality, status, downloaded_at, caption)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, url, post_type, filename, file_size, quality, 'success', datetime.now(), caption))
        
        # Update user's total downloads
        cursor.execute('''
            UPDATE users SET total_downloads = total_downloads + 1
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    def get_user_history(self, user_id, limit=10):
        """Get user's download history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT filename, url, post_type, downloaded_at, caption
            FROM downloads
            WHERE user_id = ?
            ORDER BY downloaded_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_user_stats(self, user_id):
        """Get user statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT total_downloads, first_seen, last_seen
            FROM users
            WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result

db = Database()