#!/usr/bin/env python3
"""
Comprehensive test to verify CLAUDE system functionality
"""

import os
import sys
import asyncio
import logging
from claude import CLAUDE, Session, PermissionRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_comprehensive_claude():
    """Comprehensive test of CLAUDE system functionality"""
    print("Running comprehensive CLAUDE system test...")

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

        # Test 2: Session creation
        print("\nTest 2: Session creation...")
        command = "echo 'test command'"
        cwd = "/tmp"
        env_summary = {"TEST": "value"}
        session_id = claude.create_session(command, cwd, env_summary)
        if session_id:
            print(f"✅ Session created successfully with ID: {session_id}")
            if session_id in claude.sessions:
                print("✅ Session found in session manager")
            else:
                print("❌ Session not found in session manager")
                return False
        else:
            print("❌ Failed to create session")
            return False

        # Test 3: Permission request handling
        print("\nTest 3: Permission request handling...")
        permission_request = PermissionRequest(
            request_id="test-request-123",
            session_id=session_id,
            category="test",
            summary="Test permission request"
        )
        claude.permission_requests[permission_request.request_id] = permission_request
        claude.pending_requests[session_id] = [permission_request.request_id]
        print("✅ Permission request created and stored")

        # Test 4: Basic helper methods
        print("\nTest 4: Helper method tests...")

        # Test session ID extraction
        test_text = "[SID:test123] Some output"
        extracted_sid = claude.extract_session_id(test_text)
        if extracted_sid == "test123":
            print("✅ Session ID extraction works")
        else:
            print("❌ Session ID extraction failed")
            return False

        # Test request ID extraction
        test_text = "[RID:request456] Some output"
        extracted_rid = claude.extract_request_id(test_text)
        if extracted_rid == "request456":
            print("✅ Request ID extraction works")
        else:
            print("❌ Request ID extraction failed")
            return False

        print("\n✅ All comprehensive tests PASSED")
        return True

    except Exception as e:
        print(f"❌ Error during comprehensive test: {e}")
        logger.error(f"Error during comprehensive test: {e}")
        return False

if __name__ == "__main__":
    print("Running comprehensive CLAUDE system test...")
    try:
        result = asyncio.run(test_comprehensive_claude())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"Test failed with exception: {e}")
        sys.exit(1)