#!/usr/bin/env python3
import subprocess
import sys
import os

# Test what the exact command would be
test_message = "hello"
command = f'claude -p -c "{test_message}" --output-format json'

print(f"Testing exact command: {command}")
print("This command should work according to AGENTS.md specification")

try:
    # First, verify if this command works in shell
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=15
    )
    print(f"Return code: {result.returncode}")
    if result.stdout:
        print(f"STDOUT (first 200 chars): {repr(result.stdout[:200])}")
    if result.stderr:
        print(f"STDERR: {repr(result.stderr)}")
    print("Command completed successfully!")
    
except subprocess.TimeoutExpired:
    print("❌ Command timed out! This is likely an environment setup issue.")
    print("The command might need different execution mode or environment setup.")
    print("Try running the command directly in terminal first to verify:")
    print(f"  {command}")
except Exception as e:
    print(f"❌ Command failed with error: {e}")
    import traceback
    traceback.print_exc()