# CLAUDE - Claude Code Session Reporter & Numeric Permission Controller

CLAUDE is a wrapper/daemon that runs Claude Code (CC) sessions and:
- Streams session-specific output (stdout/stderr) to a designated Telegram Bot/chat
- Reports session state changes (start, running, waiting, completed, failed, etc.)
- Intercepts permission requests from CC and allows operators to respond via numeric input in Telegram (e.g., 1 = Allow, 2 = Allow once, 3 = Deny)

## Features

- Stream CC session output (stdout/stderr) to Telegram in near real-time
- Notify Telegram on:
  - Session start
  - State changes
  - Permission requests
  - Session end (with summary)
- Allow operators to resolve permission requests via numeric reply in Telegram
- Support multiple concurrent sessions
- Maintain audit logs for all permission decisions
- Enforce user and chat-level access control

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env` or directly:
```bash
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export ALLOWED_USER_IDS="123456789,987654321"  # Optional
```

## Usage

### Run a command through CLAUDE:
```bash
claude run -- <claude-code command>
```

For example:
```bash
claude run -- claude
```

### Important Note:
The system **must** be run with a command to start a Claude CLI session. Without a running session, there's no way to receive Telegram messages. Telegram messages can only be forwarded to active sessions.

### Commands:
- `/status` - List active sessions
- `/help` - Show help message

### Permission Response:
When a permission request is triggered, reply with:
- `1` - Allow
- `2` - Allow once
- `3` - Deny (default)

## Architecture

### Core Components
- **Runner / Wrapper**: Spawns and manages CC processes, collects stdout/stderr streams, maintains session state machine
- **Event Bus**: Normalizes internal events (session.start, output.chunk, permission.request, state.change, session.end)
- **Telegram Notifier**: Converts events to Telegram messages, handles chunking and rate limiting
- **Telegram Command & Reply Handler**: Receives numeric replies and commands, maps replies to active permission requests
- **Permission Broker**: Tracks pending permission requests, resolves requests via Telegram input
- **Storage**: Session metadata, event logs, audit logs, Telegram message ↔ request mapping

### Session States
- CREATED
- STARTING
- RUNNING
- WAITING_PERMISSION
- COMPLETED
- FAILED
- CANCELLED

## Configuration

Environment variables:
- `TELEGRAM_BOT_TOKEN` - Telegram bot token (required)
- `TELEGRAM_CHAT_ID` - Telegram chat ID (required)
- `ALLOWED_USER_IDS` - Comma-separated list of allowed user IDs (optional)
- `POLL_INTERVAL_MS` - Polling interval (default: 1000)
- `OUTPUT_MAX_CHARS` - Max message size (default: 3500)
- `OUTPUT_FLUSH_MS` - Output flush interval (default: 1000)
- `PERMISSION_TIMEOUT_SEC` - Permission timeout (default: 300)
- `STORAGE_PATH` - Storage path for logs (default: ./clade_data/)
- `LOG_LEVEL` - Logging level (default: info)
