# claude-watch

Know when a Claude Code session is waiting on you, without watching the terminal.

Claude Code fires a `Notification` hook whenever a session stalls: a permission
prompt that has sat unanswered for ~6 seconds, an idle prompt ~60 seconds after
Claude finished talking, an MCP server asking for input, a paused usage limit.
`claude-watch` registers itself on that hook, remembers which sessions are
blocked and for how long, sends a desktop notification, and keeps reminding you
until you deal with it. It runs on macOS and Windows.

It tracks every session at once, so three terminals in three projects stay
distinguishable — each notification names the project, and `claude-watch status`
tells you which window to go to.

## Why this exists

This started because Michael wanted a way to get notified when Claude needs
you. Claude Code will happily sit on a permission prompt in a background
terminal for an hour while you assume it is still working. `claude-watch` is the
answer to that: it tells you the moment a session is waiting, and keeps telling
you until you go back to it.

## Install

```sh
./claude-watch install
```

That does three things:

1. Adds six hooks to `~/.claude/settings.json` (backing the file up first, and
   merging alongside any hooks you already have).
2. Writes a default config to `~/.claude-watch/config.json`.
3. Loads a launchd agent that runs `claude-watch reap` every 30 seconds, which
   is what produces the *reminders* for a prompt you have not answered yet.
   Skip it with `--no-daemon` and you get one notification per prompt instead.

Hooks are read when a session starts, so open a new Claude Code session
afterwards. `claude-watch uninstall` removes the hooks and the agent and leaves
your other settings untouched.

### Make notifications actually appear

By default this shells out to `osascript`, which routes notifications through
the built-in Script Editor app. If Script Editor does not have notification
permission, **the command fails silently** — macOS never prompts. One-time fix:

```sh
osascript -e 'display notification "test"'   # nothing appears yet
```

Then open **System Settings → Notifications**, find **Script Editor**, and turn
on *Allow Notifications*.

Better option:

```sh
brew install terminal-notifier
```

`claude-watch` picks it up automatically. It has its own app bundle (so macOS
prompts for permission properly), it collapses repeat notifications for the same
session instead of stacking them, and **clicking a notification jumps straight to
the terminal window that is blocked**.

## Windows

Same script, same commands. From PowerShell or Command Prompt, in the folder you
cloned into:

```
.\claude-watch.cmd install
.\claude-watch.cmd test
```

`claude-watch.cmd` is a two-line wrapper that runs the script with `python`, so
Python 3.9+ has to be on your `PATH`. What is different from macOS:

- **Notifications** are Windows toasts, sent through the built-in Windows
  PowerShell. They show up under the name "Windows PowerShell" in the
  notification centre, and screen readers announce them. If nothing appears,
  check **Settings → System → Notifications** and that Do Not Disturb is off.
- **Reminders** come from a Task Scheduler job named `claude-watch` instead of
  launchd. Task Scheduler cannot repeat faster than once a minute, so a reminder
  can land up to a minute late.
- **Sounds** are toast sound events (`Notification.Default`,
  `Notification.Reminder`, `Notification.IM`, `Notification.Mail`,
  `Notification.SMS`) rather than macOS sound names.
- **`speak`** uses the Windows speech synthesizer; `voice` takes an installed
  voice name such as `"Microsoft Zira Desktop"`.
- **`focus`** raises the terminal window the session lives in, but cannot pick
  the right tab inside Windows Terminal. Clicking a toast does not focus
  anything.
- **`notifier`** is `auto` (toast) or `none`.

## Commands

| Command | What it does |
| --- | --- |
| `claude-watch status` | What is waiting on you right now, longest wait first |
| `claude-watch status --json` | Same, as JSON |
| `claude-watch log [-n 40]` | History of waits: what asked, how long you took |
| `claude-watch focus 1` | Bring that session's terminal window to the front |
| `claude-watch test` | Send a sample notification |
| `claude-watch doctor` | Check hooks, notifier, agent, recent errors |
| `claude-watch config` | Print the config file and its path |
| `claude-watch clear` | Forget all tracked sessions |
| `claude-watch daemon` | Run the reminder loop in the foreground instead of launchd |
| `claude-watch install` / `uninstall` | Register / remove the hooks |

`focus` takes the number from `status`, a session id prefix, or a project name.
On macOS it works with Apple Terminal, iTerm2, and tmux panes.

Example:

```
$ claude-watch status
1 of 3 session(s) waiting on you.

1. WAITING 4m 12s: Claude needs approval
     project: lyra  (/Users/taylorarndt/Developer/lyra)
     says:    Claude needs your permission to use Bash
     where:   /dev/ttys004  Apple_Terminal  mode=ask
     session: 8df01052-6552-4f65-bb3b-ee7af359ec9c
```

## Config

`~/.claude-watch/config.json`. Delete a key to fall back to its default.

| Key | Default | Meaning |
| --- | --- | --- |
| `notify` | see below | Per notification type: show a desktop notification or not |
| `sounds` | `Ping` / `Tink` / `Glass` | Sound per type (macOS names shown; see Windows above); `""` for silent, `default` covers the rest |
| `speak` | `false` | Also announce the notification aloud |
| `voice` | `""` | Voice for `speak`, e.g. `"Samantha"`; empty uses the system voice |
| `renag_seconds` | `120` | Remind you every N seconds while a session stays blocked; `0` disables |
| `renag_max` | `4` | Stop after this many reminders |
| `notifier` | `"auto"` | `auto`, `terminal-notifier`, `osascript`, or `none` (Windows: `auto` or `none`) |
| `notify_on_stop` | `false` | Notify every time Claude finishes responding, not just when it idles |
| `stale_session_seconds` | `86400` | Forget sessions that have gone quiet this long |

The notification types, and which ones count as *waiting on you*:

| Type | Waiting? | Notified by default |
| --- | --- | --- |
| `permission_prompt` | yes | yes |
| `idle_prompt` | yes | yes |
| `agent_needs_input` | yes | yes |
| `elicitation_dialog` | yes | yes |
| `elicitation_url_dialog` | yes | yes |
| `quota_auto_resume_stale` | yes | yes |
| `quota_auto_resume_disabled` | yes | yes |
| `agent_completed` | no | yes |
| `quota_auto_resume_fired` | no | yes |
| `auth_success` | no | no |
| `elicitation_complete` | no | no |
| `elicitation_response` | no | no |

Turning a type off only stops the notification — the wait is still tracked and
still shows up in `status` and `log`.

## How it works

Six hooks, all pointing at `claude-watch hook`, which reads the event JSON on
stdin:

| Hook | Why |
| --- | --- |
| `Notification` | The actual signal: a session needs you. Records it and notifies. |
| `SessionStart` | Register the session and work out which terminal it lives in. |
| `PostToolUse` | A tool ran, so a permission prompt was answered. Clear the wait. |
| `UserPromptSubmit` | You typed, so you are clearly at the keyboard. Clear the wait. |
| `Stop` | Claude finished its turn. Clear the wait. |
| `SessionEnd` | Forget the session. |

State lives in `~/.claude-watch/state.json` under an `flock`, since hooks from
several sessions can fire at once. History is appended to
`~/.claude-watch/events.jsonl`.

Which terminal a session is in is worked out at `SessionStart` by walking up the
process tree from the hook: the nearest ancestor with a controlling tty gives the
tty that `focus` targets, and the nearest `claude` ancestor gives a pid whose
liveness tells `reap` whether the session still exists. `$TERM_PROGRAM`,
`$TERM_SESSION_ID` and `$TMUX_PANE` are recorded too.

Two properties the hook path is built around:

- **It never blocks.** Notifications are spawned detached and never waited on,
  and the hook always exits 0 even if something inside it throws (errors go to
  `~/.claude-watch/errors.log`, surfaced by `doctor`).
- **It stays off the hot path.** `PostToolUse` fires on every single tool call,
  so it checks for a `~/.claude-watch/waiting` marker file and returns
  immediately when nothing is blocked — no lock, no JSON parsing. Measured cost
  in that case is ~45 ms, which is Python startup.

## Requirements

macOS or Windows 10/11, Python 3.9+, Claude Code v2.1.198 or later for the `agent_needs_input`
and `agent_completed` notification types (everything else works on older
versions). On macOS, `terminal-notifier` is optional but recommended.
