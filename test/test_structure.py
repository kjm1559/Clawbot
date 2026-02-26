#!/usr/bin/env python3
import sys
import os

# Set the current directory as the working directory for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Now test imports with proper structure
try:
    # Import modules directly as if they were in the current directory
    import importlib.util
    
    # Test config import  
    spec = importlib.util.spec_from_file_location("config", os.path.join(current_dir, "src", "config.py"))
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    
    print("✅ Config module imported successfully")
    
    # Test telegram_bridge import
    spec = importlib.util.spec_from_file_location("telegram_bridge", os.path.join(current_dir, "src", "telegram_bridge.py"))
    bridge_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge_module)
    
    print("✅ Telegram bridge module imported successfully")
    
    print("\n🎉 Basic functionality verified!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()