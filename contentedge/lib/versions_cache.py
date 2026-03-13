import os
import json
import sqlite3
from datetime import datetime, timedelta
from .cache_manager import CacheManager

class VersionsCache(CacheManager):
    def __init__(self, cache_dir, prefix, md5_checksum, expire_cache_days=30):
        # Check and remove old cache files with same prefix but different checksum
        for file in os.listdir(cache_dir):
            if file.startswith(f"{prefix}_") and file.endswith(".db"):
                old_cache_file = os.path.join(cache_dir, file)
                if f"{prefix}_{md5_checksum}.db" != file:
                    try:
                        os.remove(old_cache_file)
                    except OSError:
                        pass  # Ignore errors if file cannot be deleted

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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                cc TEXT,
                version TEXT,
                value TEXT,
                PRIMARY KEY (cc, version)
            )
        ''')

        self.cursor = cursor
        self.conn = conn
        self.expire_cache_days = expire_cache_days

    def get(self, key):
        """
        Gets a value from cache using composite key (cc_version)
        Args:
            key (str): Composite key in format 'cc_version'
        Returns:
            The stored value or None if not found
        """
        try:
            cc, version = key.split('_', 1)
            self.cursor.execute('SELECT value FROM cache WHERE cc = ? AND version = ?', (cc, version))
            result = self.cursor.fetchone()

            if result:
                try:
                    # Verify if string is valid JSON
                    value = result[0]
                    if isinstance(value, str) and value.strip():
                        if (value.startswith('{') and value.endswith('}')) or \
                           (value.startswith('[') and value.endswith(']')):
                            return json.loads(value)
                    return value  # Return as-is if not JSON
                except json.JSONDecodeError:
                    return result[0]  # Return original string if JSON parsing fails
            return None
        except Exception as e:
            return None

    def set(self, key, value):
        """
        Sets a value in cache using composite key (cc_version)
        Args:
            key (str): Composite key in format 'cc_version'
            value: Value to store
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cc, version = key.split('_', 1)
            self.cursor.execute('INSERT OR REPLACE INTO cache (cc, version, value) VALUES (?, ?, ?)', 
                              (cc, version, value))
            self.conn.commit()
            return True
        except Exception as e:
            return False
        
    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def retrieve_versions(self, cc, version_from, version_to):
        """
        Retrieves report versions from cache within the specified date range.
        
        Args:
            cc (str): Content class identifier
            version_from (str): Start date in format 'yyyymmddHHMMSS'
            version_to (str): End date in format 'yyyymmddHHMMSS'
        
        Returns:
            dict: Dictionary with version_key:object_id pairs for versions within range
        """
        try:
            query = '''
                SELECT cc, version, value 
                FROM cache 
                WHERE cc = ? 
                AND version >= ? 
                AND version <= ?
                ORDER BY version DESC
            '''
            self.cursor.execute(query, (cc, version_from, version_to))
            results = self.cursor.fetchall()
            
            versions = {}
            for cc, version, value in results:
                key = f"{cc}_{version}"
                versions[key] = value
                
            return versions
            
        except Exception as e:
            return {}
