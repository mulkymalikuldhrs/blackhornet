#!/usr/bin/env python3
"""
BH ↔ QNA BRIDGE
===============
Connects BlackHornet AGI to Quant Nanggroe hedge fund.
BH can:
  - Query QNA market data and signals
  - Send investment decisions to QNA
  - Read QNA performance for self-evaluation
  - Use QNA signals as input for agent goals

Usage:
  python3 qna_bridge.py [action] [args]
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path

BH_DIR = Path(__file__).resolve().parent.parent.parent
QNA_DIR = BH_DIR.parent / "repositories" / "Quant-Nanggroe-AI-worktree"
DATA_DIR = BH_DIR / "data"
os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [BH-QNA] %(message)s")
log = logging.getLogger("BH-QNA")

QNA_ENGINE = QNA_DIR / "quant_nanggroe" / "live_engine.py"
CACHE_FILE = DATA_DIR / "qna-cache.json"


def _run_qna(action):
    if not QNA_ENGINE.exists():
        return {"error": f"QNA engine not found at {QNA_ENGINE}"}
    try:
        result = subprocess.run(
            [sys.executable, str(QNA_ENGINE), action],
            capture_output=True, text=True, timeout=30
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        return {"error": result.stderr.strip() or "empty response"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON from QNA", "raw": result.stdout[:500]}
    except subprocess.TimeoutExpired:
        return {"error": "QNA timeout"}
    except Exception as e:
        return {"error": str(e)}


def get_market_snapshot():
    cache = {}
    if CACHE_FILE.exists():
        cache = json.loads(CACHE_FILE.read_text())
    age = time.time() - cache.get("timestamp", 0) if cache else 999
    if age < 30:
        return cache
    data = _run_qna("dashboard")
    if "error" not in data:
        data["timestamp"] = time.time()
        CACHE_FILE.write_text(json.dumps(data, indent=2))
        return data
    return cache if cache else data


def get_signals(limit=5):
    data = get_market_snapshot()
    return data.get("recent_signals", [])[:limit]


def get_performance_summary():
    data = get_market_snapshot()
    return {
        "balance": data.get("balance", 0),
        "total_pnl": data.get("total_pnl", 0),
        "win_rate": data.get("win_rate", "0%"),
        "sharpe": data.get("sharpe_ratio", 0),
        "volatility": data.get("volatility", 0),
        "trades": data.get("total_trades", 0),
        "drawdown": data.get("drawdown", "0%"),
    }


def bh_decision_engine():
    """BH evaluates market and decides what to recommend to QNA."""
    perf = get_performance_summary()
    signals = get_signals()

    decision = {
        "timestamp": datetime.now().isoformat(),
        "bh_assessment": "neutral",
        "confidence": 0.5,
        "reasoning": [],
        "recommended_action": "hold",
    }

    if perf.get("sharpe", 1) < 0.5:
        decision["bh_assessment"] = "cautious"
        decision["reasoning"].append(f"Sharpe {perf['sharpe']:.2f} below threshold")
    if perf.get("drawdown", "0%").replace("%", "") > "10":
        decision["bh_assessment"] = "defensive"
        decision["reasoning"].append("High drawdown detected")

    recent_buys = sum(1 for s in signals if s.get("signal") == "buy")
    recent_sells = sum(1 for s in signals if s.get("signal") == "sell")

    if recent_buys > recent_sells * 2:
        decision["confidence"] = 0.7
        decision["recommended_action"] = "aggressive"
    elif recent_sells > recent_buys * 2:
        decision["confidence"] = 0.3
        decision["recommended_action"] = "defensive"

    if not decision["reasoning"]:
        decision["reasoning"].append(f"Normal conditions. Win rate: {perf['win_rate']}")

    return decision


def inject_bh_decision():
    """BH sends a decision to QNA via the signals table."""
    decision = bh_decision_engine()
    db_path = QNA_DIR / "data" / "qna_live.db"
    if not db_path.exists():
        log.warning("QNA database not found")
        return decision

    import sqlite3
    try:
        db = sqlite3.connect(str(db_path))
        db.execute(
            "INSERT INTO signals (symbol, strategy, signal, price, timestamp) VALUES (?,?,?,?,?)",
            ("BH_AGI", "BH_Decision", decision["recommended_action"],
             get_market_snapshot().get("portfolio_value", 0),
             datetime.now().isoformat())
        )
        db.commit()
        db.close()
        log.info(f"BH decision injected: {decision['recommended_action']} (confidence: {decision['confidence']})")
    except Exception as e:
        log.warning(f"Failed to inject decision: {e}")

    return decision


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BH↔QNA Bridge")
    parser.add_argument("action", choices=["market", "signals", "perf", "decide", "inject", "bridge"],
                        help="Action to perform")
    args = parser.parse_args()

    if args.action == "market":
        data = get_market_snapshot()
        if "error" in data:
            print(f"Error: {data['error']}")
        else:
            print(f"Portfolio: ${data.get('portfolio_value',0):.2f} | Balance: ${data.get('balance',0):.2f}")
            print(f"Assets: {json.dumps(data.get('assets',{}), indent=2)}")

    elif args.action == "signals":
        for s in get_signals(10):
            print(f"  [{s.get('strategy','?')}] {s.get('signal','?')} @ ${s.get('price',0):.2f}")

    elif args.action == "perf":
        p = get_performance_summary()
        for k, v in p.items():
            print(f"  {k}: {v}")

    elif args.action == "decide":
        d = bh_decision_engine()
        print(f"Assessment: {d['bh_assessment']}")
        print(f"Action: {d['recommended_action']} (confidence: {d['confidence']})")
        for r in d['reasoning']:
            print(f"  → {r}")

    elif args.action == "inject":
        d = inject_bh_decision()
        print(f"Injected: {d['recommended_action']} (confidence: {d['confidence']})")

    elif args.action == "bridge":
        log.info("BH↔QNA Bridge running (continuous)")
        cycle = 0
        while True:
            cycle += 1
            log.info(f"Bridge cycle {cycle}")
            inject_bh_decision()
            time.sleep(300)


if __name__ == "__main__":
    main()
