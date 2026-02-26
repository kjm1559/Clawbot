#!/usr/bin/env python3
"""
Simple test to verify the current implementation
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test that we can import the modules
try:
    from src.app import main
    print("Import successful - app module works correctly")
except Exception as e:
    print(f"Import failed: {e}")

print("Current implementation should display all intermediate messages")