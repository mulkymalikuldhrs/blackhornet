#!/usr/bin/env python3
import argparse
import json
import sys

def cmd_status(args):
    info = {"version": "0.1.0", "uptime": "3h12m", "status": "running"}
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print(f"Status: {info['status']} | Version: {info['version']} | Uptime: {info['uptime']}")

def cmd_swarm(args):
    info = {"nodes": 12, "active": 10, "draining": 2, "leader": "node-01"}
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print(f"Swarm: {info['active']}/{info['nodes']} active | Leader: {info['leader']}")

def cmd_health(args):
    info = {"status": "healthy", "checks": {"api": True, "db": True, "cache": True}}
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print(f"Health: {info['status']} | API: {info['checks']['api']} | DB: {info['checks']['db']} | Cache: {info['checks']['cache']}")

def cmd_colony(args):
    info = {"colonies": ["alpha", "beta", "gamma"], "region": "us-east-1"}
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print(f"Colonies: {', '.join(info['colonies'])} | Region: {info['region']}")

def main():
    parser = argparse.ArgumentParser(prog="blackhornet-cli")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    sub = parser.add_subparsers(dest="command")
    for name, func, help_text in [
        ("status", cmd_status, "Show system status"),
        ("swarm", cmd_swarm, "Show swarm node status"),
        ("health", cmd_health, "Show health checks"),
        ("colony", cmd_colony, "Show colony info"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
        p.set_defaults(func=func)
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)

if __name__ == "__main__":
    main()
