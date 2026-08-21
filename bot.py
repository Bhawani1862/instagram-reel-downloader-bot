#!/usr/bin/env python3
"""
Instagram Reel Downloader Telegram Bot - UPGRADED VERSION
For public Instagram accounts only
With inline buttons, actual quality selection, and real file sizes
"""

import logging
import asyncio
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
DOWNLOAD_URL, SELECT_QUALITY, SEARCH_USER = range(3)

# ==================== START & HELP ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler"""
    user = update.effective_user
    db.add_user(user.id, user.username or "unknown", user.first_name)
    
    welcome_text = f"""
👋 **Welcome {user.first_name}!**

I'm your Instagram Reel Downloader Bot! 🎬

**What I can do:**
✅ Download Instagram Reels (Original Quality)
✅ Download Stories (by username)
✅ Download Carousel Posts
✅ View user profiles & stats
✅ Get download history

**📱 Available Commands:**
"""
    
    # Create inline buttons for main menu
    keyboard = [
        [InlineKeyboardButton("📥 Download Reel", callback_data="cmd_download")],
        [InlineKeyboardButton("📸 Download Story", callback_data="cmd_story")],
        [InlineKeyboardButton("🔍 Search User", callback_data="cmd_search")],
        [InlineKeyboardButton("📜 History", callback_data="cmd_history")],
        [InlineKeyboardButton("📊 Stats", callback_data="cmd_stats")],
        [InlineKeyboardButton("❓ Help", callback_data="cmd_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    logger.info(f"User {user.id} ({user.first_name}) started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command handler"""
    help_text = """
**📖 HELP - How to use this bot**

**1. Download a Reel/Post:**
   • Tap: 📥 Download Reel
   • Or use: `/download`
   • Paste Instagram link
   • Select quality with inline buttons
   • Done! ✅

**2. Download Stories:**
   • Tap: 📸 Download Story
   • Or use: `/story`
   • Enter Instagram username
   • Bot downloads latest story

**3. Search User:**
   • Tap: 🔍 Search User
   • Get user profile info with stats

**4. View History:**
   • Tap: 📜 History
   • See last 10 downloads

**5. Statistics:**
   • Tap: 📊 Stats
   • View your usage stats

**Supported URLs:**
✅ https://instagram.com/reel/xxxxx
✅ https://instagram.com/p/xxxxx
✅ https://instagram.com/tv/xxxxx
✅ https://instagr.am/p/xxxxx

**Note:** Only PUBLIC accounts supported!

**Problems?** 
• Check URL is correct
• Make sure profile is public
• Wait a moment and try again
"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ==================== MAIN MENU CALLBACKS ====================

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle main menu button clicks"""
    query = update.callback_query
    await query.answer()
    
    command = query.data.split("_")[1]
    
    if command == "download":
        await query.edit_message_text(
            "📥 **Please send me an Instagram link:**\n\n"
            "Examples:\n"
            "• https://instagram.com/reel/ABC123\n"
            "• https://instagram.com/p/XYZ789\n\n"
            "Type /cancel to stop.",
            parse_mode="Markdown"
        )
        context.user_data['awaiting_url'] = True
        
    elif command == "story":
        await query.edit_message_text(
            "📸 **Enter Instagram username:**\n\n"
            "Example: cristiano\n\n"
            "Type /cancel to stop.",
            parse_mode="Markdown"
        )
        context.user_data['awaiting_story'] = True
        
    elif command == "search":
        await query.edit_message_text(
            "🔍 **Enter Instagram username:**\n\n"
            "Example: cristiano\n\n"
            "Type /cancel to stop.",
            parse_mode="Markdown"
        )
        context.user_data['awaiting_search'] = True
        
    elif command == "history":
        await show_history_query(update, context)
        
    elif command == "stats":
        await show_stats_query(update, context)
        
    elif command == "help":
        await help_command(update, context)

# ==================== DOWNLOAD HANDLERS ====================

async def download_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start download conversation"""
    keyboard = [
        [InlineKeyboardButton("↩️ Back", callback_data="back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📥 **Please send me an Instagram link:**\n\n"
        "Examples:\n"
        "• https://instagram.com/reel/ABC123\n"
        "• https://instagram.com/p/XYZ789\n\n"
        "Type /cancel to stop.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    context.user_data['awaiting_url'] = True
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
    
    # Show loading
    loading_msg = await update.message.reply_text("⏳ Fetching media info...")
    
    try:
        # Get media info with quality options
        qualities, error = await instagram.get_available_qualities(url)
        
        if error or not qualities:
            await loading_msg.edit_text(f"❌ Error: {error}")
            return DOWNLOAD_URL
        
        context.user_data['download_url'] = url
        context.user_data['media_info'] = qualities
        
        # Create quality buttons with file sizes
        keyboard = []
        for quality_info in qualities:
            btn_text = f"{quality_info['emoji']} {quality_info['name']} - {quality_info['size']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"quality_{quality_info['id']}")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_download")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(
            "✅ **Available Quality Options:**",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return SELECT_QUALITY
        
    except Exception as e:
        await loading_msg.edit_text(f"❌ Error: {str(e)}")
        logger.error(f"Error fetching qualities: {str(e)}")
        return DOWNLOAD_URL

async def select_quality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quality selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_download":
        await query.edit_message_text("❌ Download cancelled!")
        return ConversationHandler.END
    
    quality_id = query.data.split("_")[1]
    context.user_data['selected_quality'] = quality_id
    
    await query.edit_message_text(
        "⏳ **Downloading...**\n\n"
        "Please wait, this may take a moment...",
        parse_mode="Markdown"
    )
    
    try:
        url = context.user_data['download_url']
        qualities = context.user_data['media_info']
        
        # Find selected quality info
        quality_info = next((q for q in qualities if q['id'] == quality_id), None)
        
        if not quality_info:
            await query.edit_message_text("❌ Quality not found!")
            return ConversationHandler.END
        
        # Download the media
        result, error = await instagram.download_media(url, quality_id)
        
        if error:
            await query.edit_message_text(f"❌ Error: {error}")
            logger.error(f"Download error: {error}")
            return ConversationHandler.END
        
        # Log to database
        db.log_download(
            update.effective_user.id,
            url,
            'reel' if 'reel' in url else 'post',
            result['filename'],
            result['file_size'],
            quality_info['name'],
            result.get('caption', '')
        )
        
        success_msg = f"""
✅ **Download Successful!**

📄 **File:** `{result['filename']}`
📊 **Quality:** {quality_info['name']}
💾 **Size:** {quality_info['size']}
👤 **Author:** @{result.get('username', 'unknown')}

"""
        
        if result.get('caption'):
            success_msg += f"💬 **Caption:** {result['caption'][:100]}..."
        
        await query.edit_message_text(success_msg, parse_mode="Markdown")
        logger.info(f"User {update.effective_user.id} downloaded: {url} (Quality: {quality_id})")
        
    except Exception as e:
        await query.edit_message_text(f"❌ Download failed: {str(e)}")
        logger.error(f"Download error: {str(e)}")
    
    return ConversationHandler.END

# ==================== STORY HANDLER ====================

async def story_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start story download"""
    keyboard = [
        [InlineKeyboardButton("↩️ Back", callback_data="back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📸 **Enter Instagram username:**\n\n"
        "Example: cristiano\n\n"
        "Type /cancel to stop.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    context.user_data['awaiting_story'] = True
    return SEARCH_USER

async def download_story(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Download user's story"""
    username = update.message.text.strip().lstrip('@')
    
    loading_msg = await update.message.reply_text("⏳ Fetching story...")
    
    try:
        result, error = await instagram.download_story(username)
        
        if error:
            await loading_msg.edit_text(f"❌ Error: {error}")
            return ConversationHandler.END
        
        story_msg = f"""
✅ **Story Downloaded!**

👤 **User:** @{username}
📄 **File:** {result['filename']}
💾 **Type:** {result['type']}
"""
        
        await loading_msg.edit_text(story_msg, parse_mode="Markdown")
        logger.info(f"User {update.effective_user.id} downloaded story from @{username}")
        
    except Exception as e:
        await loading_msg.edit_text(f"❌ Error: {str(e)}")
        logger.error(f"Story download error: {str(e)}")
    
    return ConversationHandler.END

# ==================== SEARCH HANDLER ====================

async def search_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start user search"""
    keyboard = [
        [InlineKeyboardButton("↩️ Back", callback_data="back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔍 **Enter Instagram username:**\n\n"
        "Example: cristiano\n\n"
        "Type /cancel to stop.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    context.user_data['awaiting_search'] = True
    return SEARCH_USER

async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle search input"""
    username = update.message.text.strip().lstrip('@')
    
    loading_msg = await update.message.reply_text(f"🔍 Searching for @{username}...")
    
    try:
        user_info, error = await instagram.search_user(username)
        
        if error:
            await loading_msg.edit_text(f"❌ Error: {error}")
            return ConversationHandler.END
        
        info_text = f"""
✅ **User Found!**

👤 **Name:** {user_info['full_name']}
📱 **Username:** @{user_info['username']}
✔️ **Verified:** {'Yes ✓' if user_info['verified'] else 'No'}

📊 **Stats:**
  • Followers: {user_info['followers']:,}
  • Following: {user_info['following']:,}
  • Posts: {user_info['posts']:,}

📝 **Bio:** {user_info['biography'][:100] if user_info['biography'] else 'No bio'}
"""
        
        # Create action buttons
        keyboard = [
            [InlineKeyboardButton("📥 Download Latest Post", callback_data=f"user_post_{username}")],
            [InlineKeyboardButton("❌ Close", callback_data="close_search")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(info_text, parse_mode="Markdown", reply_markup=reply_markup)
        logger.info(f"User {update.effective_user.id} searched for @{username}")
        
    except Exception as e:
        await loading_msg.edit_text(f"❌ Error: {str(e)}")
        logger.error(f"Search error: {str(e)}")
    
    return ConversationHandler.END

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
        history_text += f"   🕐 {timestamp}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🗑️ Clear History", callback_data="clear_history")],
        [InlineKeyboardButton("↩️ Back", callback_data="back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(history_text, parse_mode="Markdown", reply_markup=reply_markup)

async def show_history_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show download history from query"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    history = db.get_user_history(user_id, limit=10)
    
    if not history:
        await query.edit_message_text(
            "📜 **Your Download History**\n\n"
            "No downloads yet!"
        )
        return
    
    history_text = "📜 **Your Download History** (Last 10)\n\n"
    
    for idx, (filename, url, post_type, timestamp, caption) in enumerate(history, 1):
        history_text += f"{idx}. **{post_type.upper()}**\n"
        history_text += f"   📄 {filename}\n"
        history_text += f"   🕐 {timestamp}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("↩️ Back", callback_data="back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(history_text, reply_markup=reply_markup)

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
    
    keyboard = [
        [InlineKeyboardButton("↩️ Back", callback_data="back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(stats_text, parse_mode="Markdown", reply_markup=reply_markup)

async def show_stats_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show stats from query"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    stats = db.get_user_stats(user_id)
    
    if not stats:
        await query.edit_message_text("📊 **Your Statistics**\n\nStart downloading to see stats!")
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
    
    keyboard = [
        [InlineKeyboardButton("↩️ Back", callback_data="back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

# ==================== BACK HANDLER ====================

async def back_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Go back to main menu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📥 Download Reel", callback_data="cmd_download")],
        [InlineKeyboardButton("📸 Download Story", callback_data="cmd_story")],
        [InlineKeyboardButton("🔍 Search User", callback_data="cmd_search")],
        [InlineKeyboardButton("📜 History", callback_data="cmd_history")],
        [InlineKeyboardButton("📊 Stats", callback_data="cmd_stats")],
        [InlineKeyboardButton("❓ Help", callback_data="cmd_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("👋 **Main Menu**", reply_markup=reply_markup)

# ==================== MESSAGE HANDLER ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages"""
    if context.user_data.get('awaiting_url'):
        context.user_data['awaiting_url'] = False
        await get_download_url(update, context)
    elif context.user_data.get('awaiting_story'):
        context.user_data['awaiting_story'] = False
        await download_story(update, context)
    elif context.user_data.get('awaiting_search'):
        context.user_data['awaiting_search'] = False
        await handle_search_input(update, context)
    else:
        await update.message.reply_text("Please use /help for available commands")

# ==================== CANCEL HANDLER ====================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel operation"""
    await update.message.reply_text("❌ Operation cancelled!")
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
    app.add_handler(CommandHandler("history", show_history))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("download", download_start))
    app.add_handler(CommandHandler("story", story_start))
    
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
    
    # Search conversation
    search_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_user_start)],
        states={
            SEARCH_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(download_conv_handler)
    app.add_handler(story_conv_handler)
    app.add_handler(search_conv_handler)
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^cmd_"))
    app.add_handler(CallbackQueryHandler(back_menu, pattern="^back_menu$"))
    app.add_handler(CallbackQueryHandler(select_quality, pattern="^quality_"))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Start bot
    print("✅ Bot is running...")
    print("AWS Ubuntu Server - Instagram Reel Downloader Bot")
    print("Press Ctrl+C to stop.")
    print()
    
    app.run_polling()

if __name__ == '__main__':
    main()