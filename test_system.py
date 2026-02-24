#!/usr/bin/env python3
"""
Simple test script to verify the CLAUDE system works correctly.
This script tests that the system can be properly started and run with a command.
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

async def test_system():
    """Test that the CLAUDE system works correctly"""
    print("Testing CLAUDE system...")

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

    try:
        # Initialize CLAUDE class
        claude = CLAUDE()
        print("✅ CLAUDE class initialized successfully")

        # Test 1: Telegram bot connection
        print("\nTest 1: Telegram bot connection...")
        success = await claude.start_telegram_bot()
        if success:
            print("✅ Telegram bot started successfully")
            await claude.stop_telegram_bot()
            print("✅ Telegram bot stopped successfully")
        else:
            print("❌ Failed to start Telegram bot")
            return False

        print("\n✅ System test completed successfully")
        print("\nTo run CLAUDE with a command, use:")
        print("  claude run -- <command>")
        print("\nFor example:")
        print("  claude run -- claude")
        return True

    except Exception as e:
        print(f"❌ Error during system test: {e}")
        logger.error(f"Error during system test: {e}")
        return False

if __name__ == "__main__":
    print("Running CLAUDE system test...")
    try:
        result = asyncio.run(test_system())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"Test failed with exception: {e}")
        sys.exit(1)