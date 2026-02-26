import asyncio
import logging
import os
import sys
import subprocess
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from config import load_config
from telegram_bridge import TelegramBridge

logger = logging.getLogger(__name__)

async def main():
    """Main application entry point - single-shot execution mode."""
    # Load configuration
    try:
        config = load_config()
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create Telegram bridge
    telegram_bridge = TelegramBridge(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
        max_chunk=config.tg_max_chunk,
        send_interval_ms=config.tg_send_interval_ms,
        forward_prefix=config.forward_prefix
    )

    # Set up message handler to execute single-shot clang commands
    async def handle_telegram_message(text: str):
        logger.info(f"Received Telegram message: {text}")
        logger.info("Preparing to execute Claude command...")
        
        # Execute a single-shot Claude command with the message
        try:
            # Run exactly as per AGENTS.md specifications:
            # claude -p -c "MESSAGE" --output-format json
            command = ['claude', '-p', '-c', text, '--output-format', 'json']
            
            logger.info(f"Command to execute: {' '.join(command)}")
            
            # Set environment to prevent interactive behavior
            env = os.environ.copy()
            env['TERM'] = 'dumb'
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # Execute the command with proper timeout and environment
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,  # Increased timeout to 60 seconds for long-running commands
                env=env
            )
            
            logger.info(f"Command executed with return code: {result.returncode}")
            
            # Log results
            if result.returncode == 0:
                logger.info("Command executed successfully")
                # Parse JSON output
                if result.stdout.strip():
                    try:
                        response_data = json.loads(result.stdout.strip())
                        logger.info(f"Successfully parsed JSON response with type: {response_data.get('type', 'unknown')}")
                        # Extract assistant text from response
                        if 'content' in response_data:
                            content = response_data['content']
                            if isinstance(content, list) and len(content) > 0:
                                assistant_text = content[0].get('text', '')
                                if assistant_text:
                                    logger.info("Sending response to Telegram")
                                    await telegram_bridge.send_message(assistant_text)
                                else:
                                    logger.warning("No text content found in response")
                                    await telegram_bridge.send_message("No response text found")
                            else:
                                logger.warning("Empty content array in response")
                                await telegram_bridge.send_message("Empty content")
                        else:
                            # Send the raw response if content is not structured properly
                            logger.warning("Response doesn't contain 'content' field")
                            await telegram_bridge.send_message(result.stdout.strip())
                    except json.JSONDecodeError as e:
                        # If response isn't JSON, send raw output
                        if result.stdout.strip():
                            logger.warning(f"Failed to parse JSON response: {e}")
                            await telegram_bridge.send_message(result.stdout.strip())
                else:
                    # Empty output case
                    logger.warning("Command executed but no output")
                    await telegram_bridge.send_message("Command executed but no output")
            else:
                logger.error(f"Command failed with code {result.returncode}")
                error_msg = f"Command failed: {result.stderr.strip() if result.stderr.strip() else 'Unknown error'}"
                await telegram_bridge.send_message(error_msg)
                
        except subprocess.TimeoutExpired:
            logger.error("Command timed out")
            await telegram_bridge.send_message("Command timed out (environment limitation)")
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            await telegram_bridge.send_message(f"Error: {str(e)}")

    telegram_bridge.set_message_handler(handle_telegram_message)

    # Start Telegram polling
    logger.info("Starting Telegram polling...")
    await telegram_bridge.start_polling()

if __name__ == "__main__":
    asyncio.run(main())