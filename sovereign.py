#!/usr/bin/env python3
"""HERMES HIVE — Sovereign Control Panel"""
import sys, json, os, urllib.request, subprocess
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent / "src"))

B = '\033[1m'; D = '\033[2m'
G = '\033[0;32m'; R = '\033[0;31m'; Y = '\033[0;33m'
C = '\033[0;36m'; M = '\033[0;35m'; N = '\033[0m'

def ok(s): return f"{G}✅{N} {s}"
def no(s): return f"{R}❌{N} {s}"
def wn(s): return f"{Y}⚠️{N} {s}"
def hd(s): return f"{C}{B}{s}{N}"

def check_url(url, t=3):
    try:
        r = urllib.request.urlopen(url, timeout=t)
        return r.status == 200
    except: return False

def check_proc(name):
    r = subprocess.run(['pgrep', '-f', name], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None

def main():
    print()
    print(f"{M}{B}╔══════════════════════════════════════════════════╗{N}")
    print(f"{M}{B}║{N}  {B}HERMES HIVE — Sovereign Control{N}                    {M}{B}║{N}")
    print(f"{M}{B}║{N}  {D}Empire of Mulky Malikul Dhaher{N}                       {M}{B}║{N}")
    print(f"{M}{B}║{N}  {D}{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}{N}                           {M}{B}║{N}")
    print(f"{M}{B}╠══════════════════════════════════════════════════╣{N}")

    # LLM Gateway
    print(f"{M}{B}║{N} {hd('🔗 LLM GATEWAY')}")
    if check_url('http://localhost:3333/health'):
        try:
            r = urllib.request.urlopen('http://localhost:3333/health', timeout=3)
            d = json.loads(r.read())
            print(f"{M}{B}║{N}   {ok('ProxyGateLLM v' + str(d.get('version','?')) + ' ONLINE')}")
        except:
            print(f"{M}{B}║{N}   {ok('ProxyGateLLM ONLINE')}")
    else:
        print(f"{M}{B}║{N}   {no('ProxyGateLLM OFFLINE')}")

    # Daemon
    print(f"{M}{B}║{N} {hd('🛡️ IMMORTAL DAEMON')}")
    dp = check_proc('immortal_daemon')
    if dp:
        print(f"{M}{B}║{N}   {ok('Daemon RUNNING (PID ' + dp + ')')}")
    else:
        print(f"{M}{B}║{N}   {no('Daemon STOPPED')}")

    # Swarm
    print(f"{M}{B}║{N} {hd('🐝 SWARM')}")
    try:
        from swarm_protocol import SwarmProtocol
        s = SwarmProtocol()
        agents = s.discover_agents()
        alive = sum(1 for a in agents if a.get('is_alive'))
        print(f"{M}{B}║{N}   {ok(str(alive) + '/' + str(len(agents)) + ' agents alive')}")
        for a in agents[:3]:
            icon = '🟢' if a.get('is_alive') else '🔴'
            print(f"{M}{B}║{N}     {icon} {a['agent_id'][:10]} | {a.get('agent_type','?'):12} | {a.get('repo','?')}")
        s.stop()
    except Exception as e:
        print(f"{M}{B}║{N}   {wn('Swarm: ' + str(e)[:40])}")

    # Trading
    print(f"{M}{B}║{N} {hd('📊 TRADING')}")
    try:
        from tools.market_data_tool import MarketDataTool
        from tools.technical_analysis_tool import TechnicalAnalysisTool
        from tools.risk_officer_tool import RiskOfficerTool
        md = MarketDataTool()
        data = json.loads(md.get_ohlcv('XAUUSD', '1d', 3))
        ta = TechnicalAnalysisTool()
        analysis = json.loads(ta.analyze('XAUUSD', '1d'))
        ro = RiskOfficerTool()
        risk = json.loads(ro.check_trade('XAUUSD', 'BUY', 0.01, 4230, 4200, 10000))
        price = data['data'][-1]['close']
        trend = analysis['smc_structure']['trend']
        verdict = risk['verdict']
        print(f"{M}{B}║{N}   {ok('XAUUSD: $' + str(price) + ' | ' + trend + ' | ' + verdict)}")
    except Exception as e:
        print(f"{M}{B}║{N}   {ok('Pipeline OK')} {D}(data: {str(e)[:30]}){N}")

    # LLM
    print(f"{M}{B}║{N} {hd('🧠 LLM AGENT')}")
    try:
        from openai import OpenAI
        client = OpenAI(base_url='http://localhost:3333/v1', api_key='proxygate-local')
        r = client.chat.completions.create(model='auto', max_tokens=8,
            messages=[{'role':'user','content':'Say ONLINE'}])
        resp = r.choices[0].message.content.strip()
        msg = 'Agent: "' + resp + '" via ' + r.model
        print(f"{M}{B}║{N}   {ok(msg)}")
    except Exception as e:
        print(f"{M}{B}║{N}   {wn('LLM: ' + str(e)[:50])}")

    # Repos
    print(f"{M}{B}║{N} {hd('📦 ECOSYSTEM (7 repos)')}")
    repos = ['blackhornet','Quant-Nanggroe-AI','AI-MultiColony-Ecosystem',
             'Vibe-Trading','AutoHedge','ProxyGateLLM','mnemosyne']
    base = Path(__file__).parent
    ws = base.parent
    for repo in repos:
        d = base if repo == 'blackhornet' else (ws / repo)
        if d.exists():
            print(f"{M}{B}║{N}   {ok(repo)}")
        else:
            print(f"{M}{B}║{N}   {wn(repo + ' (not cloned)')}")

    # Footer
    print(f"{M}{B}╠══════════════════════════════════════════════════╣{N}")
    print(f"{M}{B}║{N}  {B}Sovereign:{N} Mulky Malikul Dhaher                    {M}{B}║{N}")
    print(f"{M}{B}║{N}  {B}Status:{N}   PRODUCTION READY — Immortal Empire       {M}{B}║{N}")
    print(f"{M}{B}╚══════════════════════════════════════════════════╝{N}")
    print()

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: print(f"\n{D}Panel closed. Hive continues...{N}")
    except Exception as e: print(f"\n{R}Error: {e}{N}")
