#!/usr/bin/env python3
"""
Debug script to test the send command specifically
"""
import sys
import os
sys.path.insert(0, '.')

from claude import CLAUDE

# Test the send command parsing logic directly
def test_send_parsing():
    print("Testing send command parsing...")

    # Simulate what a Telegram message would look like
    test_cases = [
        "/send 123456789 hello world",
        "/send abc123 test message with spaces",
        "/send 999999 simple",
        "/send 123",
        "/send"
    ]

    for i, message_text in enumerate(test_cases):
        print(f"\nTest case {i+1}: '{message_text}'")
        parts = message_text.split(' ', 2)
        print(f"  Parts: {parts}")
        print(f"  Length: {len(parts)}")

        if len(parts) >= 3:
            sid = parts[1]
            text = parts[2]
            print(f"  Session ID: '{sid}'")
            print(f"  Text: '{text}'")
        else:
            print("  Not enough parts for valid /send command")

if __name__ == "__main__":
    test_send_parsing()