# CLAUDE System Usage Demo

## Current Status

The CLAUDE system is fully functional but currently configured with placeholder values in `.env`:
- TELEGRAM_BOT_TOKEN=123456789:ABC-DEF1234ghIJK5678lmnopQR890123456789
- TELEGRAM_CHAT_ID=123456789
- ALLOWED_USER_IDS=123456789

## How to Set Up Real Telegram Integration

1. **Create a Telegram Bot**:
   - Message @BotFather on Telegram
   - Send `/newbot` command
   - Give your bot a name and username
   - Copy the provided token

2. **Get Your Chat ID**:
   - Message your bot on Telegram
   - Visit: https://api.telegram.org/bot[TOKEN]/getUpdates
   - Find your chat ID in the response

3. **Update Configuration**:
   ```bash
   # Update .env file with real values
   TELEGRAM_BOT_TOKEN=your_real_bot_token_here
   TELEGRAM_CHAT_ID=your_real_chat_id_here
   ```

## Running Commands

Once properly configured, you can run:
```bash
claude run -- <command>
```

Example:
```bash
claude run -- echo "Hello World"
```

## Expected Behavior

1. Session starts → Telegram shows "Session started" message
2. Output streams → Telegram shows "Output chunk" messages
3. Permission requests → Telegram shows permission cards with 1/2/3 options
4. Session ends → Telegram shows exit status and duration

## Testing the System

You can test the core functionality without Telegram:
```bash
python test_clade.py
```

This will test session creation and permission request handling without Telegram integration.