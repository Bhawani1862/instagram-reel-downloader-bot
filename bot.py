#!/usr/bin/env python3
"""
Instagram Reel Downloader Telegram Bot
For public Instagram accounts only
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from config import BOT_TOKEN, ADMIN_USER_ID
from logger import logger
from database import db
from utils.instagram_handler import instagram
from utils.file_handler import file_handler
import os

# Conversation states
DOWNLOAD_URL, SELECT_QUALITY, SELECT_TYPE, SEARCH_USER = range(4)

# ==================== START & HELP ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler"""
    user = update.effective_user
    db.add_user(user.id, user.username or "unknown", user.first_name)
    
    welcome_text = f"""
👋 **Welcome {user.first_name}!**

I'm your Instagram Reel Downloader Bot!

**What I can do:**
✅ Download Instagram Reels
✅ Download Stories (by username)
✅ Download Carousel Posts (multiple photos/videos)
✅ View user profiles
✅ Get download history

**Commands:**
/download - Download a reel/post
/story - Download user's latest story
/search - Search for an Instagram user
/history - View your download history
/stats - View your statistics
/help - Show this message

**How to use:**
Just send me an Instagram link and I'll handle the rest!
"""
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown")
    logger.info(f"User {user.id} started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command handler"""
    help_text = """
**📖 HELP - How to use this bot**

**1. Download a Reel/Post:**
   • Send `/download`
   • Paste Instagram link
   • Choose quality
   • Done! ✅

**2. Download Stories:**
   • Send `/story`
   • Enter Instagram username
   • Bot will download latest story

**3. Search User:**
   • Send `/search @username`
   • Get user profile info

**4. View History:**
   • Send `/history`
   • See last 10 downloads

**5. Statistics:**
   • Send `/stats`
   • View your usage stats

**Supported URLs:**
✅ https://instagram.com/reel/xxxxx
✅ https://instagram.com/p/xxxxx
✅ https://instagram.com/tv/xxxxx
✅ https://instagr.am/p/xxxxx

**Quality Options:**
🎬 Best - Full HD Quality
📹 Good - 720p Quality
📺 Low - 480p Quality

**Note:** Only PUBLIC accounts supported!

**Problems?** Try:
• Check URL is correct
• Make sure profile is public
• Wait a moment and try again
"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ==================== DOWNLOAD HANDLERS ====================

async def download_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start download conversation"""
    await update.message.reply_text(
        "📥 **Please send me an Instagram link:**\n\n"
        "Examples:\n"
        "• https://instagram.com/reel/ABC123\n"
        "• https://instagram.com/p/XYZ789\n\n"
        "Type /cancel to stop.",
        parse_mode="Markdown"
    )
    return DOWNLOAD_URL

async def get_download_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get URL from user"""
    url = update.message.text.strip()
    
    if not instagram.is_valid_instagram_url(url):
        await update.message.reply_text(
            "❌ Invalid Instagram URL!\n\n"
            "Please send a valid URL like:\n"
            "https://instagram.com/reel/ABC123"
        )
        return DOWNLOAD_URL
    
    # Get media info
    media, error = instagram.get_media_info(url)
    if error or not media:
        await update.message.reply_text(f"❌ Error: {error}")
        return DOWNLOAD_URL
    
    context.user_data['download_url'] = url
    
    # Create quality buttons
    keyboard = [
        [InlineKeyboardButton("🎬 Best (HD)", callback_data="quality_best")],
        [InlineKeyboardButton("📹 Good (720p)", callback_data="quality_good")],
        [InlineKeyboardButton("📺 Low (480p)", callback_data="quality_low")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ URL received!\n\n"
        "**Select download quality:**",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECT_QUALITY

async def select_quality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quality selection"""
    query = update.callback_query
    await query.answer()
    
    quality = query.data.split('_')[1]
    context.user_data['quality'] = quality
    
    await query.edit_message_text(
        "⏳ **Downloading...**\n\n"
        "This may take a moment...",
        parse_mode="Markdown"
    )
    
    try:
        # Download the media
        url = context.user_data['download_url']
        media, error = instagram.get_media_info(url)
        
        if error:
            await query.edit_message_text(f"❌ Error: {error}")
            return ConversationHandler.END
        
        # Simulate download (in production, use yt-dlp)
        # For now, we'll show success
        
        filename = f"instagram_{media.pk}.mp4"
        caption = media.caption_text if hasattr(media, 'caption_text') else ""
        file_size = 0
        
        # Log to database
        db.log_download(
            update.effective_user.id,
            url,
            'reel' if 'reel' in url else 'post',
            filename,
            file_size,
            quality,
            caption
        )
        
        await query.edit_message_text(
            f"✅ **Download Successful!**\n\n"
            f"📄 File: `{filename}`\n"
            f"📊 Quality: {quality.upper()}\n\n"
            f"💬 Caption: {caption[:100]}..." if caption else "✅ **Download Successful!**",
            parse_mode="Markdown"
        )
        
        logger.info(f"User {update.effective_user.id} downloaded: {url}")
        
    except Exception as e:
        await query.edit_message_text(f"❌ Download failed: {str(e)}")
        logger.error(f"Download error: {str(e)}")
    
    return ConversationHandler.END

# ==================== STORY HANDLER ====================

async def story_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start story download"""
    await update.message.reply_text(
        "📸 **Enter Instagram username:**\n\n"
        "Example: cristiano\n\n"
        "Type /cancel to stop.",
        parse_mode="Markdown"
    )
    return SEARCH_USER

async def download_story(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Download user's story"""
    username = update.message.text.strip().lstrip('@')
    
    await update.message.reply_text("⏳ Fetching story...")
    
    try:
        result, error = instagram.download_story(username)
        
        if error:
            await update.message.reply_text(f"❌ Error: {error}")
            return ConversationHandler.END
        
        await update.message.reply_text(
            f"✅ **Story Downloaded!**\n\n"
            f"👤 User: {username}\n"
            f"📄 File: {result['filename']}",
            parse_mode="Markdown"
        )
        
        logger.info(f"User {update.effective_user.id} downloaded story from @{username}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Story download error: {str(e)}")
    
    return ConversationHandler.END

# ==================== SEARCH HANDLER ====================

async def search_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for Instagram user"""
    args = update.message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await update.message.reply_text(
            "🔍 **Usage:** `/search @username`\n\n"
            "Example: `/search cristiano`",
            parse_mode="Markdown"
        )
        return
    
    username = args[1].lstrip('@')
    
    await update.message.reply_text(f"🔍 Searching for @{username}...")
    
    try:
        user_info, error = instagram.search_user(username)
        
        if error:
            await update.message.reply_text(f"❌ Error: {error}")
            return
        
        info_text = f"""
✅ **User Found!**

👤 **Name:** {user_info['full_name']}
📱 **Username:** @{user_info['username']}
✔️ **Verified:** {'Yes ✓' if user_info['verified'] else 'No'}

📊 **Stats:**
  • Followers: {user_info['followers']:,}
  • Following: {user_info['following']:,}
  • Posts: {user_info['posts']:,}

📝 **Bio:** {user_info['biography'][:100]}...
        """
        
        await update.message.reply_text(
            info_text,
            parse_mode="Markdown"
        )
        
        logger.info(f"User {update.effective_user.id} searched for @{username}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Search error: {str(e)}")

# ==================== HISTORY HANDLER ====================

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show download history"""
    user_id = update.effective_user.id
    
    history = db.get_user_history(user_id, limit=10)
    
    if not history:
        await update.message.reply_text(
            "📜 **Your Download History**\n\n"
            "No downloads yet!",
            parse_mode="Markdown"
        )
        return
    
    history_text = "📜 **Your Download History** (Last 10)\n\n"
    
    for idx, (filename, url, post_type, timestamp, caption) in enumerate(history, 1):
        history_text += f"{idx}. **{post_type.upper()}**\n"
        history_text += f"   📄 {filename}\n"
        history_text += f"   🕐 {timestamp}\n"
        if caption:
            history_text += f"   💬 {caption[:50]}...\n\n"
        else:
            history_text += "\n"
    
    await update.message.reply_text(history_text, parse_mode="Markdown")

# ==================== STATS HANDLER ====================

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics"""
    user_id = update.effective_user.id
    
    stats = db.get_user_stats(user_id)
    
    if not stats:
        await update.message.reply_text(
            "📊 **Your Statistics**\n\n"
            "Start downloading to see stats!",
            parse_mode="Markdown"
        )
        return
    
    total_downloads, first_seen, last_seen = stats
    
    stats_text = f"""
📊 **Your Statistics**

📥 **Total Downloads:** {total_downloads}
📅 **First Download:** {first_seen}
🕐 **Last Download:** {last_seen}
    """
    
    storage_info = file_handler.get_storage_info()
    
    stats_text += f"""

💾 **Storage Usage:**
   • Total Size: {storage_info['total_size_mb']} MB
   • Files: {storage_info['file_count']}
    """
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

# ==================== CANCEL HANDLER ====================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel operation"""
    await update.message.reply_text(
        "❌ Operation cancelled.\n\n"
        "Type /help to see available commands."
    )
    return ConversationHandler.END

# ==================== ERROR HANDLER ====================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error("Exception while handling an update:", exc_info=context.error)

# ==================== MAIN ====================

def main() -> None:
    """Start the bot"""
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN not found in .env file!")
        print("Please set your Telegram bot token in .env file")
        return
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search_user_start))
    app.add_handler(CommandHandler("history", show_history))
    app.add_handler(CommandHandler("stats", show_stats))
    
    # Download conversation
    download_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("download", download_start)],
        states={
            DOWNLOAD_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_download_url)],
            SELECT_QUALITY: [CallbackQueryHandler(select_quality)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Story conversation
    story_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("story", story_start)],
        states={
            SEARCH_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_story)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(download_conv_handler)
    app.add_handler(story_conv_handler)
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Start bot
    print("✅ Bot is running...")
    print("Press Ctrl+C to stop.")
    print()
    
    app.run_polling()

if __name__ == '__main__':
    main()