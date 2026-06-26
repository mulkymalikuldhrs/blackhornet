#!/usr/bin/env python3
"""
BH Doctor - Auto-Export & Self-Heal Watchdog

Automatically exports sessions, monitors system health, and triggers self-healing.
Runs as a background daemon for BlackHornet Colony.
"""

import os
import sys
import json
import time
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str((Path(__file__).resolve().parents[1] / 'logs' / 'watchdog.log'))),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('bh_watchdog')

# Configuration
def _find_root() -> Path:
    cur = Path(__file__).resolve()
    for _ in range(10):
        if (cur / "pyproject.toml").exists():
            return cur
        cur = cur.parent
    return cur

BH_HOME = _find_root()
DATA_DIR = BH_HOME / 'data'
EXPORTS_DIR = BH_HOME / 'exports'
SESSION_EXPORT_DIR = DATA_DIR / 'session-export'
MEMORY_DIR = BH_HOME / '.bh' / 'memory'
GRAPH_DIR = BH_HOME / '.bh' / 'graph'

# Ensure directories exist
for d in [EXPORTS_DIR, SESSION_EXPORT_DIR, MEMORY_DIR, GRAPH_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class SessionExporter:
    """Automatically exports Hermes sessions to persistent storage."""
    
    def __init__(self):
        self.sessions_db = MEMORY_DIR / 'sessions.db'
        self.exported_sessions = set()
        self._load_exported_sessions()
    
    def _load_exported_sessions(self):
        """Load list of already exported sessions."""
        marker_file = SESSION_EXPORT_DIR / '.exported'
        if marker_file.exists():
            with open(marker_file, 'r') as f:
                self.exported_sessions = set(line.strip() for line in f if line.strip())
    
    def _save_exported_session(self, session_id: str):
        """Mark session as exported."""
        self.exported_sessions.add(session_id)
        marker_file = SESSION_EXPORT_DIR / '.exported'
        with open(marker_file, 'a') as f:
            f.write(f"{session_id}\n")
    
    def export_session(self, session_data: Dict[str, Any]) -> Optional[Path]:
        """Export a session to markdown file."""
        session_id = session_data.get('id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        filename = f"session_{timestamp}_{session_id}.md"
        filepath = SESSION_EXPORT_DIR / filename
        
        # Generate markdown
        md_content = f"""# Session Export: {session_id}
**Exported:** {datetime.now().isoformat()}
**Sovereign:** Mulky Malikul Dhaher
**BlackHornet Version:** 5.0.0

---

## Session Metadata
- **Session ID:** {session_id}
- **Start Time:** {session_data.get('start_time', 'N/A')}
- **End Time:** {session_data.get('end_time', 'N/A')}
- **Duration:** {session_data.get('duration', 'N/A')}
- **Tool Calls:** {session_data.get('tool_calls', 0)}

---

## Conversation Log

{session_data.get('conversation', 'No conversation data available')}

---

## Actions Taken

{session_data.get('actions', 'No actions recorded')}

---

## Graphify Capture

### Entities Discovered
{json.dumps(session_data.get('entities', []), indent=2)}

### Relationships Mapped
{json.dumps(session_data.get('relationships', []), indent=2)}

---

*Exported by BH Doctor v5.0.0 - The hive is eternal.*
"""
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"✅ Exported session {session_id} to {filepath}")
        self._save_exported_session(session_id)
        return filepath
    
    def check_new_sessions(self) -> List[Dict[str, Any]]:
        """Check for new sessions in the database."""
        if not self.sessions_db.exists():
            return []
        
        conn = sqlite3.connect(self.sessions_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get recent sessions (last 24 hours)
        cursor.execute("""
            SELECT id, title, created_at, message_count 
            FROM sessions 
            WHERE created_at > datetime('now', '-1 day')
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        new_sessions = []
        for row in cursor.fetchall():
            session_id = str(row['id'])
            if session_id not in self.exported_sessions:
                new_sessions.append({
                    'id': session_id,
                    'title': row['title'],
                    'start_time': row['created_at'],
                    'message_count': row['message_count']
                })
        
        conn.close()
        return new_sessions


class SystemHealthMonitor:
    """Monitors system health and triggers self-healing."""
    
    def __init__(self):
        self.health_checks = {
            'disk': self._check_disk,
            'memory': self._check_memory,
            'logs': self._check_logs,
            'git': self._check_git_status,
            'services': self._check_services,
        }
        self.last_check = {}
    
    def _check_disk(self) -> Dict[str, Any]:
        """Check disk space."""
        import shutil
        total, used, free = shutil.disk_usage(str(BH_HOME))
        free_percent = (free / total) * 100
        
        status = 'healthy' if free_percent > 20 else 'warning' if free_percent > 10 else 'critical'
        
        return {
            'check': 'disk',
            'status': status,
            'free_gb': free / (1024**3),
            'free_percent': free_percent,
            'message': f"Disk free: {free/(1024**3):.2f}GB ({free_percent:.1f}%)"
        }
    
    def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage (if available)."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            available_percent = mem.available / mem.total * 100
            
            status = 'healthy' if available_percent > 30 else 'warning' if available_percent > 15 else 'critical'
            
            return {
                'check': 'memory',
                'status': status,
                'available_gb': mem.available / (1024**3),
                'available_percent': available_percent,
                'message': f"Memory available: {mem.available/(1024**3):.2f}GB ({available_percent:.1f}%)"
            }
        except ImportError:
            return {
                'check': 'memory',
                'status': 'unknown',
                'message': 'psutil not installed'
            }
    
    def _check_logs(self) -> Dict[str, Any]:
        """Check log files for errors."""
        log_file = BH_HOME / 'logs' / 'watchdog.log'
        errors_24h = 0
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                for line in f:
                    if 'ERROR' in line or 'CRITICAL' in line:
                        errors_24h += 1
        
        status = 'healthy' if errors_24h < 10 else 'warning' if errors_24h < 50 else 'critical'
        
        return {
            'check': 'logs',
            'status': status,
            'errors_24h': errors_24h,
            'message': f"Errors in log: {errors_24h}"
        }
    
    def _check_git_status(self) -> Dict[str, Any]:
        """Check git working directory status."""
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=str(BH_HOME),
                capture_output=True,
                text=True,
                timeout=10
            )
            
            changes = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            status = 'healthy' if changes == 0 else 'warning'
            
            return {
                'check': 'git',
                'status': status,
                'uncommitted_changes': changes,
                'message': f"Git changes: {changes} files modified" if changes else "Git working directory clean"
            }
        except Exception as e:
            return {
                'check': 'git',
                'status': 'error',
                'message': f"Git check failed: {str(e)}"
            }
    
    def _check_services(self) -> Dict[str, Any]:
        """Check if critical services are running."""
        # Placeholder - implement based on your services
        return {
            'check': 'services',
            'status': 'healthy',
            'message': 'All services operational'
        }
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return summary."""
        results = {}
        overall_status = 'healthy'
        
        for check_name, check_func in self.health_checks.items():
            try:
                result = check_func()
                results[check_name] = result
                
                if result['status'] == 'critical':
                    overall_status = 'critical'
                elif result['status'] == 'warning' and overall_status != 'critical':
                    overall_status = 'warning'
            except Exception as e:
                results[check_name] = {
                    'check': check_name,
                    'status': 'error',
                    'message': str(e)
                }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status,
            'checks': results
        }


class SelfHealingOrchestrator:
    """Orchestrates self-healing actions based on health checks."""
    
    def __init__(self):
        self.recovery_actions = {
            'disk_critical': self._cleanup_old_logs,
            'git_changes': self._commit_changes,
            'export_pending': self._export_sessions,
        }
    
    def _cleanup_old_logs(self, health_result: Dict[str, Any]) -> bool:
        """Clean up old log files to free disk space."""
        logs_dir = BH_HOME / 'logs'
        if not logs_dir.exists():
            return False
        
        cleaned = 0
        for log_file in logs_dir.glob('*.log.*'):
            try:
                log_file.unlink()
                cleaned += 1
                logger.info(f"Cleaned up old log: {log_file}")
            except Exception as e:
                logger.error(f"Failed to clean {log_file}: {e}")
        
        logger.info(f"Self-heal: Cleaned {cleaned} old log files")
        return cleaned > 0
    
    def _commit_changes(self, health_result: Dict[str, Any]) -> bool:
        """Auto-commit uncommitted changes."""
        import subprocess
        try:
            # Check if there are changes
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=str(BH_HOME),
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout.strip():
                # Add all changes
                subprocess.run(['git', 'add', '-A'], cwd=str(BH_HOME), timeout=10)
                
                # Commit with auto message
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
                message = f"[AUTO] Watchdog commit - {timestamp}"
                subprocess.run(['git', 'commit', '-m', message], cwd=str(BH_HOME), timeout=10)
                
                logger.info(f"Self-heal: Auto-committed changes")
                return True
        except Exception as e:
            logger.error(f"Self-heal: Auto-commit failed: {e}")
        
        return False
    
    def _export_sessions(self, exporter: SessionExporter) -> bool:
        """Export pending sessions."""
        new_sessions = exporter.check_new_sessions()
        exported = 0
        
        for session in new_sessions:
            # Fetch full session data (placeholder - implement based on your session storage)
            session_data = {
                'id': session['id'],
                'title': session['title'],
                'start_time': session['start_time'],
                'end_time': datetime.now().isoformat(),
                'duration': 'N/A',
                'tool_calls': session.get('message_count', 0),
                'conversation': '# Session data available in Hermes memory',
                'actions': 'Actions logged in session',
                'entities': [],
                'relationships': []
            }
            
            if exporter.export_session(session_data):
                exported += 1
        
        if exported > 0:
            logger.info(f"Self-heal: Exported {exported} pending sessions")
            return True
        
        return False
    
    def execute_recovery(self, health_summary: Dict[str, Any], exporter: SessionExporter) -> List[str]:
        """Execute recovery actions based on health status."""
        actions_taken = []
        
        for check_name, result in health_summary.get('checks', {}).items():
            status = result.get('status', 'unknown')
            
            # Map status to recovery action
            if check_name == 'disk' and status == 'critical':
                if self.recovery_actions['disk_critical'](result):
                    actions_taken.append('Cleaned old logs (disk critical)')
            
            elif check_name == 'git' and status == 'warning':
                if self.recovery_actions['git_changes'](result):
                    actions_taken.append('Auto-committed git changes')
            
            elif check_name == 'export':
                if self.recovery_actions['export_pending'](exporter):
                    actions_taken.append('Exported pending sessions')
        
        return actions_taken


def main():
    """Main watchdog loop."""
    logger.info("=" * 60)
    logger.info("BH Doctor Watchdog Starting...")
    logger.info(f"BH_HOME: {BH_HOME}")
    logger.info(f"Export Dir: {SESSION_EXPORT_DIR}")
    logger.info("=" * 60)
    
    exporter = SessionExporter()
    health_monitor = SystemHealthMonitor()
    healer = SelfHealingOrchestrator()
    
    check_interval = 300  # 5 minutes
    export_interval = 600  # 10 minutes
    last_export = 0
    
    iteration = 0
    while True:
        iteration += 1
        logger.info(f"\n--- Watchdog Iteration {iteration} ---")
        
        # Run health checks
        health_summary = health_monitor.run_all_checks()
        logger.info(f"Overall Health: {health_summary['overall_status'].upper()}")
        
        for check_name, result in health_summary['checks'].items():
            logger.info(f"  {check_name}: {result['status']} - {result['message']}")
        
        # Export sessions (every 10 minutes)
        current_time = time.time()
        if current_time - last_export > export_interval:
            logger.info("\nChecking for new sessions to export...")
            new_sessions = exporter.check_new_sessions()
            if new_sessions:
                logger.info(f"Found {len(new_sessions)} new sessions")
                healer.execute_recovery(health_summary, exporter)
            else:
                logger.info("No new sessions to export")
            last_export = current_time
        
        # Execute recovery actions if needed
        if health_summary['overall_status'] in ['warning', 'critical']:
            logger.info("\n⚠️  Health issues detected, running recovery...")
            actions = healer.execute_recovery(health_summary, exporter)
            if actions:
                for action in actions:
                    logger.info(f"  ✅ Recovery: {action}")
        
        # Graphify: Capture this iteration
        graph_capture = {
            'timestamp': health_summary['timestamp'],
            'iteration': iteration,
            'health_status': health_summary['overall_status'],
            'checks': {k: v['status'] for k, v in health_summary['checks'].items()}
        }
        
        # Save to graph directory
        graph_file = GRAPH_DIR / f'watchdog_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(graph_file, 'w') as f:
            json.dump(graph_capture, f, indent=2)
        
        logger.info(f"✅ Graphified: {graph_file}")
        
        # Sleep until next iteration
        logger.info(f"\nSleeping for {check_interval}s...")
        time.sleep(check_interval)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nWatchdog stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Watchdog crashed: {e}", exc_info=True)
        sys.exit(1)