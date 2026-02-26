#!/usr/bin/env python3
"""
Simple test to verify the app imports correctly
"""
import sys
import os

# Test that modules import correctly
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    from config import load_config, Config
    from telegram_bridge import TelegramBridge
    
    print("✅ All modules import successfully")
    
    # Test config creation
    config = Config()
    print("✅ Config creation works")
    
    # Test bridge creation
    bridge = TelegramBridge(bot_token="test", chat_id=12345)
    print("✅ Telegram bridge creation works")
    
    print("\n🎉 Basic functionality verified!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()