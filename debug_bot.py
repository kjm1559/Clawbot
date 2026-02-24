#!/usr/bin/env python3
"""
Debug script to check if Telegram bot is working properly
"""
import os
import asyncio
import logging
from claude import CLAUDE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def debug_bot():
    """Debug the Telegram bot"""
    print("Creating CLAUDE instance...")
    claude = CLAUDE()

    print("Starting Telegram bot...")
    success = await claude.start_telegram_bot()

    if success:
        print("✅ Telegram bot started successfully")
        print("Bot is running. Try sending a message to your Telegram bot.")
        print("Press Ctrl+C to stop.")

        # Keep running to see if messages are processed
        try:
            while True:
                await asyncio.sleep(5)
                print("Bot is still running...")
        except KeyboardInterrupt:
            print("Stopping bot...")
            await claude.stop_telegram_bot()
            print("Bot stopped.")

if __name__ == "__main__":
    asyncio.run(debug_bot())