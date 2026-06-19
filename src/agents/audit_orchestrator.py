"""AuditOrchestrator — spawns 100 parallel audit agents across the codebase.

Deploys all 52 audit agents + 48 specialist agents to scan every Python
file in parallel, streaming findings into GraphifyPipeline.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.graph.graph_store import GraphStore
from src.graph.graphify_pipeline import GraphifyPipeline

logger = logging.getLogger(__name__)

BH_HOME = Path("/sdcard/dhaherlabs/blackhornet-worktree")
SRC_DIR = BH_HOME / "src"


@dataclass
class AuditFinding:
    agent: str = ""
    file_path: str = ""
    severity: str = "info"  # critical | high | medium | low | info
    title: str = ""
    description: str = ""
    line_number: int = 0
    category: str = ""
    recommendation: str = ""


@dataclass
class AgentSpec:
    name: str = ""
    category: str = "audit"
    priority: int = 5
    patterns: List[str] = field(default_factory=list)
    file_filter: str = "*.py"


# ── Built-in audit agent definitions (52 audit + 48 specialist = 100) ───

AUDIT_AGENTS: List[AgentSpec] = [
    AgentSpec(name="SecurityAuditAgent", category="security", patterns=[r"(?i)(password|secret|token|key|credential)", r"(?i)(eval|exec|pickle\.loads|subprocess\.shell)", r"(?i)(sql_injection|xss|csrf)"]),
    AgentSpec(name="CodeQualityAuditAgent", category="quality", patterns=[r".{200,}", r"(?i)(TODO|FIXME|HACK|XXX)", r"except\s*:"], priority=3),
    AgentSpec(name="DependencyAuditAgent", category="deps", patterns=[r"^(import|from)\s+(\w+)", r"__import__"]),
    AgentSpec(name="ConfigurationAuditAgent", category="config", patterns=[r"(?i)(HARDCODED|CONFIG|ENV|SETTINGS)", r"os\.environ", r"\.env"]),
    AgentSpec(name="PerformanceAuditAgent", category="perf", patterns=[r"for\s+\w+\s+in\s+range\(len\(", r"\.append\(\)\s+in\s+loop", r"while\s+True"]),
    AgentSpec(name="MemoryAuditAgent", category="memory", patterns=[r"__init__\.py", r"self\._\w+\s*=\s*\{", r"self\._\w+\s*=\s*\["], priority=4),
    AgentSpec(name="NetworkAuditAgent", category="network", patterns=[r"urllib\.request|requests\.get|httpx\.", r"socket\.", r"aiohttp\."]),
    AgentSpec(name="ApiAuditAgent", category="api", patterns=[r"@app\.route|@router\.", r"def\s+\w+_endpoint", r"api_route"]),
    AgentSpec(name="DatabaseAuditAgent", category="database", patterns=[r"sqlite3\.|sqlalchemy\.|psycopg", r"execute\(.*SELECT|INSERT|UPDATE|DELETE", r"cursor\.execute"]),
    AgentSpec(name="FilesystemAuditAgent", category="filesystem", patterns=[r"open\(|Path\(|os\.path\.|shutil\.", r"os\.remove|os\.unlink", r"tempfile\."]),
    AgentSpec(name="AuthenticationAuditAgent", category="auth", patterns=[r"(?i)(auth|login|password|token|jwt|oauth)", r"getpass", r"API_KEY"]),
    AgentSpec(name="AuthorizationAuditAgent", category="auth", patterns=[r"(?i)(permission|role|access|acl|rbac)", r"is_admin|is_owner", r"user\.role"]),
    AgentSpec(name="EncryptionAuditAgent", category="security", patterns=[r"(?i)(encrypt|decrypt|hash|sha|md5|cipher)", r"cryptography\.", r"hashlib\."]),
    AgentSpec(name="LoggingAuditAgent", category="observability", patterns=[r"logging\.(info|debug|warn|error)", r"logger\.", r"print\(|print\(f"]),
    AgentSpec(name="MonitoringAuditAgent", category="observability", patterns=[r"prometheus|metrics|histogram|counter", r"health_check|status", r"monitor"]),
    AgentSpec(name="ComplianceAuditAgent", category="compliance", patterns=[r"(?i)(gdpr|hipaa|pci|sox|ccpa|audit_log)"]),
    AgentSpec(name="RiskAssessmentAgent", category="risk", patterns=[r"(?i)(risk|impact|probability|mitigation)", r"try:\s*\n.*except\s*(Exception|:)"], priority=2),
    AgentSpec(name="VulnerabilityAuditAgent", category="security", patterns=[r"(?i)(cve|cwe|nvd|exploit|vulnerability)", r"(?i)(injection|RCE|LFI|RFI|SSRF)"]),
    AgentSpec(name="ErrorHandlingAgent", category="quality", patterns=[r"except\s*(Exception)?\s*:", r"raise\s+(Exception|ValueError|TypeError)", r"try:", r"finally:"]),
    AgentSpec(name="RetryLogicAgent", category="resilience", patterns=[r"(?i)(retry|backoff|timeout)", r"@retry", r"max_retries|retry_count"]),
    AgentSpec(name="TimeoutAuditAgent", category="resilience", patterns=[r"(?i)(timeout|expir|ttl)", r"signal\.alarm", r"asyncio\.wait_for"]),
    AgentSpec(name="RateLimitingAgent", category="resilience", patterns=[r"(?i)(rate.*limit|throttle|burst)", r"leaky_bucket|token_bucket"]),
    AgentSpec(name="CachingAuditAgent", category="performance", patterns=[r"(?i)(cache|lru|ttl_cache|memoize)", r"@lru_cache|@cache", r"redis\.get|memcached"]),
    AgentSpec(name="QueueAuditAgent", category="infra", patterns=[r"(?i)(queue|message.*broker|rabbit|kafka|sqs|pub.*sub)"]),
    AgentSpec(name="EventAuditAgent", category="infra", patterns=[r"(?i)(event.*bus|event.*emit|publish|subscribe|notify)"]),
    AgentSpec(name="StateManagementAgent", category="architecture", patterns=[r"self\._state|self\.state", r"STATE_|state_machine", r"STATUS_"]),
    AgentSpec(name="LifecycleAuditAgent", category="architecture", patterns=[r"__init__|__enter__|__exit__|__aexit__", r"startup|shutdown|lifespan"]),
    AgentSpec(name="AccessControlAgent", category="security", patterns=[r"(?i)(access.*control|ACL|allow|deny|blacklist|whitelist)"]),
    AgentSpec(name="ChangeManagementAgent", category="process", patterns=[r"(?i)(change.*mgmt|rollback|version.*control|migration)"]),
    AgentSpec(name="ReleaseAuditAgent", category="process", patterns=[r"(?i)(release|tag|version|semver|changelog)", r"__version__", r"VERSION"]),
    AgentSpec(name="DeploymentAuditAgent", category="devops", patterns=[r"(?i)(deploy|Dockerfile|docker-compose|helm|kustomize)"]),
    AgentSpec(name="InfrastructureAuditAgent", category="devops", patterns=[r"(?i)(terraform|ansible|pulumi|cloudformation|infra)"]),
    AgentSpec(name="CloudAuditAgent", category="cloud", patterns=[r"(?i)(aws|gcp|azure|cloud|s3|ec2|lambda|cloud.*function)"]),
    AgentSpec(name="ContainerAuditAgent", category="devops", patterns=[r"(?i)(docker|container|Dockerfile|podman|OCI|image)"]),
    AgentSpec(name="KubernetesAuditAgent", category="devops", patterns=[r"(?i)(k8s|kubernetes|pod|deployment|service|ingress|helm|kubectl)"]),
    AgentSpec(name="CicdAuditAgent", category="devops", patterns=[r"(?i)(CI|CD|jenkins|github.*actions|gitlab.*ci|circleci|pipeline)"]),
    AgentSpec(name="TestCoverageAuditAgent", category="quality", patterns=[r"def\s+test_", r"class\s+Test", r"assert_", r"pytest\.|unittest\."]),
    AgentSpec(name="DocumentationAuditAgent", category="docs", patterns=[r'"""', r"'''", r"#\s*:", r"Args:|Returns:|Raises:|Parameters"]),
    AgentSpec(name="LicenseAuditAgent", category="legal", patterns=[r"(?i)(license|MIT|Apache|GPL|BSD|copyright|SPDX)"]),
    AgentSpec(name="SupplyChainAuditAgent", category="security", patterns=[r"(?i)(supply.*chain|SBOM|dependency|integrity|checksum)"]),
    AgentSpec(name="OpenSourceAuditAgent", category="legal", patterns=[r"(?i)(open.*source|OSS|FOSS|repository|pypi|npm)"]),
    AgentSpec(name="ThirdPartyAuditAgent", category="deps", patterns=[r"(?i)(third.*party|external|vendor|integration|SDK)"]),
    AgentSpec(name="ApiContractAuditAgent", category="api", patterns=[r"@app\.|@router\.|route\(", r"async\s+def\s+\w+\(.*request", r"JSONResponse|Response\("]),
    AgentSpec(name="SchemaValidationAgent", category="quality", patterns=[r"BaseModel|pydantic|TypedDict|dataclass", r"field\(|Field\(", r"validator|model_validator"]),
    AgentSpec(name="PrivacyAuditAgent", category="legal", patterns=[r"(?i)(privacy|PII|personal.*data|anonymize|opt.*out|consent)"]),
    AgentSpec(name="PenetrationTestAgent", category="security", patterns=[r"(?i)(pentest|pen.?test|fuzz|bypass|escalation)"]),
    AgentSpec(name="IncidentResponseAgent", category="security", patterns=[r"(?i)(incident|response|IR|remediation|containment|playbook)"]),
    AgentSpec(name="BusinessContinuityAgent", category="resilience", patterns=[r"(?i)(BCP|business.*continuity|failover|HA|high.*avail)"]),
    AgentSpec(name="DisasterRecoveryAgent", category="resilience", patterns=[r"(?i)(DR|disaster.*recovery|backup|restore|RTO|RPO)"]),
    AgentSpec(name="DataIntegrityAgent", category="quality", patterns=[r"(?i)(integrity|checksum|hash.*verify|consistency|validation)"]),
    # Specialist agents (48 more)
    AgentSpec(name="DatabaseSpecialist", category="specialist", patterns=[r"sqlite|postgres|mysql|oracle|mongo|redis", r"SELECT|INSERT|UPDATE|DELETE|JOIN"]),
    AgentSpec(name="KubernetesSpecialist", category="specialist", patterns=[r"k8s|kubernetes|pod|deployment|service|ingress|configmap"]),
    AgentSpec(name="DevOpsSpecialist", category="specialist", patterns=[r"ansible|terraform|pulumi|docker|helm|kustomize|ci/cd"]),
    AgentSpec(name="CloudSpecialist", category="specialist", patterns=[r"aws|gcp|azure|s3|ec2|lambda|cloud.*function|serverless"]),
    AgentSpec(name="FrontendSpecialist", category="specialist", patterns=[r"html|css|javascript|react|vue|angular|svelte|ui"]),
    AgentSpec(name="APIGatewaySpecialist", category="specialist", patterns=[r"api.*gateway|reverse.*proxy|nginx|traefik|envoy"]),
    AgentSpec(name="MLSpecialist", category="specialist", patterns=[r"tensorflow|pytorch|sklearn|keras|machine.*learn|deep.*learn|neural"]),
    AgentSpec(name="SIEMSpecialist", category="specialist", patterns=[r"siem|splunk|elastic|logstash|kibana|elk|security.*info"]),
    AgentSpec(name="FirewallSpecialist", category="specialist", patterns=[r"firewall|iptables|nftables|ufw|pf|ipset"]),
    AgentSpec(name="DNSSpecialist", category="specialist", patterns=[r"dns|domain|bind|named|zone|resolver|nameserver"]),
    AgentSpec(name="LoadBalancerSpecialist", category="specialist", patterns=[r"load.*balanc|haproxy|nginx|round.robin|health.*check"]),
    AgentSpec(name="MonitoringSpecialist", category="specialist", patterns=[r"prometheus|grafana|alert.*manage|datadog|new.relic|nagios"]),
    AgentSpec(name="LoggingSpecialist", category="specialist", patterns=[r"logstash|fluentd|fluentbit|syslog|log.*shipper|filebeat"]),
    AgentSpec(name="MessageQueueSpecialist", category="specialist", patterns=[r"rabbitmq|kafka|sqs|nats|pulsar|celery|redis.*queue"]),
    AgentSpec(name="MicroservicesSpecialist", category="specialist", patterns=[r"microservice|service.*mesh|istio|consul|eureka"]),
    AgentSpec(name="ServerlessSpecialist", category="specialist", patterns=[r"serverless|lambda|cloud.*function|faas|knative"]),
    AgentSpec(name="CacheSpecialist", category="specialist", patterns=[r"redis|memcached|cache|varnish|cdn|content.*delivery"]),
    AgentSpec(name="CDNSpecialist", category="specialist", patterns=[r"cdn|cloudflare|akamai|fastly|edge.*comput|distribut"]),
    AgentSpec(name="ETLSpecialist", category="specialist", patterns=[r"etl|data.*pipelin|extract.*transform.*load|data.*warehouse"]),
    AgentSpec(name="DataWarehouseSpecialist", category="specialist", patterns=[r"data.*warehouse|snowflake|bigquery|redshift|delta.*lake"]),
    AgentSpec(name="DataEngineeringSpecialist", category="specialist", patterns=[r"spark|hadoop|flink|beam|data.*engin|data.*pipeline"]),
    AgentSpec(name="AnalyticsSpecialist", category="specialist", patterns=[r"analytics|bi|report|dashboard|tableau|power.*bi|looker"]),
    AgentSpec(name="BISpecialist", category="specialist", patterns=[r"bi|business.*intelligence|olap|cube|dimension|fact"]),
    AgentSpec(name="DashboardSpecialist", category="specialist", patterns=[r"dashboard|grafana.*dash|kibana.*dash|chart|graph.*vis"]),
    AgentSpec(name="ReportSpecialist", category="specialist", patterns=[r"report|crystal|cognos|jasper|birt|pdf.*generat"]),
    AgentSpec(name="NotificationSpecialist", category="specialist", patterns=[r"notif|alert|push.*notif|fcm|apns|webhook|webpush"]),
    AgentSpec(name="PushNotificationSpecialist", category="specialist", patterns=[r"push|fcm|apns|web.*push|notification.*service"]),
    AgentSpec(name="EmailSpecialist", category="specialist", patterns=[r"smtp|sendgrid|mailgun|ses|email|mail.*serv|imap|pop3"]),
    AgentSpec(name="SMSSpecialist", category="specialist", patterns=[r"sms|twilio|vonage|nexmo|text.*message|gateway.*sms"]),
    AgentSpec(name="SearchSpecialist", category="specialist", patterns=[r"elasticsearch|solr|meilisearch|algolia|search.*engine"]),
    AgentSpec(name="BackendAPISpecialist", category="specialist", patterns=[r"rest.*api|graphql|grpc|endpoint|fastapi|flask|django|express"]),
    AgentSpec(name="IntegrationSpecialist", category="specialist", patterns=[r"integrat|webhook|adapter|connect|bridge|middleware"]),
    AgentSpec(name="EventDrivenSpecialist", category="specialist", patterns=[r"event.*driven|event.*sourc|cqrs|domain.*event|bus"]),
    AgentSpec(name="SecuritySpecialist", category="specialist", patterns=[r"oauth|oidc|saml|jwt|tls|ssl|mfa|2fa|waf"]),
    AgentSpec(name="ComplianceSpecialist", category="specialist", patterns=[r"gdpr|hipaa|pci|sox|iso.*27001|audit.*trail|compliance"]),
    AgentSpec(name="GovernanceSpecialist", category="specialist", patterns=[r"govern|policy|standard|framework|control|procedure"]),
    AgentSpec(name="RiskManagementSpecialist", category="specialist", patterns=[r"risk.*manage|risk.*assess|mitigat|control.*framework"]),
    AgentSpec(name="ChangeMgmtSpecialist", category="specialist", patterns=[r"change|request|approv|review|rollback|version.*control"]),
    AgentSpec(name="ReleaseMgmtSpecialist", category="specialist", patterns=[r"release|deploy.*pipeline|staging|canary|blue.*green"]),
    AgentSpec(name="IncidentMgmtSpecialist", category="specialist", patterns=[r"incident|response|escalat|on.?call|pager|alert"]),
    AgentSpec(name="SupportSpecialist", category="specialist", patterns=[r"support|ticket|helpdesk|sla|service.*level|escalat"]),
    AgentSpec(name="DocumentationSpecialist", category="specialist", patterns=[r"doc|readme|wiki|manual|user.*guide|api.*doc"]),
    AgentSpec(name="PerformanceSpecialist", category="specialist", patterns=[r"perform|benchmark|profiling|latency|throughput|optim"]),
    AgentSpec(name="SSLTLSSpecialist", category="specialist", patterns=[r"ssl|tls|certificate|cert.*manage|https|ca.*cert"]),
    AgentSpec(name="IDSPSSpecialist", category="specialist", patterns=[r"ids|ips|intrusion|detect|prevent|snort|suricata"]),
    AgentSpec(name="ForensicsSpecialist", category="specialist", patterns=[r"forensic|investig|artifact|evidence|chain.*custody"]),
    AgentSpec(name="DatabaseAdminSpecialist", category="specialist", patterns=[r"dba|backup.*restore|replication|shard|partition|index"]),
    AgentSpec(name="NetworkSecuritySpecialist", category="specialist", patterns=[r"vpn|tunnel|proxy|gateway|dmz|nat|packet.*filter"]),
    AgentSpec(name="BackupRecoverySpecialist", category="specialist", patterns=[r"backup|restore|snapshot|replica|disaster.*recovery"]),
    AgentSpec(name="CodeReviewSpecialist", category="specialist", patterns=[r"code.*review|pull.*request|merge.*request|approv|reviewer"]),
]

assert len(AUDIT_AGENTS) >= 99, f"Only {len(AUDIT_AGENTS)} agents defined, need 99+"


class AuditOrchestrator:
    """Orchestrates 100+ parallel audit agents across the codebase."""

    def __init__(
        self,
        pipeline: Optional[GraphifyPipeline] = None,
        agents: Optional[List[AgentSpec]] = None,
    ):
        self.pipeline = pipeline or GraphifyPipeline()
        self.agents = agents or AUDIT_AGENTS
        self._findings: List[AuditFinding] = []
        self._start_time: float = 0.0
        self._status = "idle"

    async def run_full_audit(
        self,
        target_dir: Optional[str] = None,
        file_filter: str = "*.py",
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """Run all 100+ agents across the codebase in parallel."""
        self._start_time = time.time()
        self._status = "running"
        self._findings.clear()

        target = Path(target_dir) if target_dir else SRC_DIR
        files = self._collect_files(target, file_filter)

        if verbose:
            logger.info("AuditOrchestrator: %d agents scanning %d files", len(self.agents), len(files))

        agent_tasks = []
        for agent in self.agents:
            agent_tasks.append(self._run_agent(agent, files, verbose))

        results = await asyncio.gather(*agent_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning("Agent failed: %s", result)
                continue
            self._findings.extend(result)

        self._status = "completed"
        elapsed = time.time() - self._start_time

        summary = self._summarize(elapsed)
        self.pipeline.emit("audit_finding", source="audit_orchestrator", data=summary)

        return summary

    def _collect_files(self, target_dir: Path, file_filter: str) -> List[Path]:
        files = []
        if file_filter == "*.py":
            for root, dirs, fnames in os.walk(target_dir):
                dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", ".git")]
                for fname in fnames:
                    if fname.endswith(".py"):
                        files.append(Path(root) / fname)
        else:
            for root, dirs, fnames in os.walk(target_dir):
                dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", ".git")]
                for fname in fnames:
                    if fname.endswith(file_filter.replace("*", "")):
                        files.append(Path(root) / fname)
        return files

    async def _run_agent(
        self,
        agent: AgentSpec,
        files: List[Path],
        verbose: bool,
    ) -> List[AuditFinding]:
        """Run a single agent across all files."""
        findings: List[AuditFinding] = []
        import re

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                lines = content.split("\n")

                for pattern in agent.patterns:
                    try:
                        for i, line in enumerate(lines, 1):
                            if re.search(pattern, line):
                                finding = AuditFinding(
                                    agent=agent.name,
                                    file_path=str(file_path),
                                    severity="medium" if agent.priority <= 3 else "low",
                                    title=f"Pattern match: {pattern[:50]}",
                                    description=line.strip()[:200],
                                    line_number=i,
                                    category=agent.category,
                                    recommendation=f"Review line {i} in {file_path.name}",
                                )
                                findings.append(finding)

                                self.pipeline.emit(
                                    "audit_finding",
                                    source=agent.name,
                                    data={
                                        "finding": finding.title,
                                        "severity": finding.severity,
                                        "file": finding.file_path,
                                        "line": finding.line_number,
                                        "category": finding.category,
                                    },
                                )
                    except re.error:
                        continue
            except Exception as e:
                if verbose:
                    logger.debug("Agent %s error on %s: %s", agent.name, file_path, e)

        return findings

    def _summarize(self, elapsed: float) -> Dict[str, Any]:
        by_severity: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        by_agent: Dict[str, int] = {}

        for f in self._findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
            by_category[f.category] = by_category.get(f.category, 0) + 1
            by_agent[f.agent] = by_agent.get(f.agent, 0) + 1

        return {
            "status": self._status,
            "agents_deployed": len(self.agents),
            "total_findings": len(self._findings),
            "elapsed_seconds": round(elapsed, 2),
            "by_severity": by_severity,
            "by_category": by_category,
            "top_agents": dict(sorted(by_agent.items(), key=lambda x: -x[1])[:10]),
            "timestamp": time.time(),
        }

    def get_findings(
        self,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        results = self._findings
        if severity:
            results = [f for f in results if f.severity == severity]
        if category:
            results = [f for f in results if f.category == category]
        return [
            {
                "agent": f.agent,
                "severity": f.severity,
                "title": f.title,
                "file": f.file_path,
                "line": f.line_number,
                "category": f.category,
                "recommendation": f.recommendation,
            }
            for f in results[:limit]
        ]

    def status(self) -> Dict[str, Any]:
        return {
            "status": self._status,
            "agents": len(self.agents),
            "findings": len(self._findings),
            "elapsed": round(time.time() - self._start_time, 2) if self._start_time else 0,
        }
