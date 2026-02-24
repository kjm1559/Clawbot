# Claude Code Integration Fix

## Current State Analysis

The current CLAUDE implementation can:
- Run commands through subprocess
- Stream stdout/stderr to Telegram
- Handle permission requests/responses via Telegram
- Manage session lifecycle

However, it does NOT properly integrate with Claude Code's permission system as specified in CLAUDE.md.

## Missing Integration Features

### Problem
The system does not intercept Claude Code's permission prompts to transform them into structured `permission.request` events.

### Required Implementation

Based on CLAUDE.md specification, there are two approaches:

### Option A: Structured Event Mode (Preferred)
- Claude Code must provide JSON logs with structured permission hooks
- CLAUDE would parse these structured events
- CLAUDE would inject responses via official input channels

### Option B: TTY/STDIN Wrapping (More Practical)
- Pattern-match permission prompts in stdout/stderr
- Transform to `permission.request` events
- Map numeric responses back to Claude Code's stdin

## What's Missing

The current implementation lacks:
1. Output parsing logic to detect Claude Code permission prompts
2. Logic to transform detected prompts into permission.request events
3. Mechanism to inject responses back to Claude Code's stdin

## Implementation Recommendations

To properly integrate with Claude Code, the system would need:

### 1. Enhanced Output Parsing
```python
# In handle_output_chunk method, add permission prompt detection:
def _detect_claude_permission_prompt(self, text):
    # Pattern to detect Claude Code permission prompts
    patterns = [
        r"Allow access to ([\w\s]+)\?",
        r"Permission required: ([\w\s]+)",
        r"Read file \"([^\"]+)\"",
        r"Write to file \"([^\"]+)\"",
        r"Execute command ([\w\s]+)"
    ]
    # Return category and summary based on matched pattern
```

### 2. Permission Request Generation
```python
# When permission prompt is detected, generate proper event:
if permission_detected:
    category = self._determine_permission_category(prompt_text)
    summary = self._extract_permission_summary(prompt_text)
    await self.send_permission_request(session_id, category, summary)
```

### 3. Response Injection
The system would also need to:
- Capture user's Telegram replies
- Inject responses back to Claude Code's stdin
- Handle multiple concurrent sessions properly

## Why This Matters

Without proper integration:
- Users can't actually use the permission handling feature
- The system only works as a simple output streamer
- It doesn't fulfill the core purpose of intercepting and managing Claude Code permissions

## Current Limitation

The system currently only handles:
1. Session start/end notifications
2. Output streaming
3. Manual permission request sending (not from Claude Code)
4. Telegram reply handling

But it doesn't actually intercept Claude Code's own permission prompts.