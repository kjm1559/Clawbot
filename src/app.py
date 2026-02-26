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

        # Check if this is a /new_session command
        if text.startswith('/new_session'):
            # Extract the message part after /new_session
            message = text[len('/new_session'):].strip()
            if not message:
                await telegram_bridge.send_message("Error: Please provide a message after /new_session")
                return

            # Run command without -c option for new session
            command = ['claude', '-p', message, '--output-format', 'stream-json', '--verbose', '--allowedTools', 'Task,TaskOutput,Bash,Glob,Grep,ExitPlanMode,Read,Edit,Write,NotebookEdit,WebFetch,TodoWrite,WebSearch,TaskStop,AskUserQuestion,Skill,EnterPlanMode,EnterWorktree']
        # Check if this is a /compact command
        elif text.startswith('/compact'):
            # Send a summary request to Claude
            message = "Summarize all previous conversation and provide a concise overview of what has been done."
            command = ['claude', '-p', '-c', message, '--output-format', 'stream-json', '--verbose', '--allowedTools', 'Task,TaskOutput,Bash,Glob,Grep,ExitPlanMode,Read,Edit,Write,NotebookEdit,WebFetch,TodoWrite,WebSearch,TaskStop,AskUserQuestion,Skill,EnterPlanMode,EnterWorktree']
        else:
            # Run exactly as per AGENTS.md specifications:
            # claude -p -c "MESSAGE" --output-format stream-json
            command = ['claude', '-p', '-c', text, '--output-format', 'stream-json', '--verbose', '--allowedTools', 'Task,TaskOutput,Bash,Glob,Grep,ExitPlanMode,Read,Edit,Write,NotebookEdit,WebFetch,TodoWrite,WebSearch,TaskStop,AskUserQuestion,Skill,EnterPlanMode,EnterWorktree']

        logger.info(f"Command to execute: {' '.join(command)}")
        
        # Set environment to prevent interactive behavior
        env = os.environ.copy()
        env['TERM'] = 'dumb'
        env['PYTHONIOENCODING'] = 'utf-8'
        # Ensure no interactive behavior for Claude CLI
        env['CLAUDE_NO_INTERACTIVE'] = '1'
        # Set locale to avoid encoding issues
        env['LANG'] = 'C.UTF-8'
        env['LC_ALL'] = 'C.UTF-8'
        
        # Execute the command with proper timeout and environment
        try:
            # Use Popen for line-by-line processing  
            p = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                env=env,
                cwd=os.getcwd()
            )
            
            logger.info(f"Command executed with PID: {p.pid}")
            
            # Process output line by line
            for line in p.stdout:
                line = line.strip()
                if not line:
                    continue

                # Log the line being processed (this will show in logs)
                logger.info(f"Processing line from command: {line}.")

                # Send all lines to Telegram for display - this ensures intermediate messages are shown
                await telegram_bridge.send_message(line)

                try:
                    # Handle possible invalid JSON or malformed data gracefully
                    if not line.startswith('{'):
                        # Not JSON - send directly as text
                        continue

                    response_data = json.loads(line)
                    logger.info(f"Processing JSON line: type={response_data.get('type', 'unknown')}")

                    response_type = response_data.get('type', 'unknown')

                    # Only process message, user, and assistant types to filter out tool_use and tool_result
                    if response_type not in ['message', 'user', 'assistant']:
                        continue

                    # Handle different response types
                    if response_type == 'result':
                        # Result type is final signal - command completed
                        logger.info("Received result type - command completed")
                        # Send any final result if available
                        result_value = response_data.get('result', '')
                        if result_value:
                            await telegram_bridge.send_message(result_value)
                        break  # Stop processing after result

                    elif response_type in ['message', 'user', 'assistant']:
                        # Message type - extract text content
                        content = response_data.get('content', [])
                        if content and isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict):
                                    if item.get('type') == 'text':
                                        text_content = item.get('text', '')
                                        if text_content:
                                            # Send immediately as it's received
                                            await telegram_bridge.send_message(text_content)
                                            break
                                    elif item.get('type') == 'tool_result':
                                        # Handle tool_result content - display tool name and input wrapped in backticks
                                        tool_name = item.get('tool_call_id', 'Unknown Tool')
                                        input_content = item.get('input', '')
                                        if input_content:
                                            # Format tool call with backticks
                                            formatted_content = f"Tool: {tool_name}\nInput: ```{input_content}```\n"
                                            await telegram_bridge.send_message(formatted_content)
                                            break
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse line as JSON: {e}")
                    # If we can't parse a line, send as-is (for non-JSON output)
                    if line.strip():
                        # Send immediately as it's received
                        await telegram_bridge.send_message(line.strip())
                except Exception as e:
                    logger.error(f"Error processing response: {e}")
                    # Continue processing other messages
                    continue
                        
            # Force flush of any remaining output
            p.stdout.flush()
            
            # Wait for process to complete and get return code
            p.wait()
            logger.info(f"Command executed with return code: {p.returncode}")
            
            # Handle stderr output
            if p.stderr is not None:
                stderr_output = p.stderr.read().strip()
                if stderr_output:
                    logger.warning(f"Command stderr output: {stderr_output}")
                    # Send stderr output to Telegram for display with clear formatting
                    await telegram_bridge.send_message(f"STDERR: {stderr_output}")
                    
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