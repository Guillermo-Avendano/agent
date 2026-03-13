import os
import json
import sqlite3
from datetime import datetime, timedelta
from rocketcontent.cache_manager import CacheManager

class BaseCache(CacheManager):
    def __init__(self, cache_dir, prefix, md5_checksum, expire_cache_days=30):
        # Check and remove old cache files with same prefix but different checksum
        for file in os.listdir(cache_dir):
            if file.startswith(f"{prefix}_") and file.endswith(".db"):
                old_cache_file = os.path.join(cache_dir, file)
                if f"{prefix}_{md5_checksum}.db" != file:
                    try:
                        os.remove(old_cache_file)
                    except OSError:
                        pass

        self.cache_file = os.path.join(cache_dir, f"{prefix}_{md5_checksum}.db")
        
        # Check if cache file is older than expire_cache_days
        if os.path.exists(self.cache_file):
            file_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file))
            if datetime.now() - file_time > timedelta(days=expire_cache_days):
                try:
                    os.remove(self.cache_file)
                except OSError:
                    pass
                
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()

        cursor.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)')

        self.cursor = cursor
        self.conn = conn
        self.expire_cache_days = expire_cache_days

    def get(self, key):
        self.cursor.execute('SELECT value FROM cache WHERE key = ?', (key,))
        result = self.cursor.fetchone()

        if result:
            try:
                value = result[0]
                if isinstance(value, str) and value.strip():
                    if (value.startswith('{') and value.endswith('}')) or \
                       (value.startswith('[') and value.endswith(']')):
                        return json.loads(value)
                return value
            except json.JSONDecodeError:
                return result[0]
        return None

    def getID(self, key):
        self.cursor.execute('SELECT value FROM cache WHERE key = ?', (key,))
        result = self.cursor.fetchone()
        object_id = None
        if result:
            try:
                cached_data = result[0]
                if cached_data:
                    json_data = json.loads(cached_data)
                    object_id = json_data["data"]["objectId"]
                return object_id
            except json.JSONDecodeError:
                return None
        return None

    def set(self, key, value):
        try:
            self.cursor.execute('INSERT OR REPLACE INTO cache VALUES (?, ?)', (key, value))
            self.conn.commit()
            return True
        except Exception:
            return False

    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass