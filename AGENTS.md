#Telegram Controller for Claude CLI

## Overview
Telegram bot controlling `claude` via CLI commands with intelligent typing indicators and structured JSON streaming output.

Designed for:
- One-shot execution with session continuation
- Structured JSON parsing
- Real-time streaming responses
- Optional session forking

---

## Core Features

- **Command Execution**: Run Claude CLI with structured JSON output
- **Session Continuation**: Continue latest session using `-c`
- **Session Forking**: Optional `--fork-session` support
- **Typing Indicators**: Intelligent typing action control
- **Streaming Output**: Real-time response streaming to Telegram
- **Error Handling**: Robust JSON and process error handling

---

## Execution Model

All Claude executions use:

```bash
claude -p -c "MESSAGE" --output-format stream-json
```

Note: The `-verbose` flag is not required when using `--output-format stream-json` with `--print` and may cause issues with JSON stream processing.

## Flag Explanation

| Flag | Purpose |
|------|-------|
| `-c` | Continue the latest session and preserve conversation context |
| `-p` | Print the response and exit (non-interactive, no REPL) |
| `--fork-session` | Create a new session branched from the current session state |
| `--output-format stream-json` | Output structured machine-readable JSON with streaming |

## Optional: Fork Session

To create a new branched session:

```bash
claude -p -c --fork-session "MESSAGE" --output-format json
```

## --fork-session
- Creates a new session derived from current context
- Preserves conversation state up to fork point
- Useful for alternate reasoning paths

## Telegram Commands

/ask <message>

Executes:

```bash
claude -p -c "<message>" --output-format stream-json
```

Streams parsed response to Telegram.

⸻

/new_session <message>

Executes:

```bash
claude -p "<message>" --output-format stream-json
```

Starts a new session without continuing the previous one.

⸻

/compact

Sends a summary request to Claude:

```bash
claude -p -c "Summarize all previous conversation and provide a concise overview of what has been done." --output-format stream-json
```

Creates a concise summary of the current conversation.

⸻

/fork <message>

Executes:
```bash
claude -p -c --fork-session "<message>" --output-format stream-json
```

Creates branched session and streams result.

⸻

/reset

No direct session deletion required.

To simulate reset, run without -c:

```bash
claude -p "<message>" --output-format json
```

ON Handling

All responses must be parsed from structured JSON output.

Typical structure:

```bash
{
  "type": "message",
  "content": [
    {
      "type": "text",
      "text": "Response content here"
    }
  ]
}
```

Filtering Rules

Ignore non-content events such as:
- step_start
- step_finish
- metadata-only events

Only forward meaningful content.text blocks to Telegram.

⸻

Typing Indicator Logic
1. Send typing action when command starts
2. Keep active while process is running
3. Stop typing when:
- Process exits successfully
- Final JSON message parsed
- Error occurs

Use process exit code:
- 0 → success
- non-zero → error

⸻

Streaming Strategy
- Spawn Claude process
- Read stdout line-by-line
- Buffer partial JSON fragments if needed
- Parse complete JSON objects
- Extract content.text
- Send incrementally to Telegram

⸻

Error Handling

CLI Errors
- Non-zero exit code → Send structured error message
- STDERR output → Log internally

JSON Errors
- Retry parse on partial chunk
- Fail gracefully with raw output fallback

Timeout Protection
- Optional process timeout
- Kill long-running processes safely

⸻

Recommended Production Invocation Pattern

Standard execution:

```bash
claude -p -c "USER_MESSAGE" --output-format stream-json
```

Forked execution:

```bash
claude -p -c --fork-session "USER_MESSAGE" --output-format stream-json
```

## Design Principles
- No manual session ID handling
- Rely on Claude CLI's internal session management
- Always use JSON mode for deterministic parsing
- Never use interactive REPL mode
- All executions must be non-interactive (-p required)
- Safe for automation, CI, and bot environments

## Troubleshooting
- If claude process hangs with "Command executed with PID" and no further output, try:
  1. Opening browser to http://localhost:3001 (default port)
  2. Checking if another process is using the port
  3. Running with a different port using -p flag
  4. Verifying terminal is not in a broken state
  5. Ensure npm exec is working correctly

