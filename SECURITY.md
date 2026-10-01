# Security policy

## Supported versions

Only the latest version on the `main` branch is supported. Fixes are not
backported.

## Reporting a vulnerability

Please do not open a public issue for a security problem.

Report it privately through GitHub:
<https://github.com/taylorarndt/claude-watch/security/advisories/new>

Include what you found, how to reproduce it, and which platform you were on.
You should get a reply within 7 days. If the report is confirmed, a fix will be
released and you will be credited unless you ask not to be.

## What claude-watch touches

Knowing this helps you judge what counts as a vulnerability:

- It edits `~/.claude/settings.json` to register hooks, backing the file up
  first.
- It runs on every Claude Code hook event and reads the event JSON, which
  includes notification messages, working directories, and transcript paths.
- It stores session state and history in `~/.claude-watch/` as plain text.
  Nothing is sent over the network.
- It installs a background job (a launchd agent on macOS, a Task Scheduler job
  on Windows) that runs as you, with no elevated privileges.
- It starts `osascript`, `terminal-notifier`, or Windows PowerShell to show
  notifications. Notification text is passed as arguments or environment
  variables, never interpolated into a script.

Anything that lets hook input run commands, write outside `~/.claude-watch/`,
or damage `settings.json` is in scope.
