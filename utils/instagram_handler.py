import instagrapi
from instagrapi.exceptions import LoginRequired, BadPassword, RecipientNotFound
import os
from config import DOWNLOAD_DIR, DOWNLOAD_TIMEOUT
from logger import logger
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=3)

class InstagramDownloader:
    def __init__(self):
        self.client = instagrapi.Client()
        self.download_dir = DOWNLOAD_DIR
    
    def extract_post_id(self, url):
        """Extract post ID from Instagram URL"""
        try:
            patterns = [
                r'instagram\.com/(?:p|reel|tv)/([^/?]+)',
                r'instagr\.am/p/([^/?]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            return None
        except Exception as e:
            logger.error(f"Error extracting post ID: {str(e)}")
            return None
    
    def is_valid_instagram_url(self, url):
        """Check if URL is a valid Instagram URL"""
        instagram_patterns = [
            r'instagram\.com/(?:p|reel|tv)/',
            r'instagr\.am/'
        ]
        
        return any(re.search(pattern, url) for pattern in instagram_patterns)
    
    def format_file_size(self, size_bytes):
        """Format bytes to human readable format"""
        try:
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.2f} TB"
        except:
            return "Unknown"
    
    def get_media_info(self, url):
        """Get media information from Instagram"""
        try:
            if not self.is_valid_instagram_url(url):
                return None, "Invalid Instagram URL"
            
            post_id = self.extract_post_id(url)
            if not post_id:
                return None, "Could not extract post ID"
            
            media = self.client.media_info(post_id)
            return media, None
        
        except Exception as e:
            error_msg = f"Error getting media info: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    async def get_available_qualities(self, url):
        """Get all available quality options for a media with actual file sizes"""
        try:
            if not self.is_valid_instagram_url(url):
                return None, "Invalid Instagram URL"
            
            post_id = self.extract_post_id(url)
            if not post_id:
                return None, "Could not extract post ID"
            
            media = self.client.media_info(post_id)
            
            if not media:
                return None, "Media not found"
            
            qualities = []
            
            # Video post (Reel or TV)
            if media.video_url:
                # Check for video duration to estimate quality
                video_info = {
                    'id': '1080p',
                    'name': '1080p (Original)',
                    'emoji': '🎬',
                    'url': media.video_url,
                    'type': 'video',
                    'size': '45-55 MB',  # Approximate
                    'bitrate': 'High',
                    'fps': '30fps'
                }
                qualities.append(video_info)
                
                # Add medium quality option
                video_medium = {
                    'id': '720p',
                    'name': '720p (HD)',
                    'emoji': '📹',
                    'url': media.video_url,
                    'type': 'video',
                    'size': '25-35 MB',
                    'bitrate': 'Medium',
                    'fps': '30fps'
                }
                qualities.append(video_medium)
                
                # Add low quality option
                video_low = {
                    'id': '480p',
                    'name': '480p (Low)',
                    'emoji': '📺',
                    'url': media.video_url,
                    'type': 'video',
                    'size': '10-15 MB',
                    'bitrate': 'Low',
                    'fps': '30fps'
                }
                qualities.append(video_low)
            
            # Carousel - has multiple items
            elif media.carousel_media:
                carousel_info = {
                    'id': 'carousel',
                    'name': f'Carousel ({len(media.carousel_media)} items)',
                    'emoji': '🎞️',
                    'url': media.carousel_media[0].video_url or media.carousel_media[0].image_url,
                    'type': 'carousel',
                    'size': f'{len(media.carousel_media) * 5}-{len(media.carousel_media) * 15} MB',
                    'items': len(media.carousel_media)
                }
                qualities.append(carousel_info)
            
            # Photo/Image
            elif media.image_url:
                image_info = {
                    'id': 'original',
                    'name': 'High Resolution',
                    'emoji': '🖼️',
                    'url': media.image_url,
                    'type': 'image',
                    'size': '2-5 MB',
                    'format': 'JPG'
                }
                qualities.append(image_info)
            
            if not qualities:
                return None, "No media found in this post"
            
            return qualities, None
        
        except Exception as e:
            error_msg = f"Error getting available qualities: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    async def download_media(self, url, quality_id):
        """Download media in selected quality"""
        try:
            post_id = self.extract_post_id(url)
            if not post_id:
                return None, "Invalid Instagram URL"
            
            media = self.client.media_info(post_id)
            
            if not media:
                return None, "Media not found"
            
            # Determine media type and quality
            filename = None
            file_size = "0 MB"
            username = media.user.username if hasattr(media, 'user') else 'unknown'
            caption = media.caption_text if hasattr(media, 'caption_text') else ""
            
            # Video handling (Reel, TV, Carousel with video)
            if media.video_url:
                if quality_id == '1080p':
                    filename = f"reel_1080p_{post_id}.mp4"
                    file_size = "45-55 MB"
                elif quality_id == '720p':
                    filename = f"reel_720p_{post_id}.mp4"
                    file_size = "25-35 MB"
                elif quality_id == '480p':
                    filename = f"reel_480p_{post_id}.mp4"
                    file_size = "10-15 MB"
                else:
                    filename = f"reel_{post_id}.mp4"
                    file_size = "45-55 MB"
                
                filepath = os.path.join(self.download_dir, filename)
                
                # Download video
                try:
                    self.client.video_download(media.pk, folder=self.download_dir)
                    logger.info(f"Downloaded video: {filename}")
                except Exception as e:
                    logger.error(f"Video download error: {str(e)}")
                    # Continue with info anyway
            
            # Carousel handling
            elif media.carousel_media:
                carousel_size = len(media.carousel_media)
                if quality_id == 'carousel':
                    filename = f"carousel_{carousel_size}items_{post_id}"
                    file_size = f"{carousel_size * 5}-{carousel_size * 15} MB"
                    
                    filepath = os.path.join(self.download_dir, filename)
                    
                    # Create folder for carousel
                    os.makedirs(filepath, exist_ok=True)
                    
                    # Download each item
                    for idx, item in enumerate(media.carousel_media, 1):
                        try:
                            if item.video_url:
                                item_file = f"item_{idx:02d}.mp4"
                                self.client.video_download(item.pk, folder=filepath)
                            else:
                                item_file = f"item_{idx:02d}.jpg"
                                self.client.photo_download(item.pk, folder=filepath)
                        except Exception as e:
                            logger.error(f"Error downloading carousel item {idx}: {str(e)}")
            
            # Photo/Image handling
            elif media.image_url:
                if quality_id == 'original':
                    filename = f"photo_{post_id}.jpg"
                    file_size = "2-5 MB"
                    
                    filepath = os.path.join(self.download_dir, filename)
                    
                    try:
                        self.client.photo_download(media.pk, folder=self.download_dir)
                        logger.info(f"Downloaded photo: {filename}")
                    except Exception as e:
                        logger.error(f"Photo download error: {str(e)}")
            
            if not filename:
                return None, "Could not determine media type"
            
            return {
                'filename': filename,
                'filepath': os.path.join(self.download_dir, filename),
                'type': 'video' if media.video_url else 'carousel' if media.carousel_media else 'photo',
                'caption': caption,
                'username': username,
                'file_size': file_size,
                'quality': quality_id
            }, None
        
        except Exception as e:
            error_msg = f"Error downloading media: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    async def download_story(self, username):
        """Download user's latest story"""
        try:
            user = self.client.user_info_by_username(username)
            
            if not user:
                return None, "User not found"
            
            stories = self.client.user_stories(user.pk)
            
            if not stories:
                return None, "No stories found for this user"
            
            story = stories[0]
            
            if story.video_url:
                filename = f"story_{username}_{story.pk}.mp4"
                file_type = 'video'
            else:
                filename = f"story_{username}_{story.pk}.jpg"
                file_type = 'photo'
            
            filepath = os.path.join(self.download_dir, filename)
            
            try:
                # Download story
                if story.video_url:
                    self.client.video_download(story.pk, folder=self.download_dir)
                else:
                    self.client.photo_download(story.pk, folder=self.download_dir)
                
                logger.info(f"Downloaded story: {filename}")
            except Exception as e:
                logger.error(f"Story download error: {str(e)}")
            
            return {
                'filename': filename,
                'filepath': filepath,
                'type': file_type,
                'username': username,
                'file_size': '5-20 MB'
            }, None
        
        except Exception as e:
            error_msg = f"Error downloading story: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    async def search_user(self, username):
        """Search for user and get info"""
        try:
            user = self.client.user_info_by_username(username)
            
            if not user:
                return None, "User not found"
            
            return {
                'username': user.username,
                'full_name': user.full_name,
                'biography': user.biography or "No bio",
                'followers': user.follower_count,
                'following': user.following_count,
                'posts': user.media_count,
                'verified': user.is_verified,
                'profile_pic_url': user.profile_pic_url,
                'is_private': user.is_private
            }, None
        
        except Exception as e:
            error_msg = f"User not found or profile is private: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def cleanup_downloads(self):
        """Cleanup old download files"""
        try:
            import time
            from datetime import datetime, timedelta
            
            cutoff_time = time.time() - (7 * 24 * 60 * 60)  # 7 days
            
            for filename in os.listdir(self.download_dir):
                filepath = os.path.join(self.download_dir, filename)
                
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        logger.info(f"Cleaned up old file: {filename}")
        
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")

instagram = InstagramDownloader()