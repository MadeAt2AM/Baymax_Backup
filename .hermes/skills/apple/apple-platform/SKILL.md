---
name: apple-platform
description: "Apple platform integrations: Notes, Reminders, Find My, iMessage, macOS automation via native CLIs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Apple, macOS, Notes, Reminders, FindMy, iMessage, Automation, iCloud]
    related_skills: [obsidian]
prerequisites:
  commands: [memo, remindctl]
---

# Apple Platform Integrations

This skill covers Apple platform integrations available to Hermes when running on macOS: Notes, Reminders, Find My, iMessage, and macOS automation via computer use.

## Prerequisites

Each sub-integration requires its own CLI tool. Install via Homebrew (`brew install ...`).
Each tool requires macOS with the respective Apple app and (for Notes/Reminders) Automation permissions.

## Integrations

### Apple Notes (`memo`)

**CLI:** `memo` (antoniorodr/memo tap)
**Install:** `brew install antoniorodr/memo/memo`
**Perms:** System Settings → Privacy → Automation → Notes.app

Manage Apple Notes from terminal. Notes sync via iCloud.

```bash
memo notes                    # List all notes
memo notes -f "Folder Name"  # Filter by folder
memo notes -s "query"       # Search notes (fuzzy)
memo add "Note content"     # Create note
memo export --md            # Export to Markdown
```

### Apple Reminders (`remindctl`)

**CLI:** `remindctl` (steipete tap)
**Install:** `brew install steipete/tap/remindctl`
**Perms:** Grant Reminders permission when prompted

Manage Apple Reminders from terminal. Tasks sync via iCloud across all Apple devices.

```bash
remindctl                       # Today's reminders
remindctl today                 # Today
remindctl add "Buy milk"        # Add reminder
remindctl add --title "Call" --due tomorrow
remindctl complete <id>        # Complete by ID
remindctl list                  # List all lists
```

### Find My (`findmy`)

**CLI:** `findmy` (custom script or `findmy` CLI)
**Perms:** Location Services enabled

Query location of Apple devices and contacts tagged with AirTag / Find My.

```bash
findmy list                     # List devices
findmy locate "iPhone"         # Get location
```

### iMessage

**CLI:** via `osascript` or `imessage` CLI
**Perms:** Full Disk Access for Messages app

Send and read iMessages from terminal.

```bash
# osascript approach
osascript -e 'tell application "Messages" to send "Hello" to buddy "+1555..."'
```

**Pitfall:** Requires Full Disk Access on macOS. Will silently fail without it.
**Alternative:** Use a dedicated relay service if running in a restricted environment.

### macOS Computer Use

Use browser automation on macOS via Accessibility permissions (AppleScript/GUI automation).

**Perms:** System Settings → Privacy → Accessibility

When the user wants Hermes to interact with macOS GUI applications:
1. Grant Accessibility permission to the terminal or Hermes backend
2. Use `osascript` for scriptable GUI control
3. Use `clicks` or `cliclick` CLI for mouse automation

```bash
cliclick c:500,300    # Click at screen coordinates
cliclick dc:500,300  # Double-click
```

---

## When NOT to Use

| Task | Use Instead |
|------|-------------|
| Agent-only memory/notes | `memory` tool |
| Obsidian vault | `obsidian` skill |
| Cross-platform notes | `honcho-memory` or `notion` |
| Scheduling agent alerts | `cronjob` tool |

## Shared Platform Notes

- All Apple integrations sync via **iCloud** — ensure the Mac is signed into the same Apple ID as other devices
- **Permissions** must be granted individually per tool — automation permissions live in System Settings → Privacy
- Scripts that call AppleScript (`osascript`) may need **Full Disk Access** to read from apps like Messages, Notes, Reminders
