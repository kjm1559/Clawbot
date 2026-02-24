#!/usr/bin/env python3
"""
Simple test to check if Telegram connection works properly
"""

import os
import sys
import asyncio
import logging
from claude import CLAUDE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_telegram_connection():
    """Test Telegram connection"""
    print("Testing Telegram connection...")

    # Check if required environment variables are set
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    print(f"TELEGRAM_BOT_TOKEN set: {bool(telegram_bot_token)}")
    print(f"TELEGRAM_CHAT_ID set: {bool(telegram_chat_id)}")

    if not telegram_bot_token:
        print("ERROR: TELEGRAM_BOT_TOKEN environment variable not set")
        return False

    if not telegram_chat_id:
        print("ERROR: TELEGRAM_CHAT_ID environment variable not set")
        return False

    print("Environment variables are set. Attempting to initialize CLAUDE class...")

    try:
        # Initialize CLAUDE class
        claude = CLAUDE()
        print("CLAUDE class initialized successfully")

        # Try to start Telegram bot
        print("Attempting to start Telegram bot...")
        success = await claude.start_telegram_bot()

        if success:
            print("✅ Telegram bot started successfully!")
            print("✅ Telegram connection test PASSED")

            # Stop the bot
            await claude.stop_telegram_bot()
            print("Telegram bot stopped")

            return True
        else:
            print("❌ Failed to start Telegram bot")
            print("❌ Telegram connection test FAILED")
            return False

    except Exception as e:
        print(f"❌ Error during Telegram connection test: {e}")
        logger.error(f"Error during Telegram connection test: {e}")
        return False

if __name__ == "__main__":
    print("Running Telegram connection test...")
    try:
        result = asyncio.run(test_telegram_connection())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"Test failed with exception: {e}")
        sys.exit(1)