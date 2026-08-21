import os
import shutil
from config import DOWNLOAD_DIR
from logger import logger

class FileHandler:
    def __init__(self):
        self.download_dir = DOWNLOAD_DIR
    
    def get_file_size(self, filepath):
        """Get file size in MB"""
        try:
            size_bytes = os.path.getsize(filepath)
            size_mb = size_bytes / (1024 * 1024)
            return round(size_mb, 2)
        except Exception as e:
            logger.error(f"Error getting file size: {str(e)}")
            return 0
    
    def file_exists(self, filename):
        """Check if file exists"""
        filepath = os.path.join(self.download_dir, filename)
        return os.path.exists(filepath)
    
    def delete_file(self, filename):
        """Delete a file"""
        try:
            filepath = os.path.join(self.download_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted file: {filename}")
                return True
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
        return False
    
    def cleanup_old_files(self, days=7):
        """Delete files older than specified days"""
        import time
        from datetime import datetime, timedelta
        
        try:
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            
            for filename in os.listdir(self.download_dir):
                filepath = os.path.join(self.download_dir, filename)
                
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        logger.info(f"Cleaned up old file: {filename}")
        
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")
    
    def list_downloads(self):
        """List all downloaded files"""
        try:
            files = os.listdir(self.download_dir)
            return files
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []
    
    def get_storage_info(self):
        """Get storage usage info"""
        try:
            total_size = 0
            file_count = 0
            
            for filename in os.listdir(self.download_dir):
                filepath = os.path.join(self.download_dir, filename)
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)
                    file_count += 1
            
            total_size_mb = total_size / (1024 * 1024)
            return {
                'total_size_mb': round(total_size_mb, 2),
                'file_count': file_count
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {str(e)}")
            return {'total_size_mb': 0, 'file_count': 0}

file_handler = FileHandler()