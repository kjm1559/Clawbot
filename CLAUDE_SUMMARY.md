# CLAUDE System Summary

## Overview
CLAUDE is a wrapper/daemon that runs Claude Code (CC) sessions and:
- Streams session-specific output (stdout/stderr) to a designated Telegram Bot/chat
- Reports session state changes (start, running, waiting, completed, failed, etc.)
- Intercepts permission requests from CC and allows operators to respond via numeric input in Telegram (e.g., 1 = Allow, 2 = Allow once, 3 = Deny)

## Key Features
1. **Output Streaming**: Real-time streaming of stdout/stderr to Telegram
2. **Session Management**: Tracks session states (CREATED, STARTING, RUNNING, WAITING_PERMISSION, COMPLETED, FAILED, CANCELLED)
3. **Permission Handling**: Intercepts permission requests and allows numeric replies via Telegram
4. **Audit Logging**: Maintains logs for all permission decisions
5. **Access Control**: Enforces user and chat-level access control

## Architecture
- **Runner / Wrapper**: Spawns and manages CC processes, collects stdout/stderr streams, maintains session state machine
- **Event Bus**: Normalizes internal events (session.start, output.chunk, permission.request, state.change, session.end)
- **Telegram Notifier**: Converts events to Telegram messages, handles chunking and rate limiting
- **Telegram Command & Reply Handler**: Receives numeric replies and commands, maps replies to active permission requests
- **Permission Broker**: Tracks pending permission requests, resolves requests via Telegram input
- **Storage**: Session metadata, event logs, audit logs, Telegram message ↔ request mapping

## Configuration
The system requires these environment variables:
- `TELEGRAM_BOT_TOKEN` - Telegram bot token (required)
- `TELEGRAM_CHAT_ID` - Telegram chat ID (required)
- `ALLOWED_USER_IDS` - Comma-separated list of allowed user IDs (optional)
- Various other settings for output handling, timeouts, etc.

## How to Use
1. Set up Telegram bot and get token
2. Get the chat ID where messages should be sent
3. Configure environment variables
4. Run commands using: `claude run -- <command>`
5. Respond to permission requests via Telegram numeric replies (1=Allow, 2=Allow once, 3=Deny)

## Security Model
- Authorization is enforced based on user IDs
- Unauthorized replies are ignored and logged
- All permission resolutions are logged for audit purposes

## Limitations in Current Implementation
The current implementation shows that CLAUDE works correctly in terms of session management and command execution, but requires a valid Telegram bot token and chat ID to actually send messages. The dummy values we used in our test resulted in "Chat not found" errors, which is expected behavior.