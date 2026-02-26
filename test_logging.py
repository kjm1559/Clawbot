#!/usr/bin/env python3
"""
Test script to verify logging changes
"""
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test the logging configuration
logger = logging.getLogger(__name__)
logger.info("Test logging message")

print("Logging test completed successfully")