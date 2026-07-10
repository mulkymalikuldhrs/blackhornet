import sys
p = "src/immortal_daemon.py"
s = open(p).read()

old1 = '''from swarm_protocol import SwarmProtocol

logger = logging.getLogger("ImmortalDaemon")'''
new1 = '''logger = logging.getLogger("ImmortalDaemon")

# SwarmProtocol is OPTIONAL (pulls numpy on some platforms; uses os.uname which
# fails on Windows). Import lazily so a missing/broken dep never kills the daemon
# at module load (forensic Layer-0: a self-upgrade loop must survive its own deps).
def _load_swarm():
    try:
        from swarm_protocol import SwarmProtocol
        return SwarmProtocol
    except Exception:
        return None


class _NullSwarm:
    """No-op stand-in so the daemon survives a missing/failed SwarmProtocol."""
    identity = type("I", (), {"agent_id": "guardian-offline"})()
    tasks_completed = 0
    errors_24h = 0

    def stop(self): pass
    def heartbeat(self): pass
    def heal_swarm(self): return None
    def discover_agents(self): return []
    def _git_push(self, *_a, **_k): pass'''
assert old1 in s, "old1"
s = s.replace(old1, new1, 1)

old2 = '''    def __init__(self):
        self.swarm = SwarmProtocol(
            agent_type="guardian",
            repo="blackhornet",
            version="6.3.0"
        )
        self.running = True
        self.cycles = 0
        self.health_log: List[Dict] = []

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum, frame):
        logger.info("Daemon shutting down...")
        self.running = False
        self.swarm.stop()'''
new2 = '''    def __init__(self):
        SwarmProtocol = _load_swarm()
        if SwarmProtocol is not None:
            try:
                self.swarm = SwarmProtocol(
                    agent_type="guardian",
                    repo="blackhornet",
                    version="6.3.0"
                )
            except Exception:
                self.swarm = _NullSwarm()
                logger.warning("SwarmProtocol init failed — running without swarm reporting")
        else:
            self.swarm = _NullSwarm()
            logger.warning("SwarmProtocol unavailable — running without swarm reporting")
        self.running = True
        self.cycles = 0
        self.health_log: List[Dict] = []

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum, frame):
        logger.info("Daemon shutting down...")
        self.running = False
        if self.swarm is not None:
            self.swarm.stop()'''
assert old2 in s, "old2"
s = s.replace(old2, new2, 1)

old3 = '''    def self_push(self, message: str = "[auto] daemon sync") -> bool:
        """Auto-commit and push changes to all remotes."""
        import subprocess
        repo_dir = BASE_DIR
        try:
            # Check for changes
            r = subprocess.run(["git", "-C", str(repo_dir), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=10)
            if not r.stdout.strip():
                return True  # Nothing to push

            # Stage all
            subprocess.run(["git", "-C", str(repo_dir), "add", "-A"],
                         capture_output=True, timeout=10)
            # Commit
            subprocess.run(["git", "-C", str(repo_dir), "commit", "-m", message],
                         capture_output=True, timeout=10)
            # Push to canonical GitHub remote (configured in repo) on main.
            # Uses GITHUB_TOKEN env / credential helper if set; degrades gracefully.
            token = os.getenv("GITHUB_TOKEN")
            remote_url = subprocess.run(
                ["git", "-C", str(repo_dir), "config", "--get", "remote.github.url"],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip() or "github"
            push_target = remote_url
            if token and push_target.startswith("https://"):
                # inject token into URL for this one push (no credential stored on disk)
                from urllib.parse import quote
                auth = f"https://x-access-token:{quote(token)}@"
                push_target = push_target.replace("https://", auth, 1)
            subprocess.run(
                ["git", "-C", str(repo_dir), "push", push_target, "main"],
                capture_output=True, timeout=60,
            )
            logger.info(f"✓ Auto-pushed to github/main: {message}")
            return True
        except Exception as e:
            logger.warning(f"Self-push failed: {e}")
            return False'''
new3 = '''    def _verify_before_publish(self, repo_dir: Path) -> bool:
        """Publish gate (security skill): never push code that doesn't compile.

        Compiles every .py under repo_dir. Returns True only if all compile.
        Cheap, dependency-free, deterministic — safe to run every self_push.
        """
        try:
            py_files = list(repo_dir.rglob("*.py"))
            if not py_files:
                return True
            for f in py_files:
                try:
                    py_compile.compile(str(f), doraise=True, quiet=1)
                except py_compile.PyCompileError as e:
                    logger.error(f"Publish gate FAIL: {f.name} — {e}")
                    return False
            return True
        except Exception as e:
            logger.warning(f"Publish gate error (treat as fail): {e}")
            return False

    def self_push(self, message: str = "[auto] daemon sync") -> bool:
        """Auto-commit and push to canonical GitHub remote on main.

        Publishes ONLY after the verification gate passes — a self-upgrade that
        ships broken code is a regression engine, not an upgrade.
        """
        import subprocess
        repo_dir = BASE_DIR
        try:
            r = subprocess.run(["git", "-C", str(repo_dir), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=10)
            if not r.stdout.strip():
                return True  # Nothing to push

            # ── PUBLISH GATE ──
            if not self._verify_before_publish(repo_dir):
                logger.error("Self-push ABORTED: verification gate failed — not publishing broken code")
                return False

            subprocess.run(["git", "-C", str(repo_dir), "add", "-A"],
                         capture_output=True, timeout=10)
            subprocess.run(["git", "-C", str(repo_dir), "commit", "-m", message],
                         capture_output=True, timeout=10)
            token = os.getenv("GITHUB_TOKEN")
            remote_url = subprocess.run(
                ["git", "-C", str(repo_dir), "config", "--get", "remote.github.url"],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip() or "github"
            push_target = remote_url
            if token and push_target.startswith("https://"):
                from urllib.parse import quote
                push_target = push_target.replace("https://",
                                                  f"https://x-access-token:{quote(token)}@", 1)
            res = subprocess.run(
                ["git", "-C", str(repo_dir), "push", push_target, "main"],
                capture_output=True, timeout=60,
            )
            if res.returncode != 0:
                logger.error(f"Self-push failed: {res.stderr.decode(errors='ignore')[:200]}")
                return False
            logger.info(f"✓ Auto-pushed to github/main: {message}")
            return True
        except Exception as e:
            logger.warning(f"Self-push failed: {e}")
            return False'''
assert old3 in s, "old3"
s = s.replace(old3, new3, 1)

open(p, "w").write(s)
print("ALL 3 EDITS APPLIED")
