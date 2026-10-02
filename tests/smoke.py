#!/usr/bin/env python3
"""End-to-end smoke test: drive the hooks the way Claude Code does.

  python tests/smoke.py             safe anywhere; uses a throwaway state dir
  python tests/smoke.py --install   also runs install/uninstall for real, which
                                    edits ~/.claude/settings.json and registers
                                    the reminder agent. Meant for CI runners.
"""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "claude-watch"
IS_WINDOWS = os.name == "nt"

home = tempfile.mkdtemp(prefix="claude-watch-test-")
os.environ["CLAUDE_WATCH_HOME"] = home
Path(home, "config.json").write_text(json.dumps({"notifier": "none"}))


def run(*args, stdin=None):
    result = subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, f"{args} exited {result.returncode}: {result.stderr}"
    return result.stdout


def hook(event, **fields):
    payload = {"hook_event_name": event, "session_id": "smoke-1", "cwd": home, **fields}
    out = run("hook", stdin=json.dumps(payload))
    assert json.loads(out) == {"suppressOutput": True}, out


def sessions():
    return json.loads(run("status", "--json"))


def check(label, condition, detail=""):
    print(f"{'ok  ' if condition else 'FAIL'} {label}" + (f": {detail}" if detail else ""))
    if not condition:
        failures.append(label)


failures = []

hook("SessionStart")
check("session is registered", len(sessions()) == 1)

hook("Notification", notification_type="permission_prompt",
     message="Claude needs your permission to use Bash — “ünï”")
state = sessions()[0]
check("permission prompt marks the session waiting", state.get("status") == "waiting")
check("non-ASCII message survives", "ünï" in state.get("message", ""))
check("marker file exists while waiting", Path(home, "waiting").exists())

run("reap", "--verbose")
check("reap keeps a live session", len(sessions()) == 1)
run("status")
run("doctor")

bare = subprocess.run([sys.executable, str(SCRIPT), "focus"], capture_output=True, text=True)
check("focus with no argument picks the waiting session", bare.returncode == 0, bare.stdout.strip())

hook("PostToolUse")
check("tool use clears the wait", sessions()[0].get("status") == "idle")
check("marker file is removed", not Path(home, "waiting").exists())
events = [e.get("event") for e in json.loads(run("log", "--json"))]
check("history records the wait and its answer", events == ["notification", "resolved"], str(events))

hook("SessionEnd")
check("session end forgets the session", sessions() == [])
check("no errors were logged", not Path(home, "errors.log").exists(),
      Path(home, "errors.log").read_text() if Path(home, "errors.log").exists() else "")

# Internals that differ per platform.
loader = importlib.machinery.SourceFileLoader("claude_watch", str(SCRIPT))
cw = importlib.util.module_from_spec(importlib.util.spec_from_loader("claude_watch", loader))
loader.exec_module(cw)

table = cw._proc_table()
check("process table includes this process", os.getpid() in table)
check("this process counts as alive", cw.pid_alive(os.getpid()))
child = subprocess.Popen([sys.executable, "-c", "pass"])
child.wait()
check("an exited process counts as dead", not cw.pid_alive(child.pid))

if sys.platform == "darwin":
    binary = cw.notifier_binary()
    check("notifier app builds", binary is not None and binary.exists())
    check("notifier app is reused once built", cw.notifier_binary() == binary
          and not Path(home, "errors.log").exists())

if "--install" in sys.argv:
    print(run("install"))
    settings = json.loads(cw.SETTINGS_PATH.read_text(encoding="utf-8"))
    check("install registers all six hooks", len(settings.get("hooks", {})) == 6)

    payload = json.dumps({"hook_event_name": "SessionStart", "session_id": "smoke-2", "cwd": home})
    shells = {"default shell": None}
    if IS_WINDOWS:
        shells = {"cmd": None, "Git Bash": ["bash", "-c"],
                  "PowerShell": ["powershell.exe", "-NoProfile", "-Command"]}
    for name, prefix in shells.items():
        if prefix:
            result = subprocess.run([*prefix, cw.HOOK_COMMAND], input=payload,
                                    capture_output=True, text=True)
        else:
            result = subprocess.run(cw.HOOK_COMMAND, shell=True, input=payload,
                                    capture_output=True, text=True)
        check(f"hook command runs under {name}", "suppressOutput" in result.stdout,
              (result.stdout + result.stderr).strip()[:300])

    doctor = run("doctor")
    print(doctor)
    if IS_WINDOWS:
        check("scheduled task is registered", "reminder agent: loaded" in doctor)
        query = subprocess.run(["schtasks", "/Query", "/TN", cw.TASK_NAME, "/XML"],
                               capture_output=True, text=True)
        check("scheduled task runs on battery",
              "<DisallowStartIfOnBatteries>false" in query.stdout)

        # Informational only: runners are servers with no notification centre.
        env = {**os.environ, "CW_TITLE": "t", "CW_SUBTITLE": "s", "CW_MESSAGE": "m",
               "CW_SOUND": "", "CW_GROUP": "g", "CW_APPID": cw.TOAST_APP_ID}
        toast = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
                                "-Command", cw.TOAST_SCRIPT],
                               env=env, capture_output=True, text=True)
        print(f"info toast script exit {toast.returncode}: {toast.stderr.strip()[:400]}")

    print(run("uninstall"))
    settings = json.loads(cw.SETTINGS_PATH.read_text(encoding="utf-8"))
    check("uninstall removes the hooks", not settings.get("hooks"))

print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
