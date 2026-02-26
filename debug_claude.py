#!/usr/bin/env python3
"""
Debug version to determine exactly what's happening with command execution
"""
import asyncio
import logging
import os
import sys
import subprocess
import json

# Set up logging first
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def debug_command():
    """Debug function to test the command directly"""
    logger.info("=== COMMAND EXECUTION DEBUG ===")
    
    # Test command
    text = "test"
    command = f'claude -p -c "{text}" --output-format json'
    
    logger.info(f"Command being built: {command}")
    logger.info(f"Command length: {len(command)}")
    
    # Check if claude exists
    try:
        result = subprocess.run(['which', 'claude'], capture_output=True, text=True, timeout=5)
        logger.info(f"Claude location: {result.stdout.strip()}")
    except Exception as e:
        logger.error(f"Error finding claude: {e}")
        return
    
    # Test just the shell command
    logger.info("Testing shell command execution...")
    try:
        shell_result = subprocess.run('echo "testing"', shell=True, capture_output=True, text=True, timeout=5)
        logger.info(f"Shell test output: {shell_result.stdout.strip()}")
    except Exception as e:
        logger.error(f"Shell test error: {e}")
    
    # Now test actual claude command
    logger.info("About to execute claude command...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=3)
        logger.info(f"RETURN CODE: {result.returncode}")
        logger.info(f"STDOUT (first 200 chars): {repr(result.stdout[:200])}")
        logger.info(f"STDERR (first 200 chars): {repr(result.stderr[:200])}")
        logger.info("Command execution completed.")
    except subprocess.TimeoutExpired:
        logger.error("COMMAND TIMED OUT - this shows claude is hanging!")
        logger.error("This is normal behavior for claude CLI in subprocess mode")
        logger.error("The issue is that claude CLI behaves as interactive tool in subprocess")
    except Exception as e:
        logger.error(f"Unexpected error in command execution: {e}")

if __name__ == "__main__":
    debug_command()