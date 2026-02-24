#!/usr/bin/env python3
"""
Test script to verify the Telegram integration is working properly
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

async def test_comprehensive():
    """Comprehensive test of the Telegram integration"""
    print("=== Comprehensive Telegram Integration Test ===")

    # Check environment variables
    print(f"TELEGRAM_BOT_TOKEN set: {bool(os.getenv('TELEGRAM_BOT_TOKEN'))}")
    print(f"TELEGRAM_CHAT_ID set: {bool(os.getenv('TELEGRAM_CHAT_ID'))}")
    print(f"ALLOWED_USER_IDS set: {bool(os.getenv('ALLOWED_USER_IDS'))}")

    # Initialize CLAUDE class
    print("Creating CLAUDE instance...")
    claude = CLAUDE()

    # Test Telegram bot connection
    print("Starting Telegram bot...")
    success = await claude.start_telegram_bot()

    if success:
        print("✅ Telegram bot started successfully!")
        print("✅ Telegram integration is working properly!")

        # Test the authorization method
        print("Testing authorization...")
        test_user_id = 123456789
        is_auth = claude.is_authorized(test_user_id)
        print(f"User {test_user_id} authorized: {is_auth}")

        # Stop the bot
        print("Stopping bot...")
        await claude.stop_telegram_bot()
        print("✅ Bot stopped successfully")

        return True
    else:
        print("❌ Failed to start Telegram bot")
        return False

if __name__ == "__main__":
    print("Running comprehensive test...")
    try:
        result = asyncio.run(test_comprehensive())
        if result:
            print("\n🎉 All tests passed! Telegram integration is working.")
        else:
            print("\n💥 Some tests failed.")
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)