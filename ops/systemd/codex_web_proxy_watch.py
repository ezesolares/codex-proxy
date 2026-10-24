#!/usr/bin/env python3
"""Check proxy liveness and refresh its Codex workers when the Web bridge returns.

Do not replay requests: an interrupted coding turn might have made changes.
Only local socket/HTTP probes, with no credentials or model quota consumption.
"""

import json
import os
from pathlib import Path
import socket
import subprocess
import urllib.error
import urllib.request

UNIT = "artemob-codex-web-proxy.service"
BRIDGE_PORT = int(os.getenv("CODEX_PROXY_WATCH_BRIDGE_PORT", "17841"))
PROXY_PORT = int(os.getenv("CODEX_PROXY_WATCH_PROXY_PORT", "3467"))
DRY_RUN = os.getenv("CODEX_PROXY_WATCH_DRY_RUN") == "1"
RUN_DIR = Path(os.getenv("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
STATE_FILE = Path(os.getenv("CODEX_PROXY_WATCH_STATE_FILE", str(RUN_DIR / "codex-web-proxy-watch.json")))


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except OSError:
        return False


def proxy_healthy() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PROXY_PORT}/health", timeout=3) as r:
            return r.status == 200 and json.load(r).get("status") == "ok"
    except (OSError, ValueError, urllib.error.URLError):
        return False


def load_state() -> dict:
    try:
        state = json.loads(STATE_FILE.read_text())
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
    tmp.write_text(json.dumps(state) + "\n")
    tmp.chmod(0o600)
    tmp.replace(STATE_FILE)


def main() -> None:
    before = load_state()
    bridge_up = port_open(BRIDGE_PORT)
    proxy_up = proxy_healthy()
    failed = 0 if proxy_up else int(before.get("proxy_failures", 0)) + 1
    state = {"bridge": "up" if bridge_up else "down", "proxy_failures": failed}
    reason = None
    if before.get("bridge") == "down" and bridge_up:
        reason = "bridge_recovered"
    elif failed >= 2:
        reason = "proxy_unhealthy_twice"

    if reason:
        if DRY_RUN:
            print(f"DRY_RUN would restart {UNIT}: {reason}")
        else:
            print(f"restarting {UNIT}: {reason}")
            try:
                result = subprocess.run(["systemctl", "--user", "restart", UNIT], timeout=12, check=False)
                restarted = result.returncode == 0
            except (OSError, subprocess.TimeoutExpired) as exc:
                print(f"restart failed: {type(exc).__name__}")
                restarted = False
            if not restarted:
                # Keep the old bridge state so recovery will be retried next check.
                state["bridge"] = before.get("bridge", "down")
                print("restart unsuccessful")
            else:
                state["proxy_failures"] = 0
    else:
        print(f"bridge={'up' if bridge_up else 'down'} proxy={'healthy' if proxy_up else 'unhealthy'} failures={failed}")

    if not DRY_RUN:
        save_state(state)


if __name__ == "__main__":
    main()
