#!/usr/bin/env python3
"""
CLAUDE - Claude Code Session Reporter & Numeric Permission Controller
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
import uuid
import pexpect
import jsonlines
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

import telegram
from telegram import Update, Message, Chat
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ALLOWED_USER_IDS = os.getenv('ALLOWED_USER_IDS', '').split(',') if os.getenv('ALLOWED_USER_IDS') else []
STORAGE_PATH = os.getenv('STORAGE_PATH', './claude_data/')
OUTPUT_MAX_CHARS = int(os.getenv('OUTPUT_MAX_CHARS', '3500'))
OUTPUT_FLUSH_MS = int(os.getenv('OUTPUT_FLUSH_MS', '200'))
PERMISSION_TIMEOUT_SEC = int(os.getenv('PERMISSION_TIMEOUT_SEC', '300'))
STRIP_ANSI = os.getenv('STRIP_ANSI', 'true').lower() == 'true'

# Ensure storage path exists
os.makedirs(STORAGE_PATH, exist_ok=True)

# Storage file paths
SESSIONS_FILE = os.path.join(STORAGE_PATH, 'sessions.jsonl')
EVENTS_FILE = os.path.join(STORAGE_PATH, 'events.jsonl')
AUDIT_FILE = os.path.join(STORAGE_PATH, 'audit.jsonl')
TELEGRAM_MAP_FILE = os.path.join(STORAGE_PATH, 'telegram_map.json')

@dataclass
class Session:
    """Session data structure"""
    session_id: str
    command: str
    cwd: str
    env_summary: Dict[str, str]
    state: str
    start_time: float
    end_time: Optional[float] = None
    exit_code: Optional[int] = None
    duration_ms: Optional[int] = None
    pid: Optional[int] = None
    pty_handle: Optional[str] = None
    active_claim_owner: Optional[int] = None

    def __post_init__(self):
        pass

    def to_dict(self):
        data = asdict(self)
        data['start_time'] = self.start_time
        data['end_time'] = self.end_time
        return data

@dataclass
class PermissionRequest:
    """Permission request data structure"""
    request_id: str
    session_id: str
    category: str
    summary: str
    details: Optional[str] = None
    options: List[Dict[str, Any]] = None
    default: int = 3
    timeout_sec: int = 300
    created_at: float = None
    resolved: bool = False
    decision_code: Optional[int] = None
    decided_by: Optional[str] = None
    decided_at: Optional[float] = None

    def __post_init__(self):
        if self.options is None:
            self.options = [
                {"code": 1, "label": "Allow"},
                {"code": 2, "label": "Allow once"},
                {"code": 3, "label": "Deny"}
            ]
        if self.created_at is None:
            self.created_at = time.time()

    def to_dict(self):
        data = asdict(self)
        data['created_at'] = self.created_at
        data['decided_at'] = self.decided_at
        return data

@dataclass
class Event:
    """Event data structure for audit logging"""
    event: str
    session_id: str
    user_id: str
    username: str
    timestamp: str
    bytes_len: int = 0
    details: Optional[Dict[str, Any]] = None

    def to_dict(self):
        data = asdict(self)
        return data

class CLAUDE:
    """Main CLAUDE class"""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.permission_requests: Dict[str, PermissionRequest] = {}
        self.pending_requests: Dict[str, List[str]] = {}  # session_id -> [request_ids]
        self.output_buffers: Dict[str, List[str]] = {}  # session_id -> [chunks]
        self.output_flush_timers: Dict[str, asyncio.TimerHandle] = {}
        self.app: Optional[Application] = None
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self.pty_processes: Dict[str, pexpect.spawn] = {}  # For PTY mode
        self.claimed_sessions: Dict[int, str] = {}  # user_id -> session_id
        self.telegram_message_map: Dict[str, str] = {}  # telegram_message_id -> request_id
        self.audit_log: List[Dict[str, Any]] = []
        self.load_storage()

    def is_authorized(self, user_id: int) -> bool:
        """Check if a user is authorized to use the bot"""
        # If no allowed users are specified, allow all users
        if not ALLOWED_USER_IDS:
            return True

        # Check if user ID is in allowed list
        return str(user_id) in ALLOWED_USER_IDS

    async def start_telegram_bot(self):
        """Initialize and start the Telegram bot"""
        if not TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
            return False

        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Register handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("sessions", self.sessions_command))
        self.app.add_handler(CommandHandler("send", self.send_command))
        self.app.add_handler(CommandHandler("claim", self.claim_command))
        self.app.add_handler(CommandHandler("release", self.release_command))
        self.app.add_handler(CommandHandler("cancel", self.cancel_command))
        self.app.add_handler(CommandHandler("keys", self.keys_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_reply))

        # Start the bot
        await self.app.initialize()
        await self.app.start()
        # Start polling to actually process messages
        asyncio.create_task(self.app.updater.start_polling())
        logger.info("Telegram bot started with polling")
        return True

    async def stop_telegram_bot(self):
        """Stop the Telegram bot"""
        if self.app:
            await self.app.stop()
            await self.app.shutdown()
            logger.info("Telegram bot stopped")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text("CLAUDE bot is running! Send numeric replies to permission requests.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self.is_authorized(update.message.from_user.id):
            await update.message.reply_text("Unauthorized")
            return

        status_text = "Active sessions:\n"
        for sid, session in self.sessions.items():
            status_text += f"  {sid}: {session.state}\n"
        await update.message.reply_text(status_text)

    async def sessions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sessions command"""
        if not self.is_authorized(update.message.from_user.id):
            await update.message.reply_text("Unauthorized")
            return

        sessions_text = "All sessions:\n"
        for sid, session in self.sessions.items():
            sessions_text += f"  {sid}: {session.state} - {session.command}\n"
        await update.message.reply_text(sessions_text)

    async def send_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /send command"""
        if not self.is_authorized(update.message.from_user.id):
            await update.message.reply_text("Unauthorized")
            return

        user_id = update.message.from_user.id
        message_text = update.message.text.strip()

        # Parse command: /send <sid> <text>
        parts = message_text.split(' ', 2)
        if len(parts) < 3:
            await update.message.reply_text("Usage: /send <sid> <text>")
            return

        sid = parts[1]
        text = parts[2]

        if sid not in self.sessions:
            await update.message.reply_text(f"Session {sid} not found")
            return

        # Check if session is properly initialized for PTY interaction
        if sid not in self.pty_processes:
            # Try to get the session to see its state
            session = self.sessions.get(sid)
            if session:
                logger.warning(f"Session {sid} exists but not in pty_processes. State: {session.state}")
                await update.message.reply_text(f"Session {sid} exists but is not properly initialized for input. State: {session.state}")
            else:
                await update.message.reply_text(f"Session {sid} not found")
            return

        # Forward text to the session
        await self.forward_to_session(sid, text, user_id)
        await update.message.reply_text(f"Sent to session {sid}")

    async def claim_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /claim command"""
        if not self.is_authorized(update.message.from_user.id):
            await update.message.reply_text("Unauthorized")
            return

        user_id = update.message.from_user.id
        message_text = update.message.text.strip()

        # Parse command: /claim <sid>
        parts = message_text.split(' ', 1)
        if len(parts) < 2:
            await update.message.reply_text("Usage: /claim <sid>")
            return

        sid = parts[1]

        if sid not in self.sessions:
            await update.message.reply_text(f"Session {sid} not found")
            return

        # Claim the session
        self.claimed_sessions[user_id] = sid
        await update.message.reply_text(f"Claimed session {sid}")

    async def release_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /release command"""
        if not self.is_authorized(update.message.from_user.id):
            await update.message.reply_text("Unauthorized")
            return

        user_id = update.message.from_user.id

        if user_id in self.claimed_sessions:
            sid = self.claimed_sessions[user_id]
            del self.claimed_sessions[user_id]
            await update.message.reply_text(f"Released session {sid}")
        else:
            await update.message.reply_text("No session claimed")

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command"""
        if not self.is_authorized(update.message.from_user.id):
            await update.message.reply_text("Unauthorized")
            return

        user_id = update.message.from_user.id
        message_text = update.message.text.strip()

        # Parse command: /cancel <sid>
        parts = message_text.split(' ', 1)
        if len(parts) < 2:
            await update.message.reply_text("Usage: /cancel <sid>")
            return

        sid = parts[1]

        if sid not in self.sessions:
            await update.message.reply_text(f"Session {sid} not found")
            return

        # Cancel the session
        session = self.sessions[sid]
        if session.state in ["RUNNING", "WAITING_PERMISSION"]:
            session.state = "CANCELLED"
            await self.send_state_change(session, "CANCELLED")
            await update.message.reply_text(f"Cancelled session {sid}")
        else:
            await update.message.reply_text(f"Session {sid} is not running or waiting for permission")

    async def keys_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /keys command"""
        if not self.is_authorized(update.message.from_user.id):
            await update.message.reply_text("Unauthorized")
            return

        user_id = update.message.from_user.id
        message_text = update.message.text.strip()

        # Parse command: /keys <sid> [CTRL_C|CTRL_D]
        parts = message_text.split(' ', 2)
        if len(parts) < 2:
            await update.message.reply_text("Usage: /keys <sid> [CTRL_C|CTRL_D]")
            return

        sid = parts[1]

        if sid not in self.sessions:
            await update.message.reply_text(f"Session {sid} not found")
            return

        # Forward special key to the session
        if len(parts) >= 3:
            key = parts[2].upper()
            if key == "CTRL_C":
                await self.send_ctrl_c(sid)
            elif key == "CTRL_D":
                await self.send_ctrl_d(sid)
            else:
                await update.message.reply_text("Unknown key. Use CTRL_C or CTRL_D")
        else:
            await update.message.reply_text("Usage: /keys <sid> [CTRL_C|CTRL_D]")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
CLAUDE - Claude Code Session Reporter & Numeric Permission Controller

Commands:
/status - List active sessions
/sessions - List all sessions
/send <sid> <text> - Send text to a session
/claim <sid> - Claim a session for auto-forwarding
/release - Release claimed session
/cancel <sid> - Cancel a session
/keys <sid> CTRL_C - Send Ctrl+C to a session
/keys <sid> CTRL_D - Send Ctrl+D to a session
/help - Show this help message

To respond to permission requests, reply with:
1 - Allow
2 - Allow once
3 - Deny (default)
        """
        await update.message.reply_text(help_text)

    async def handle_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle numeric replies to permission requests and general input"""
        user_id = update.message.from_user.id
        reply_text = update.message.text
        message_id = update.message.message_id

        if not self.is_authorized(user_id):
            logger.warning(f"Unauthorized user {user_id} attempted to reply")
            await update.message.reply_text("Unauthorized")
            return

        # Check if this message is replying to a permission request
        if update.message.reply_to_message:
            # Check if the reply-to message contains a request ID
            reply_to_text = update.message.reply_to_message.text
            if reply_to_text and "Permission request" in reply_to_text:
                # Try to extract request_id from the reply-to message
                request_id = self.extract_request_id(reply_to_text)
                if request_id and request_id in self.permission_requests:
                    # This is a permission reply
                    await self.handle_permission_reply(update, context, request_id, user_id, reply_text)
                    return

        # Check if reply is numeric (for permission requests)
        if reply_text.isdigit():
            decision_code = int(reply_text)

            # Find pending permission requests for this user
            resolved = False
            for request_id, request in self.permission_requests.items():
                if (request.session_id in self.pending_requests and
                    request_id in self.pending_requests[request.session_id] and
                    not request.resolved):

                    # Validate decision code
                    valid_options = [opt['code'] for opt in request.options]
                    if decision_code in valid_options:
                        await self.resolve_permission_request(request_id, decision_code, user_id)
                        resolved = True
                        # Map this Telegram message to the request for future reference
                        self.telegram_message_map[str(message_id)] = request_id
                        break

            if not resolved:
                await update.message.reply_text("No pending permission request found for your reply")
            return

        # Handle regular text input
        # Determine which session to forward to based on routing priority:
        # 1. Reply-to binding
        # 2. Claim mode
        # 3. Fallback to single session or require explicit SID

        session_id = None

        # Check reply-to binding first
        if update.message.reply_to_message:
            reply_to_text = update.message.reply_to_message.text
            if reply_to_text:
                session_id = self.extract_session_id(reply_to_text)

        # If no reply-to binding, check if user has claimed a session
        if not session_id and user_id in self.claimed_sessions:
            session_id = self.claimed_sessions[user_id]

        # If no specific session identified, try to auto-route
        if not session_id:
            active_sessions = [sid for sid, session in self.sessions.items()
                              if session.state in ["RUNNING", "WAITING_PERMISSION"]]
            if len(active_sessions) == 1:
                session_id = active_sessions[0]
            elif len(active_sessions) > 1:
                await update.message.reply_text("Multiple active sessions. Please specify session ID or claim one.")
                return
            else:
                await update.message.reply_text("No active sessions. Please start a session first.")
                return

        # Forward text to the determined session
        await self.forward_to_session(session_id, reply_text, user_id)

    def extract_session_id(self, text: str) -> Optional[str]:
        """Extract session ID from text"""
        # Look for [SID:xxxxx] pattern
        import re
        match = re.search(r'\[SID:([^\]]+)\]', text)
        if match:
            return match.group(1)
        return None

    def extract_request_id(self, text: str) -> Optional[str]:
        """Extract request ID from text"""
        # Look for [RID:xxxxx] pattern
        import re
        match = re.search(r'\[RID:([^\]]+)\]', text)
        if match:
            return match.group(1)
        return None

    def create_session(self, command: str, cwd: str, env_summary: Dict[str, str]) -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            command=command,
            cwd=cwd,
            env_summary=env_summary,
            state="CREATED",
            start_time=time.time()
        )
        self.sessions[session_id] = session
        self.output_buffers[session_id] = []
        self.pending_requests[session_id] = []
        self.save_session(session)
        logger.info(f"Created session {session_id}")
        return session_id

    async def start_session(self, session_id: str, command: str, cwd: str, env_summary: Dict[str, str]):
        """Start a session by running the command"""
        # Update session state
        session = self.sessions[session_id]
        session.state = "STARTING"
        await self.send_session_start(session)

        # Create PTY process (mandatory for Claude CLI)
        try:
            # Use PTY mode only (PIPE mode is not supported)
            process = pexpect.spawn(command, cwd=cwd, timeout=None)
            session.pid = process.pid
            session.pty_handle = str(process)
            self.pty_processes[session_id] = process
            logger.info(f"Started PTY process for session {session_id}")

            # Update session state
            session.state = "RUNNING"
            await self.send_state_change(session, "RUNNING")

            # Start reading output
            asyncio.create_task(self.read_pty_output(session_id))

        except Exception as e:
            logger.error(f"Failed to start session {session_id}: {e}")
            session.state = "FAILED"
            session.end_time = time.time()
            session.duration_ms = int((session.end_time - session.start_time) * 1000)
            await self.send_session_end(session)
            # Clean up session from memory if it failed to start
            if session_id in self.sessions:
                del self.sessions[session_id]
            if session_id in self.pty_processes:
                del self.pty_processes[session_id]

    async def read_pty_output(self, session_id: str):
        """Read output from PTY process"""
        process = self.pty_processes.get(session_id)
        if not process:
            return

        # Read output from PTY process continuously
        try:
            while True:
                # Check if process is still alive
                if not process.isalive():
                    logger.info(f"PTY process ended for session {session_id}")
                    break

                try:
                    # Read available output from the PTY process
                    output = process.read_nonblocking(size=10000, timeout=0.1)
                    if output:
                        output_str = output.decode('utf-8', errors='ignore')
                        # Process the output - handle line by line
                        # Split by newlines to handle multiple lines
                        lines = output_str.split('\n')
                        for line in lines:
                            line = line.rstrip()
                            if line:
                                await self.handle_output_chunk(session_id, 'stdout', line)
                    else:
                        # No output available, small delay before next check
                        await asyncio.sleep(0.01)

                except pexpect.TIMEOUT:
                    # No data available, continue checking
                    await asyncio.sleep(0.01)
                    continue
                except pexpect.EOF:
                    # Process ended
                    logger.info(f"PTY process ended for session {session_id}")
                    break
                except Exception as e:
                    # Log error but continue reading to avoid stopping the process
                    logger.error(f"Error reading PTY output for session {session_id}: {e}")
                    # Small delay before retrying
                    await asyncio.sleep(0.01)
                    continue

        except Exception as e:
            logger.error(f"Error in PTY output reading loop for session {session_id}: {e}")

        # Process completed - update session state and clean up
        try:
            session = self.sessions.get(session_id)
            if session:
                if session.state != "COMPLETED" and session.state != "FAILED":
                    session.state = "COMPLETED"
                    session.end_time = time.time()
                    session.duration_ms = int((session.end_time - session.start_time) * 1000)
                    await self.send_session_end(session)

                # Clean up session from memory and storage
                if session_id in self.pty_processes:
                    del self.pty_processes[session_id]
                if session_id in self.output_buffers:
                    del self.output_buffers[session_id]
                if session_id in self.pending_requests:
                    del self.pending_requests[session_id]

                # Remove from sessions dict to prevent stale sessions
                if session_id in self.sessions:
                    del self.sessions[session_id]

        except Exception as e:
            logger.error(f"Error updating session state for {session_id}: {e}")

    # Note: The subprocess implementation has been removed to maintain only PTY mode as required by the specification

    async def handle_output_chunk(self, session_id: str, stream: str, text: str):
        """Handle an output chunk"""
        session = self.sessions[session_id]

        # Strip ANSI codes if configured to do so
        if STRIP_ANSI:
            # Remove ANSI escape codes
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            text = ansi_escape.sub('', text)

        # Check for permission prompts in stdout
        if stream == 'stdout':
            await self._check_for_permission_prompt(session_id, text)

        # Add to buffer
        self.output_buffers[session_id].append(text)

        # Send immediately if stderr
        if stream == 'stderr':
            await self.send_output_chunk(session_id, stream, text, is_partial=True)
        else:
            # For stdout, use flush timer to batch output
            if session_id in self.output_flush_timers:
                self.output_flush_timers[session_id].cancel()

            # Schedule flush
            loop = asyncio.get_event_loop()
            timer = loop.call_later(OUTPUT_FLUSH_MS / 1000.0,
                                  lambda: asyncio.create_task(self.flush_output(session_id)))
            self.output_flush_timers[session_id] = timer

    async def _check_for_permission_prompt(self, session_id: str, text: str):
        """Check if output contains a Claude Code permission prompt and handle it"""
        # Patterns to detect Claude Code permission prompts
        patterns = [
            r"Allow access to ([\w\s]+)\?",
            r"Permission required: ([\w\s]+)",
            r"Read file \"([^\"]+)\"",
            r"Write to file \"([^\"]+)\"",
            r"Execute command ([\w\s]+)",
            r"Access to ([\w\s]+)",
        ]

        for pattern in patterns:
            # Check if pattern exists in text (not using string comparison)
            import re
            if re.search(pattern, text):
                # Extract the file/command name
                match = re.search(pattern, text)
                if match:
                    summary = match.group(0)
                    await self.send_permission_request(session_id, "filesystem", summary)
                    return

    async def flush_output(self, session_id: str):
        """Flush output buffer"""
        if session_id not in self.output_buffers:
            return

        chunks = self.output_buffers[session_id]
        if not chunks:
            return

        # Send all chunks
        full_text = '\n'.join(chunks)
        await self.send_output_chunk(session_id, 'stdout', full_text, is_partial=False)

        # Clear buffer
        self.output_buffers[session_id] = []

    async def send_permission_request(self, session_id: str, category: str, summary: str):
        """Send a permission request to Telegram chat"""
        if not self.app or not TELEGRAM_CHAT_ID:
            return

        # Create a request ID
        request_id = str(uuid.uuid4())

        # Create the permission request object
        permission_request = PermissionRequest(
            request_id=request_id,
            session_id=session_id,
            category=category,
            summary=summary
        )

        # Store the request
        self.permission_requests[request_id] = permission_request
        if session_id not in self.pending_requests:
            self.pending_requests[session_id] = []
        self.pending_requests[session_id].append(request_id)

        # Format the permission request message
        message_text = f"""
🛡️ Permission request [RID:{request_id}][SID:{session_id}]

{summary}

Options:
1) Allow
2) Allow once
3) Deny (default)
"""

        # Print to terminal/console
        print(message_text)

        try:
            # Send message to Telegram chat
            await self.app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_text)
        except Exception as e:
            logger.error(f"Failed to send permission request to Telegram: {e}")

    async def resolve_permission_request(self, request_id: str, decision_code: int, user_id: str):
        """Resolve a permission request with the user's decision"""
        if request_id not in self.permission_requests:
            return

        request = self.permission_requests[request_id]
        request.resolved = True
        request.decision_code = decision_code
        request.decided_by = str(user_id)
        request.decided_at = time.time()

        # Log the audit event
        audit_event = Event(
            event="permission.resolve",
            session_id=request.session_id,
            user_id=str(user_id),
            username="",
            timestamp=datetime.now().isoformat(),
            bytes_len=0,
            details={"request_id": request_id, "decision": decision_code}
        )
        self.audit_log.append(audit_event.to_dict())
        self.save_audit_log(audit_event)

        # Forward the decision to the PTY process
        session = self.sessions.get(request.session_id)
        if session and request.session_id in self.pty_processes:
            pty_process = self.pty_processes[request.session_id]
            try:
                # Send the numeric decision to the PTY
                pty_process.sendline(str(decision_code))
            except Exception as e:
                logger.error(f"Failed to forward permission decision to PTY: {e}")

        # Remove from pending requests
        if request.session_id in self.pending_requests:
            try:
                self.pending_requests[request.session_id].remove(request_id)
            except ValueError:
                pass  # Already removed

    async def send_output_chunk(self, session_id: str, stream: str, text: str, is_partial: bool = False):
        """Send output chunk to both terminal and Telegram chat"""
        # First, print to terminal/console
        if stream == 'stderr':
            print(f"[SID:{session_id}] {stream.upper()}: {text}", file=sys.stderr)
        else:
            print(f"[SID:{session_id}] {stream.upper()}: {text}")

        # Then send to Telegram chat if available
        if not self.app or not TELEGRAM_CHAT_ID:
            return

        # Format the message with session ID
        if is_partial:
            # For partial output, we might want to indicate it's incomplete
            formatted_text = f"[SID:{session_id}] {stream.upper()}: {text}"
        else:
            formatted_text = f"[SID:{session_id}] {stream.upper()}: {text}"

        # Truncate if too long (Telegram has ~3500 character limit)
        if len(formatted_text) > OUTPUT_MAX_CHARS:
            formatted_text = formatted_text[:OUTPUT_MAX_CHARS-10] + " [TRUNCATED]"

        try:
            # Send message to Telegram chat
            await self.app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=formatted_text)
        except Exception as e:
            logger.error(f"Failed to send output chunk to Telegram: {e}")

    async def forward_to_session(self, session_id: str, text: str, user_id: int):
        """Forward text to a session"""
        # Check if session exists and has a valid PTY process
        if session_id not in self.pty_processes:
            logger.warning(f"Session {session_id} not found for forwarding")
            # Also check if session exists in sessions dict but not in pty_processes
            if session_id in self.sessions:
                session = self.sessions[session_id]
                logger.warning(f"Session {session_id} exists but not in pty_processes. State: {session.state}")
                # If the session is in a bad state, clean it up
                if session.state in ["FAILED", "COMPLETED", "CANCELLED"]:
                    logger.info(f"Cleaning up stale session {session_id}")
                    if session_id in self.sessions:
                        del self.sessions[session_id]
                    if session_id in self.pty_processes:
                        del self.pty_processes[session_id]
            return

        pty_process = self.pty_processes[session_id]
        if not pty_process.isalive():
            logger.warning(f"Session {session_id} PTY process not alive")
            # Clean up stale session
            try:
                session = self.sessions.get(session_id)
                if session:
                    session.state = "FAILED"
                    session.end_time = time.time()
                    session.duration_ms = int((session.end_time - session.start_time) * 1000)
                    await self.send_session_end(session)
                if session_id in self.pty_processes:
                    del self.pty_processes[session_id]
                if session_id in self.sessions:
                    del self.sessions[session_id]
            except Exception as e:
                logger.error(f"Error cleaning up stale session {session_id}: {e}")
            return

        # Log audit event
        audit_event = Event(
            event="input.forwarded",
            session_id=session_id,
            user_id=str(user_id),
            username="",
            timestamp=datetime.now().isoformat(),
            bytes_len=len(text.encode('utf-8'))
        )
        self.audit_log.append(audit_event.to_dict())
        self.save_audit_log(audit_event)

        # Print to terminal/console
        print(f"[SID:{session_id}] INPUT: {text}")

        # Send text to PTY
        try:
            pty_process.sendline(text)
        except Exception as e:
            logger.error(f"Failed to forward text to PTY: {e}")
            # Try to send a notification to user about the failure
            try:
                if self.app and TELEGRAM_CHAT_ID:
                    await self.app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"Failed to send input to session {session_id}: {e}")
            except:
                pass  # Ignore if we can't send notification

    async def send_ctrl_c(self, session_id: str):
        """Send Ctrl+C to a session"""
        if session_id not in self.pty_processes:
            logger.warning(f"Session {session_id} not found for Ctrl+C")
            return

        pty_process = self.pty_processes[session_id]
        if not pty_process.isalive():
            logger.warning(f"Session {session_id} PTY process not alive")
            return

        # Print to terminal/console
        print(f"[SID:{session_id}] Sending Ctrl+C")

        try:
            pty_process.sendintr()
        except Exception as e:
            logger.error(f"Failed to send Ctrl+C to PTY: {e}")

    async def send_ctrl_d(self, session_id: str):
        """Send Ctrl+D to a session"""
        if session_id not in self.pty_processes:
            logger.warning(f"Session {session_id} not found for Ctrl+D")
            return

        pty_process = self.pty_processes[session_id]
        if not pty_process.isalive():
            logger.warning(f"Session {session_id} PTY process not alive")
            return

        # Print to terminal/console
        print(f"[SID:{session_id}] Sending Ctrl+D")

        try:
            pty_process.sendeof()
        except Exception as e:
            logger.error(f"Failed to send Ctrl+D to PTY: {e}")

    async def send_session_start(self, session: Session):
        """Send session start notification to Telegram"""
        # This method would send a message to Telegram about session start
        # For now, we'll just log it since we don't have access to Telegram context here
        logger.info(f"Session {session.session_id} started")

        # Also print to terminal
        print(f"[SID:{session.session_id}] Session started")

    async def send_state_change(self, session: Session, new_state: str):
        """Send state change notification to Telegram"""
        # This would send a message to Telegram about session state change
        # For now, we'll just log it since we don't have access to Telegram context here
        logger.info(f"Session {session.session_id} state changed to {new_state}")

        # Also print to terminal
        print(f"[SID:{session.session_id}] State changed to {new_state}")

    async def send_session_end(self, session: Session):
        """Send session end notification to Telegram"""
        # This would send a message to Telegram about session end
        # For now, we'll just log it since we don't have access to Telegram context here
        logger.info(f"Session {session.session_id} ended")

        # Also print to terminal
        print(f"[SID:{session.session_id}] Session ended")

    async def handle_permission_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE, request_id: str, user_id: int, reply_text: str):
        """Handle a reply to a permission request"""
        if not reply_text.isdigit():
            await update.message.reply_text("Please reply with a number (1, 2, or 3)")
            return

        decision_code = int(reply_text)
        await self.resolve_permission_request(request_id, decision_code, user_id)
        await update.message.reply_text("Permission decision recorded")

    def load_storage(self):
        """Load storage data from JSONL files"""
        # Load sessions
        if os.path.exists(SESSIONS_FILE):
            try:
                with jsonlines.open(SESSIONS_FILE) as reader:
                    for obj in reader:
                        session = Session(**obj)
                        # Only load sessions that are not in terminal states
                        if session.state not in ["COMPLETED", "FAILED", "CANCELLED"]:
                            self.sessions[obj['session_id']] = session
                        else:
                            logger.info(f"Skipping stale session {obj['session_id']} in state {session.state}")
            except Exception as e:
                logger.error(f"Failed to load sessions: {e}")

        # Load audit log
        if os.path.exists(AUDIT_FILE):
            try:
                with jsonlines.open(AUDIT_FILE) as reader:
                    for obj in reader:
                        self.audit_log.append(obj)
            except Exception as e:
                logger.error(f"Failed to load audit log: {e}")

    def save_session(self, session: Session):
        """Save session to JSONL file"""
        try:
            with jsonlines.open(SESSIONS_FILE, mode='a') as writer:
                writer.write(session.to_dict())
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    def save_audit_log(self, event: Event):
        """Save audit event to JSONL file"""
        try:
            with jsonlines.open(AUDIT_FILE, mode='a') as writer:
                writer.write(event.to_dict())
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")

    async def run_command(self, command: str, cwd: str = None):
        """Run a command through CLAUDE"""
        if not TELEGRAM_CHAT_ID:
            logger.error("TELEGRAM_CHAT_ID environment variable not set")
            return

        # Create session
        env_summary = {k: v for k, v in os.environ.items() if not k.startswith('TELEGRAM_')}
        session_id = self.create_session(command, cwd or os.getcwd(), env_summary)

        # Start session
        await self.start_session(session_id, command, cwd or os.getcwd(), env_summary)

        # Keep running until completion
        try:
            while session_id in self.sessions:
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Interrupted")
        except Exception as e:
            logger.error(f"Error in run_command: {e}")

async def main():
    """Main entry point"""
    claude = CLAUDE()

    # Start Telegram bot
    if not await claude.start_telegram_bot():
        logger.error("Failed to start Telegram bot")
        return

    # Handle shutdown
    def signal_handler(signum, frame):
        logger.info("Shutting down...")
        asyncio.create_task(claude.stop_telegram_bot())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Check if command is provided
    if len(sys.argv) < 2 or sys.argv[1] != "run":
        print("Usage: claude run -- <command>")
        return

    if len(sys.argv) < 4 or sys.argv[2] != "--":
        print("Usage: claude run -- <command>")
        return

    command = " ".join(sys.argv[3:])
    logger.info(f"Running command: {command}")

    # Run the command
    await claude.run_command(command)

    # Keep the bot running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await claude.stop_telegram_bot()

if __name__ == "__main__":
    asyncio.run(main())