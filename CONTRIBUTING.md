# Contributing

Thanks for wanting to help. This is a small project, so the process is light.

## Ways to contribute

- **Test on Windows.** The Windows port is experimental and has not been run on
  a real Windows machine by its author. Open a *Windows test report* issue and
  say what worked and what did not.
- **Report a bug** with the bug report template. The output of
  `claude-watch doctor` is the most useful thing you can include.
- **Suggest a feature** with the feature request template.
- **Send a pull request.** For anything larger than a small fix, open an issue
  first so we can agree on the approach.

## Working on the code

The whole tool is one Python file, `claude-watch`, with no dependencies outside
the standard library. Please keep it that way.

To try changes without touching your real state, point it at a scratch
directory:

```sh
export CLAUDE_WATCH_HOME=/tmp/claude-watch-dev
echo '{"hook_event_name":"Notification","session_id":"test","cwd":"/tmp/demo","notification_type":"permission_prompt","message":"hello"}' | ./claude-watch hook
./claude-watch status
```

## Rules the hook path must keep

- **It never blocks.** Notifications are spawned detached and never waited on.
- **It always exits 0.** A broken watcher must never break a Claude Code
  session. Errors go to `~/.claude-watch/errors.log`.
- **It stays cheap.** `PostToolUse` fires on every tool call, so the fast path
  must not take the lock or parse state when nothing is waiting.

## Accessibility

Notifications must work with screen readers, and command output must make sense
read aloud as plain text. Do not add output that relies on colour, emoji, or
box-drawing characters to carry meaning.

## Pull requests

- Say which platforms you tested on, and be honest if you could not test one.
- Update the README when behaviour or config changes.
- Keep changes focused. One fix or feature per pull request.

By contributing you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
