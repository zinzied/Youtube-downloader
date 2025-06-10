import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import os

class DownloadHistory:
    def __init__(self):
        self.db_dir = Path.home() / '.youtube_downloader'
        self.db_path = self.db_dir / 'history.db'
        self.ensure_db_dir()
        self.init_database()
    
    def ensure_db_dir(self):
        """Create database directory if it doesn't exist"""
        self.db_dir.mkdir(exist_ok=True)
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    format TEXT NOT NULL,
                    quality TEXT,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    duration TEXT,
                    thumbnail_url TEXT,
                    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'completed',
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_url TEXT NOT NULL,
                    playlist_title TEXT NOT NULL,
                    total_videos INTEGER,
                    downloaded_videos INTEGER DEFAULT 0,
                    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'in_progress'
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS playlist_videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER,
                    download_id INTEGER,
                    video_index INTEGER,
                    FOREIGN KEY (playlist_id) REFERENCES playlists (id),
                    FOREIGN KEY (download_id) REFERENCES downloads (id)
                )
            ''')
            
            conn.commit()
    
    def add_download(self, url: str, title: str, format: str, quality: str, 
                    file_path: str, file_size: int = None, duration: str = None,
                    thumbnail_url: str = None, metadata: dict = None) -> int:
        """Add a download record to the history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO downloads 
                (url, title, format, quality, file_path, file_size, duration, thumbnail_url, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (url, title, format, quality, file_path, file_size, duration, 
                  thumbnail_url, json.dumps(metadata) if metadata else None))
            conn.commit()
            return cursor.lastrowid
    
    def add_playlist(self, playlist_url: str, playlist_title: str, total_videos: int) -> int:
        """Add a playlist record to the history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO playlists (playlist_url, playlist_title, total_videos)
                VALUES (?, ?, ?)
            ''', (playlist_url, playlist_title, total_videos))
            conn.commit()
            return cursor.lastrowid
    
    def link_playlist_video(self, playlist_id: int, download_id: int, video_index: int):
        """Link a downloaded video to a playlist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO playlist_videos (playlist_id, download_id, video_index)
                VALUES (?, ?, ?)
            ''', (playlist_id, download_id, video_index))
            conn.commit()
    
    def update_playlist_progress(self, playlist_id: int, downloaded_count: int):
        """Update playlist download progress"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE playlists 
                SET downloaded_videos = ?, 
                    status = CASE WHEN downloaded_videos >= total_videos THEN 'completed' ELSE 'in_progress' END
                WHERE id = ?
            ''', (downloaded_count, playlist_id))
            conn.commit()
    
    def get_downloads(self, limit: int = 100, offset: int = 0, 
                     search_term: str = None, format_filter: str = None) -> List[Dict]:
        """Get download history with optional filtering"""
        query = '''
            SELECT id, url, title, format, quality, file_path, file_size, 
                   duration, thumbnail_url, download_date, status, metadata
            FROM downloads
        '''
        params = []
        conditions = []
        
        if search_term:
            conditions.append("title LIKE ?")
            params.append(f"%{search_term}%")
        
        if format_filter:
            conditions.append("format = ?")
            params.append(format_filter)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY download_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            downloads = []
            for row in rows:
                download = dict(row)
                if download['metadata']:
                    download['metadata'] = json.loads(download['metadata'])
                downloads.append(download)
            
            return downloads
    
    def get_playlists(self, limit: int = 50) -> List[Dict]:
        """Get playlist history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM playlists 
                ORDER BY download_date DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_download(self, download_id: int) -> bool:
        """Delete a download record"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('DELETE FROM downloads WHERE id = ?', (download_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_history(self):
        """Clear all download history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM downloads')
            conn.execute('DELETE FROM playlists')
            conn.execute('DELETE FROM playlist_videos')
            conn.commit()
    
    def get_statistics(self) -> Dict:
        """Get download statistics"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total downloads
            cursor = conn.execute('SELECT COUNT(*) FROM downloads')
            stats['total_downloads'] = cursor.fetchone()[0]
            
            # Downloads by format
            cursor = conn.execute('''
                SELECT format, COUNT(*) as count 
                FROM downloads 
                GROUP BY format
            ''')
            stats['by_format'] = dict(cursor.fetchall())
            
            # Total file size
            cursor = conn.execute('SELECT SUM(file_size) FROM downloads WHERE file_size IS NOT NULL')
            total_size = cursor.fetchone()[0]
            stats['total_size'] = total_size if total_size else 0
            
            # Recent downloads (last 7 days)
            cursor = conn.execute('''
                SELECT COUNT(*) FROM downloads 
                WHERE download_date >= datetime('now', '-7 days')
            ''')
            stats['recent_downloads'] = cursor.fetchone()[0]
            
            return stats
    
    def file_exists(self, file_path: str) -> bool:
        """Check if downloaded file still exists"""
        return os.path.exists(file_path)

# Global history instance
history = DownloadHistory()
