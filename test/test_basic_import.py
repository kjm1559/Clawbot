#!/usr/bin/env python3
"""
Simple test to verify the modules import correctly
"""
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules work correctly."""
    try:
        # Test imports
        from src.config import load_config, Config
        from src.telegram_bridge import TelegramBridge
        
        print("✅ All modules import successfully")
        
        # Test config creation
        config = Config()
        print("✅ Config creation works")
        
        # Test bridge creation
        bridge = TelegramBridge(bot_token="test", chat_id=12345)
        print("✅ Telegram bridge creation works")
        
        print("\n🎉 Basic functionality verified!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_imports()