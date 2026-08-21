#!/bin/bash

# Instagram Reel Downloader Bot - Run Script
# Quick start script for AWS Ubuntu Server

echo "🚀 Instagram Reel Downloader Bot - Starting..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Install Python 3: sudo apt-get install python3 python3-pip"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Install/Update dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "❌ Please edit .env and add your BOT_TOKEN!"
    echo "   nano .env"
    exit 1
fi

# Check if BOT_TOKEN is set
if ! grep -q "BOT_TOKEN=YOUR_BOT_TOKEN_HERE" .env; then
    echo "✅ BOT_TOKEN is configured"
else
    echo "❌ BOT_TOKEN is not set in .env file!"
    echo "   Please edit .env and add your Telegram bot token"
    exit 1
fi

# Create necessary directories
mkdir -p downloads logs

# Show bot info
echo ""
echo "╔════════════════════════════════════════╗"
echo "║  🎬 Instagram Reel Downloader Bot 🎬  ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "📍 Python Version: $(python3 --version)"
echo "📍 Bot Directory: $(pwd)"
echo "📍 Downloads: ./downloads"
echo "📍 Logs: ./logs"
echo ""
echo "🟢 Starting bot..."
echo ""

# Run the bot
python3 bot.py

# Deactivate venv on exit
deactivate 2>/dev/null