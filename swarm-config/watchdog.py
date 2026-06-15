#!/usr/bin/env python3
"""
DHAHER SWARM — Python Watchdog Daemon
======================================
Based on blackhornet watchdog.py pattern.
10-second health checks with exponential backoff restart.
Ensures all 7 gateway profiles + ProxyGateLLM stay alive.
"""

import os
import sys
import json
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime

SWARM_DIR = Path("/root/.hermes")
PROFILES_DIR = SWARM_DIR / "profiles"
PID_DIR = SWARM_DIR / "supervisor-logs"
LOG_DIR = SWARM_DIR / "supervisor-logs"
SHARED_WS = SWARM_DIR / "shared-workspace"

PID_DIR.mkdir(parents=True, exist_ok=True)

PROFILES = ["autobot", "clawbot", "fangbot", "hackerbot", "devbot", "traderbot", "researchbot"]
CHECK_INTERVAL = 10  # seconds
MAX_BACKOFF = 300    # 5 min max backoff
INITIAL_BACKOFF = 5

backoff_tracker = {p: 0 for p in PROFILES}
proxy_backoff = 0
shutting_down = False

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [WATCHDOG] [{level}] {msg}"
    print(line, flush=True)
    log_file = LOG_DIR / "watchdog.log"
    with open(log_file, 'a') as f:
        f.write(line + '\n')

def is_alive(pid_file):
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, OSError, ValueError):
        pid_file.unlink(missing_ok=True)
        return False

def is_connected(profile):
    try:
        state_file = PROFILES_DIR / profile / "gateway_state.json"
        if not state_file.exists():
            return False
        data = json.loads(state_file.read_text())
        gw = data.get("gateway_state") == "running"
        tg = data["platforms"]["telegram"]["state"] == "connected"
        return gw and tg
    except Exception:
        return False

def restart_gateway(profile):
    """Restart a single gateway profile with clean state"""
    global backoff_tracker
    
    # Clean stale state
    for f in ["gateway.pid", "gateway.lock", "gateway_state.json"]:
        (PROFILES_DIR / profile / f).unlink(missing_ok=True)
    
    # Clean token locks
    lock_dir = Path("/root/.local/state/hermes/gateway-locks")
    if lock_dir.exists():
        for lf in lock_dir.glob("telegram-bot-token-*.lock"):
            lf.unlink(missing_ok=True)
    
    env = os.environ.copy()
    env["HERMES_HOME"] = str(PROFILES_DIR / profile)
    
    try:
        proc = subprocess.Popen(
            ["hermes", "gateway", "run", "--accept-hooks", "--replace"],
            env=env,
            stdout=open(LOG_DIR / f"{profile}.log", 'a'),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        (PID_DIR / f"{profile}.pid").write_text(str(proc.pid))
        backoff_tracker[profile] = INITIAL_BACKOFF
        log(f"✅ {profile} restarted (PID {proc.pid})")
        return True
    except Exception as e:
        log(f"❌ {profile} restart failed: {e}", "ERROR")
        backoff_tracker[profile] = min(backoff_tracker[profile] * 2 + 5, MAX_BACKOFF)
        return False

def check_proxygate():
    """Ensure ProxyGateLLM is running"""
    global proxy_backoff
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:3333/health"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip() == "200":
            proxy_backoff = 0
            return True
    except Exception:
        pass
    
    log("🔌 ProxyGateLLM DOWN — restarting", "WARNING")
    try:
        subprocess.Popen(
            ["node", "index.js"],
            cwd=str(SHARED_WS / "ProxyGateLLM"),
            stdout=open(LOG_DIR / "proxygate.log", 'a'),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        (PID_DIR / "proxygate.pid").write_text(str(proc.pid)) if 'proc' in dir() else None
        proxy_backoff = min(proxy_backoff * 2 + 10, MAX_BACKOFF)
    except Exception as e:
        log(f"❌ ProxyGateLLM restart failed: {e}", "ERROR")

def health_check():
    """Main health check cycle"""
    dead_count = 0
    
    for profile in PROFILES:
        pid_file = PID_DIR / f"{profile}.pid"
        
        if backoff_tracker[profile] > 0:
            backoff_tracker[profile] -= CHECK_INTERVAL
            if backoff_tracker[profile] > 0:
                continue  # Still in backoff, skip check
        
        if not is_alive(pid_file):
            log(f"💀 {profile} DEAD — restarting", "WARNING")
            restart_gateway(profile)
            dead_count += 1
            time.sleep(1)  # Stagger restarts
        elif not is_connected(profile):
            log(f"🔌 {profile} disconnected — restarting", "WARNING")
            restart_gateway(profile)
            dead_count += 1
            time.sleep(1)
    
    check_proxygate()
    
    if dead_count > 0:
        log(f"Health: {7 - dead_count}/7 alive, {dead_count} restarted")
    
    return dead_count

def signal_handler(signum, frame):
    global shutting_down
    shutting_down = True
    log("Watchdog received shutdown signal", "INFO")

def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    log("🛡️ Dhaher Swarm Watchdog — Activated (10s interval, exp backoff)")
    
    while not shutting_down:
        try:
            health_check()
        except Exception as e:
            log(f"Watchdog cycle error: {e}", "ERROR")
        
        time.sleep(CHECK_INTERVAL)
    
    log("Watchdog stopped")

if __name__ == "__main__":
    main()
