# claude-watch

Know when a Claude Code session is waiting on you, without watching the terminal.

Claude Code fires a `Notification` hook whenever a session stalls: a permission
prompt that has sat unanswered for ~6 seconds, an idle prompt ~60 seconds after
Claude finished talking, an MCP server asking for input, a paused usage limit.
`claude-watch` registers itself on that hook, remembers which sessions are
blocked and for how long, sends a desktop notification, and reminds you a few
more times, further apart each time, if you do not get to it. It runs on macOS. Windows support is experimental and
untested (see [Windows](#windows-experimental-untested)).

It tracks every session at once, so three terminals in three projects stay
distinguishable — each notification names the project, and `claude-watch status`
tells you which window to go to.

## Why this exists

This started because Michael wanted a way to get notified when Claude needs
you. Claude Code will happily sit on a permission prompt in a background
terminal for an hour while you assume it is still working. `claude-watch` is the
answer to that: it tells you the moment a session is waiting, and reminds you a
few times if you do not go back to it.

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

On install, `claude-watch` builds a small app of its own at
`~/.claude-watch/Claude Watch.app` and posts notifications from it. The first
one makes macOS ask whether to allow notifications from **Claude Watch**; say
yes. If you miss the prompt, turn it on under **System Settings →
Notifications → Claude Watch**.

**Clicking a notification jumps to the terminal window of the session that is
waiting.** Nothing else opens and there is nothing to pick. The first click
makes macOS ask whether Claude Watch may control your terminal app, which is
how it brings the window forward.

Optional:

```sh
brew install terminal-notifier
```

`claude-watch` picks it up automatically. It collapses repeat notifications for
the same session instead of stacking them, and a click goes to the exact
session that notification was about, rather than the latest one waiting.

## Windows (experimental, untested)

**The Windows port is experimental. It has never been run on a real Windows
machine.** It was written on a Mac, and only the macOS side has been tested.
Expect rough edges, and please file a *Windows test report* issue saying what
worked and what did not.

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
With no argument it picks the session that notified you most recently.
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
| `renag_seconds` | `300` | First reminder comes N seconds after the notification; `0` disables reminders |
| `renag_backoff` | `2` | Each later reminder waits this many times longer than the last; `1` keeps the gap fixed |
| `renag_max` | `3` | Stop after this many reminders |

With the defaults, a prompt you do not answer reminds you 5, 15, and 35 minutes
after the first notification, then goes quiet.

| Key | Default | Meaning |
| --- | --- | --- |
| `notifier` | `"auto"` | `auto`, `terminal-notifier`, `app`, `osascript`, or `none` (Windows: `auto` or `none`) |
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

macOS (tested) or Windows 10/11 (experimental, untested), Python 3.9+, Claude Code v2.1.198 or later for the `agent_needs_input`
and `agent_completed` notification types (everything else works on older
versions). On macOS, `terminal-notifier` is optional.

## Contributing

Bug reports, Windows test reports, and pull requests are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md), the [Code of Conduct](CODE_OF_CONDUCT.md),
and [SUPPORT.md](SUPPORT.md). Report security problems privately as described
in [SECURITY.md](SECURITY.md).

## Contributors

<a href="https://github.com/taylorarndt/claude-watch/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=taylorarndt/claude-watch" alt="Profile pictures of the people who have contributed to claude-watch" />
</a>

Made with [contrib.rocks](https://contrib.rocks).

## License

[MIT](LICENSE)
