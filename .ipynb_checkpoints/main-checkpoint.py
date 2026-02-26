#!/usr/bin/env python3
"""
Main entry point for Telegram CLI Controller for Claude
"""
import sys
import os

# Add src to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.app import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())