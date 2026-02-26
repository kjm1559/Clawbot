# Clawbot - Claude Telegram Bridge

Clawbot is a Telegram bridge for the Claude CLI that enables interactive REPL sessions through Telegram. It allows users to control Claude CLI through Telegram messages, with support for numeric permissions and multi-session management.

## Features

- **Telegram Integration**: Communicate with Claude CLI through Telegram
- **Interactive REPL**: Full interactive terminal session support
- **Numeric Permissions**: Handle numeric permission responses from Claude
- **Multi-session Management**: Support for multiple concurrent sessions
- **Secure Authorization**: Strict authorization rules enforcement
- **Audit Logging**: Complete input/output event logging for auditing

## Architecture

```
Telegram  ↔  Controller (Daemon)  ↔  claude (PTY subprocess)
```

The system launches Claude CLI as a managed subprocess under a pseudo-terminal (PTY) and streams all visible output to Telegram while forwarding Telegram user input back to the running REPL session.

## Requirements

- Python 3.9+
- Telegram Bot Token
- Claude CLI installed and accessible

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `TELEGRAM_CHAT_ID`: Your Telegram chat ID
   - `ALLOWED_USER_IDS`: Comma-separated list of allowed user IDs (optional)

## Usage

1. Start the bot: `python main.py`
2. Send commands to your Telegram bot
3. Interact with Claude CLI through Telegram

## Configuration

Configuration is handled through environment variables. You can also use a `.env` file for local development.

## Contributing

Contributions are welcome! Please submit a pull request with your changes.

## License

This project is licensed under the MIT License.