import asyncio
import time
import logging
from typing import Optional, Callable, Set
from collections import deque

import aiohttp

logger = logging.getLogger(__name__)

def escape_only_dots(text: str) -> str:
    """Escape only '.' for Telegram MarkdownV2 ('.' -> '\\.')."""
    return text.replace(".", r"\.").replace("-", r"\-").replace("(", r"\(").replace(")", r"\)").replace("_", r"\_").replace("#", r"\#").replace("!", r"\!").replace("=", r"\=").replace("{", r"\{").replace("}", r"\}").replace(">", r"\>").replace("<", r"\<")

class TelegramBridge:
    def __init__(self, bot_token: str, chat_id: int, max_chunk: int = 3500,
                 send_interval_ms: int = 800, forward_prefix: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.max_chunk = max_chunk
        self.send_interval_ms = send_interval_ms
        self.forward_prefix = forward_prefix

        # Buffer for outgoing messages
        self._outgoing_buffer: deque = deque()
        self._last_send_time = 0.0

        # For handling incoming messages
        self._message_handler: Optional[Callable] = None

        # Rate limiting
        self._send_interval_seconds = send_interval_ms / 1000.0

    async def send_message(self, text: str):
        """Send a message to Telegram chat."""
        if not text:
            return

        # Chunk the message if needed
        chunks = self._chunk_text(text)

        for chunk in chunks:
            # Rate limiting
            now = time.time()
            time_since_last = now - self._last_send_time
            if time_since_last < self._send_interval_seconds:
                await asyncio.sleep(self._send_interval_seconds - time_since_last)

            # Send the chunk
            await self._send_chunk(chunk)
            self._last_send_time = time.time()

    def _chunk_text(self, text: str) -> list:
        """Split text into chunks that don't exceed max_chunk size."""
        if len(text) <= self.max_chunk:
            return [text]

        chunks = []
        while text:
            if len(text) <= self.max_chunk:
                chunks.append(text)
                break

            # Find a good split point
            chunk = text[:self.max_chunk]

            # Try to split at word boundary
            last_space = chunk.rfind(' ')
            if last_space > 0:
                chunk = chunk[:last_space]

            chunks.append(chunk)
            text = text[len(chunk):].lstrip()

        return chunks

    async def _send_chunk(self, chunk: str):
        """Send a single chunk to Telegram."""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        # Apply MarkdownV2 escaping to the chunk
        escaped_chunk = escape_only_dots(chunk)
        data = {
            'chat_id': self.chat_id,
            'text': escaped_chunk,
            'parse_mode': 'MarkdownV2'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status != 200:
                        # Log error but don't raise - we don't want to break the flow
                        error_text = await response.text()
                        logger.error(f"Failed to send message to Telegram: {response.status} - {error_text}")
        except Exception as e:
            # Log error but don't raise - we don't want to break the flow
            logger.error(f"Error sending message to Telegram: {e}")

    def set_message_handler(self, handler: Callable):
        """Set the handler for incoming Telegram messages."""
        self._message_handler = handler

    async def handle_incoming_message(self, message_data: dict):
        """Handle an incoming Telegram message."""
        if not self._message_handler:
            return

        # Validate chat ID
        if 'message' not in message_data:
            return

        message = message_data['message']
        if 'chat' not in message:
            return

        chat = message['chat']
        if 'id' not in chat:
            return

        if chat['id'] != self.chat_id:
            return

        if 'text' not in message:
            return

        text = message['text']
        # Apply prefix filter if set
        if self.forward_prefix and not text.startswith(self.forward_prefix):
            return

        # Forward the message to handler - wrap in try/except to prevent crashes
        try:
            await self._message_handler(text)
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            # Continue polling even if one message fails

    async def poll_telegram_updates(self, offset: int = 0):
        """Poll for Telegram updates - this would be called in a loop."""
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            'offset': offset,
            'timeout': 30
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data:
                            # Process all messages in the batch
                            for update in data['result']:
                                # Process each update
                                await self.handle_incoming_message(update)
                            
                            # Return the next offset for the next poll
                            if data['result']:
                                try:
                                    update_ids = [update.get('update_id', 0) for update in data['result'] if 'update_id' in update]
                                    if update_ids:
                                        next_offset = max(update_ids) + 1
                                        return next_offset
                                except (ValueError, TypeError):
                                    # If we can't compute max, return current offset
                                    logger.warning("Could not compute next offset from update IDs, keeping current offset")
                                    pass
                            # Fallback: if there were updates but couldn't get max, increment offset
                            # If there were no updates, return current offset
                            return offset + 1 if data['result'] else offset
                        else:
                            # No 'result' key in response - return current offset
                            return offset
                    else:
                        logger.error(f"Telegram API error: {response.status}")
                        return offset  # Return current offset on error
        except Exception as e:
            logger.error(f"Error polling Telegram updates: {e}")
            # Return current offset on error to prevent stopping polling
            return offset

    async def start_polling(self):
        """Start polling for Telegram messages."""
        offset = 0
        while True:
            try:
                offset = await self.poll_telegram_updates(offset)
                await asyncio.sleep(0.5)  # Poll every 500ms
            except Exception as e:
                logger.error(f"Error in Telegram polling loop: {e}")
                await asyncio.sleep(1)  # Wait before retrying
                # Do not reset offset on error, continue with current offset
            # Ensure we don't get stuck if offset becomes None
            if offset is None:
                offset = 0