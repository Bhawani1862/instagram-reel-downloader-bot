import instagrapi
from instagrapi.exceptions import LoginRequired, BadPassword, RecipientNotFound
import os
from config import DOWNLOAD_DIR, DOWNLOAD_TIMEOUT
from logger import logger, log_error, log_download
import re

class InstagramDownloader:
    def __init__(self):
        self.client = instagrapi.Client()
        self.download_dir = DOWNLOAD_DIR
    
    def extract_post_id(self, url):
        """Extract post ID from Instagram URL"""
        try:
            # Match various Instagram URL formats
            patterns = [
                r'instagram\.com/(?:p|reel)/([^/?]+)',
                r'instagram\.com/tv/([^/?]+)',
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
    
    def get_media_info(self, url):
        """Get media information from Instagram"""
        try:
            if not self.is_valid_instagram_url(url):
                return None, "Invalid Instagram URL"
            
            post_id = self.extract_post_id(url)
            if not post_id:
                return None, "Could not extract post ID"
            
            # Get media info
            media = self.client.media_info(post_id)
            
            return media, None
        
        except Exception as e:
            error_msg = f"Error getting media info: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def download_reel(self, url, quality='best'):
        """Download Instagram Reel"""
        try:
            post_id = self.extract_post_id(url)
            if not post_id:
                return None, "Invalid Instagram URL"
            
            # Get media info
            media = self.client.media_info(post_id)
            
            if not media.video_url:
                return None, "Could not find video in this post"
            
            # Download video
            filename = f"reel_{post_id}.mp4"
            filepath = os.path.join(self.download_dir, filename)
            
            # Get caption
            caption = media.caption_text if hasattr(media, 'caption_text') else ""
            
            return {
                'filename': filename,
                'filepath': filepath,
                'type': 'reel',
                'caption': caption,
                'username': media.user.username if hasattr(media, 'user') else 'unknown'
            }, None
        
        except Exception as e:
            error_msg = f"Error downloading reel: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def download_story(self, username):
        """Download user's latest story"""
        try:
            # Get user info
            user = self.client.user_info_by_username(username)
            
            # Get user stories
            stories = self.client.user_stories(user.pk)
            
            if not stories:
                return None, "No stories found for this user"
            
            # Download first story
            story = stories[0]
            
            if story.video_url:
                filename = f"story_{username}_{story.pk}.mp4"
            else:
                filename = f"story_{username}_{story.pk}.jpg"
            
            filepath = os.path.join(self.download_dir, filename)
            
            return {
                'filename': filename,
                'filepath': filepath,
                'type': 'story',
                'username': username
            }, None
        
        except Exception as e:
            error_msg = f"Error downloading story: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def search_user(self, username):
        """Search for user and get info"""
        try:
            user = self.client.user_info_by_username(username)
            
            return {
                'username': user.username,
                'full_name': user.full_name,
                'biography': user.biography,
                'followers': user.follower_count,
                'following': user.following_count,
                'posts': user.media_count,
                'verified': user.is_verified
            }, None
        
        except Exception as e:
            error_msg = f"User not found or profile is private: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

instagram = InstagramDownloader()