# CLAUDE.md — Telegram Bridge for Claude CLI (Interactive REPL Mode)

## 0. Overview

This document defines a Telegram-based control bridge for the **Claude CLI (`claude`)**, which runs as an interactive REPL.

The system launches `claude` as a subprocess under a pseudo-terminal (PTY), streams all visible output to Telegram, and forwards Telegram user input back to the running REPL session.

This enables:

- Full output streaming from Claude CLI to Telegram
- Interactive input forwarding from Telegram to Claude
- Numeric permission handling
- Multi-session management
- Secure authorization and audit logging

Architecture:

    Telegram  ↔  Controller (Daemon)  ↔  claude (PTY subprocess)

Claude CLI is assumed to be a fully interactive REPL.

---

## 1. Core Capabilities

The system MUST support:

1. Running `claude` as a managed subprocess (PTY mode).
2. Streaming stdout/stderr/terminal output to Telegram.
3. Forwarding arbitrary Telegram input into the REPL.
4. Supporting numeric permission responses.
5. Handling special control signals (e.g., Ctrl+C).
6. Managing multiple concurrent sessions safely.
7. Enforcing strict authorization rules.
8. Logging all input/output events for auditing.

---

## 2. Execution Model

### 2.1 Launching Claude CLI

The controller launches:

    claude

using a pseudo-terminal (PTY).

PTY mode is mandatory because Claude CLI runs as an interactive REPL and may rely on:

- Readline
- Cursor movement
- Raw terminal input
- Line editing
- Control characters

PIPE mode is not recommended and not supported in MVP.

---

## 3. Architecture Components

### 3.1 Controller (Daemon)

Responsible for:

- Spawning PTY subprocesses
- Managing session lifecycle
- Capturing terminal output
- Forwarding Telegram input
- Enforcing authorization
- Emitting events

### 3.2 Telegram Adapter

- Sends formatted output messages
- Handles reply routing
- Parses commands
- Applies rate limiting

### 3.3 Session Manager

Tracks:

- session_id
- subprocess PID
- PTY handle
- state
- active claim owner (optional)

### 3.4 Storage

MVP storage (JSONL or SQLite):

- sessions.jsonl
- events.jsonl
- audit.jsonl
- telegram_map.json

---

## 4. Session Lifecycle

### 4.1 States

- CREATED
- STARTING
- RUNNING
- WAITING_PERMISSION
- COMPLETED
- FAILED
- CANCELLED

### 4.2 State Flow

- CREATED → STARTING → RUNNING
- RUNNING → WAITING_PERMISSION → RUNNING
- RUNNING → COMPLETED / FAILED

---

## 5. Output Streaming

### 5.1 Capturing Output

All PTY output must be captured.

This includes:

- Standard output
- Error output
- Prompts
- Interactive messages
- Permission prompts

### 5.2 Telegram Delivery

Because Telegram has limits:

- Max message size ≈ 3500 characters
- Rate limits per second

Controller MUST:

- Buffer PTY output for 100–300ms
- Chunk long output
- Throttle message sending

### 5.3 ANSI Handling

Claude CLI may emit ANSI escape codes.

Controller SHOULD:

- Optionally strip ANSI codes
- Or preserve minimal formatting
- Avoid raw cursor-control artifacts

Configuration option:

    STRIP_ANSI=true|false

### 5.4 Output Reading Fix

Fixed PTY output reading to properly capture and stream all output from Claude CLI sessions. The system now implements continuous monitoring of PTY processes to ensure output is properly captured and forwarded to Telegram even for long-running interactive sessions.

---

## 6. Interactive Input Forwarding (Telegram → Claude)

This is mandatory.

### 6.1 Supported Input

Telegram messages can be forwarded as:

- Arbitrary text
- Numeric responses
- Single-line commands
- Special control signals

### 6.2 Input Injection

For PTY mode:

- Write user text to PTY
- Append newline (`\r` or `\n`) by default

Example:

    pty.write("hello world\n")

### 6.3 Special Controls

Support:

- CTRL_C → send SIGINT to subprocess
- CTRL_D → send EOF
- ENTER → newline
- Optional arrow keys

Implementation:

- CTRL_C → send SIGINT signal
- CTRL_D → send EOT byte or close stdin
- Other keys → write escape sequences

---

## 7. Permission Handling

Permission prompts are treated as part of REPL interaction.

### 7.1 Detection (Optional Enhancement)

Controller MAY detect permission patterns and emit:

    permission.request event

Example Telegram message:

    🛡️ Permission request [SID:01H...]

    Reply:
    1) Allow
    2) Allow once
    3) Deny

### 7.2 Resolution

When operator replies with a number:

- Forward numeric input directly to PTY.
- Log decision in audit log.
- Resume RUNNING state.

Timeout behavior:

- If no reply within configured timeout (default 300s),
  send default numeric value to PTY.

---

## 8. Multi-Session Routing

Multiple Claude sessions may run simultaneously.

Incoming Telegram input must be routed safely.

### 8.1 Routing Priority

1. Reply-to Binding (Preferred)
   - If Telegram message replies to a message containing [SID:...],
     route input to that session.

2. Explicit Command
   - /send <sid> <text>

3. Claim Mode
   - /claim <sid>
   - Subsequent messages auto-forwarded
   - /release to stop

4. Fallback
   - If exactly one session active, auto-route
   - Otherwise require explicit SID

Ambiguous input must not be forwarded.

---

## 9. Telegram Commands

Required commands:

- /status
- /sessions
- /send <sid> <text>
- /claim <sid>
- /release
- /cancel <sid>
- /keys <sid> CTRL_C

---

## 10. Authorization & Security

### 10.1 Access Control

Only allowed users may:

- Send input
- Resolve permissions
- Control sessions

Configuration:

- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
- ALLOWED_USER_IDS

Unauthorized messages:

- Ignored
- Logged

### 10.2 Audit Logging

Each forwarded input must generate:

    {
      "event": "input.forwarded",
      "session_id": "...",
      "user_id": "...",
      "username": "...",
      "timestamp": "...",
      "bytes_len": 42
    }

Each permission resolution must log:

    {
      "event": "permission.resolve",
      "session_id": "...",
      "user_id": "...",
      "decision": 1,
      "timestamp": "..."
    }

---

## 11. Configuration

Environment variables:

- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
- ALLOWED_USER_IDS
- OUTPUT_MAX_CHARS=3500
- OUTPUT_FLUSH_MS=200
- PERMISSION_TIMEOUT_SEC=300
- STRIP_ANSI=true
- STORAGE_PATH=./claude_data
- LOG_LEVEL=info

---

## 12. Failure Handling

- Telegram API failure → exponential backoff
- PTY crash → mark session FAILED
- Daemon crash → terminate child processes (MVP)
- Permission timeout → send default value
- PTY output reading failure → retry with backoff, continue monitoring

---

## 13. MVP Scope

Minimum viable version must include:

1. Launch `claude` under PTY.
2. Stream all output to Telegram.
3. Forward arbitrary Telegram input to PTY.
4. Support Ctrl+C.
5. Support numeric permission replies.
6. Multi-session safe routing.
7. Authorization enforcement.
8. Audit logging.

---

## 14. Success Criteria

The system is considered complete when:

- All visible Claude CLI output appears in Telegram.
- Telegram input can control the REPL interactively.
- Numeric permission responses work reliably.
- Ctrl+C works.
- Multiple sessions do not conflict.
- Unauthorized users cannot inject commands.
- Full audit trail exists.
- PTY output is properly captured and streamed for long-running sessions.

---

End of CLAUDE.md
