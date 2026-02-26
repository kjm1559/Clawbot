import os
from typing import Optional, Union

class Config:
    def __init__(self):
        self.telegram_bot_token: str = os.environ.get('TELEGRAM_BOT_CC_TOKEN', '')
        self.telegram_chat_id: int = int(os.environ.get('TELEGRAM_CHAT_ID', 0))
        self.tg_max_chunk: int = int(os.environ.get('TG_MAX_CHUNK', 3500))
        self.tg_send_interval_ms: int = int(os.environ.get('TG_SEND_INTERVAL_MS', 800))
        self.forward_prefix: Optional[str] = os.environ.get('FORWARD_PREFIX', None)

def load_config() -> Config:
    """Load configuration from environment variables."""
    config = Config()
    
    # Validate required variables
    if not config.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_CC_TOKEN environment variable is required")
    
    if config.telegram_chat_id == 0:
        raise ValueError("TELEGRAM_CHAT_ID environment variable is required")
    
    # Validate chat ID is valid
    if config.telegram_chat_id <= 0:
        raise ValueError("TELEGRAM_CHAT_ID must be a positive integer")
    
    return config