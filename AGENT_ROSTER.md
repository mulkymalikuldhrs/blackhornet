# BlackHornet Agent Roster — Complete Documentation

> **Last Updated:** 2026-06-18
> **Total Agents:** 110 (10 core + 50 audit + 50 specialists)

---

## Table of Contents

1. [Core Agents (10)](#core-agents)
2. [Audit Agents (50)](#audit-agents)
3. [Specialist Agents (50)](#specialist-agents)
4. [Agent Registration](#agent-registration)
5. [Usage Examples](#usage-examples)

---

## Core Agents

| # | Agent | File | Purpose |
|---|-------|------|---------|
| 1 | ManusAgent | `src/agents/manus.py` | General-purpose agent with tool calling |
| 2 | PlannerAgent | `src/agents/planner.py` | Task planning and decomposition |
| 3 | ExecutorAgent | `src/agents/executor.py` | Task execution and monitoring |
| 4 | CoderAgent | `src/agents/coder.py` | Code generation and analysis |
| 5 | BrowserAgent | `src/agents/browser.py` | Web browsing and automation |
| 6 | VoiceAgent | `src/agents/voice.py` | Voice interaction and TTS |
| 7 | SecurityAgent | `src/agents/security.py` | Security scanning and auditing |
| 8 | ResearcherAgent | `src/agents/researcher.py` | Research and information gathering |
| 9 | ColonyAgent | `src/agents/colony.py` | Colony ecosystem management |
| 10 | ToolCallAgent | `src/agents/manus/agent.py` | Tool call execution base |

---

## Audit Agents

All audit agents are located in `src/agents/audit/`.

### Security Audit Agents

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 1 | SecurityAuditAgent | `security_audit_agent.py` | Vulnerability scanning | audit, scan, report, vulnerability_scan |
| 2 | AuthenticationAuditAgent | `authentication_audit_agent.py` | Auth mechanisms | audit, validate, report, auth_check |
| 3 | AuthorizationAuditAgent | `authorization_audit_agent.py` | RBAC/authorization | audit, validate, report, authz_check |
| 4 | EncryptionAuditAgent | `encryption_audit_agent.py` | Encryption standards | audit, validate, report, encryption_check |
| 5 | AccessControlAgent | `access_control_agent.py` | Access control | audit, validate, report, access_check |
| 6 | VulnerabilityAuditAgent | `vulnerability_audit_agent.py` | Vuln prioritization | audit, scan, report, vuln_assess |
| 7 | PenetrationTestAgent | `penetration_test_agent.py` | Pen testing | test, exploit, report, pentest |
| 8 | PrivacyAuditAgent | `privacy_audit_agent.py` | Privacy compliance | audit, validate, report, privacy_check |

### Infrastructure Audit Agents

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 9 | InfrastructureAuditAgent | `infrastructure_audit_agent.py` | Infrastructure security | audit, scan, report, infra_check |
| 10 | CloudAuditAgent | `cloud_audit_agent.py` | Cloud configuration | audit, validate, report, cloud_check |
| 11 | ContainerAuditAgent | `container_audit_agent.py` | Container security | audit, scan, report, container_check |
| 12 | KubernetesAuditAgent | `kubernetes_audit_agent.py` | K8s security | audit, validate, report, k8s_check |
| 13 | NetworkAuditAgent | `network_audit_agent.py` | Network security | audit, scan, report, network_check |
| 14 | DeploymentAuditAgent | `deployment_audit_agent.py` | Deployment safety | audit, validate, report, deploy_check |

### Code Quality Audit Agents

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 15 | CodeQualityAuditAgent | `code_quality_audit_agent.py` | Code quality | audit, analyze, report, quality_check |
| 16 | DependencyAuditAgent | `dependency_audit_agent.py` | Dependency CVE | audit, scan, report, dep_check |
| 17 | TestCoverageAuditAgent | `test_coverage_audit_agent.py` | Test coverage | audit, measure, report, coverage_check |
| 18 | DocumentationAuditAgent | `documentation_audit_agent.py` | Documentation | audit, validate, report, docs_check |
| 19 | LicenseAuditAgent | `license_audit_agent.py` | License compliance | audit, scan, report, license_check |
| 20 | SchemaValidationAgent | `schema_validation_agent.py` | Schema validation | audit, validate, report, schema_check |

### Performance Audit Agents

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 21 | PerformanceAuditAgent | `performance_audit_agent.py` | Performance bottlenecks | audit, profile, report, perf_check |
| 22 | MemoryAuditAgent | `memory_audit_agent.py` | Memory leaks | audit, scan, report, memory_check |
| 23 | CachingAuditAgent | `caching_audit_agent.py` | Caching strategy | audit, validate, report, cache_check |
| 24 | RateLimitingAgent | `rate_limiting_agent.py` | Rate limiting | audit, validate, report, rate_check |
| 25 | TimeoutAuditAgent | `timeout_audit_agent.py` | Timeout config | audit, validate, report, timeout_check |

### Operational Audit Agents

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 26 | ConfigurationAuditAgent | `configuration_audit_agent.py` | Config security | audit, validate, report, config_check |
| 27 | LoggingAuditAgent | `logging_audit_agent.py` | Logging security | audit, validate, report, logging_check |
| 28 | MonitoringAuditAgent | `monitoring_audit_agent.py` | Monitoring coverage | audit, validate, report, monitoring_check |
| 29 | ErrorHandlingAgent | `error_handling_agent.py` | Error handling | audit, validate, report, error_check |
| 30 | RetryLogicAgent | `retry_logic_agent.py` | Retry logic | audit, validate, report, retry_check |
| 31 | StateManagementAgent | `state_management_agent.py` | State management | audit, validate, report, state_check |
| 32 | LifecycleAuditAgent | `lifecycle_audit_agent.py` | Component lifecycle | audit, validate, report, lifecycle_check |

### Business Audit Agents

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 33 | ComplianceAuditAgent | `compliance_audit_agent.py` | Regulatory compliance | audit, validate, report, compliance_check |
| 34 | RiskAssessmentAgent | `risk_assessment_agent.py` | Risk scoring | assess, score, report, risk_check |
| 35 | IncidentResponseAgent | `incident_response_agent.py` | IR readiness | audit, test, report, ir_check |
| 36 | BusinessContinuityAgent | `business_continuity_agent.py` | BCP planning | audit, validate, report, bcp_check |
| 37 | DisasterRecoveryAgent | `disaster_recovery_agent.py` | DR preparedness | audit, test, report, dr_check |
| 38 | ChangeManagementAgent | `change_management_agent.py` | Change management | audit, validate, report, change_check |
| 39 | ReleaseAuditAgent | `release_audit_agent.py` | Release readiness | audit, validate, report, release_check |

### Data Audit Agents

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 40 | DatabaseAuditAgent | `database_audit_agent.py` | SQL injection/queries | audit, scan, report, db_check |
| 41 | DataIntegrityAgent | `data_integrity_agent.py` | Data integrity | audit, validate, report, integrity_check |
| 42 | ApiAuditAgent | `api_audit_agent.py` | API security | audit, scan, report, api_check |
| 43 | ApiContractAuditAgent | `api_contract_audit_agent.py` | API contracts | audit, validate, report, contract_check |
| 44 | FilesystemAuditAgent | `filesystem_audit_agent.py` | File permissions | audit, scan, report, fs_check |

### System Audit Agents

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 45 | CicdAuditAgent | `cicd_audit_agent.py` | CI/CD pipeline | audit, validate, report, cicd_check |
| 46 | SupplyChainAuditAgent | `supply_chain_audit_agent.py` | Supply chain | audit, scan, report, supply_check |
| 47 | OpenSourceAuditAgent | `open_source_audit_agent.py` | Open source security | audit, scan, report, oss_check |
| 48 | ThirdPartyAuditAgent | `third_party_audit_agent.py` | Third-party services | audit, validate, report, third_check |
| 49 | QueueAuditAgent | `queue_audit_agent.py` | Message queues | audit, validate, report, queue_check |
| 50 | EventAuditAgent | `event_audit_agent.py` | Event system | audit, validate, report, event_check |

---

## Specialist Agents

All specialist agents are located in `src/agents/specialists/`.

### Backend & API Specialists

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 1 | BackendApiSpecialist | `backend_api_specialist.py` | REST/GraphQL API | execute, optimize, monitor, api_design |
| 2 | DatabaseSpecialist | `database_specialist.py` | Database design | execute, optimize, monitor, db_optimize |
| 3 | CacheSpecialist | `cache_specialist.py` | Caching strategies | execute, optimize, monitor, cache_manage |
| 4 | SearchSpecialist | `search_specialist.py` | Search infrastructure | execute, optimize, monitor, search_manage |
| 5 | ApiGatewaySpecialist | `api_gateway_specialist.py` | API gateway | execute, optimize, monitor, gateway_manage |

### Frontend Specialists

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 6 | FrontendUiSpecialist | `frontend_ui_specialist.py` | Frontend development | execute, optimize, monitor, ui_build |
| 7 | DashboardSpecialist | `dashboard_specialist.py` | Dashboard development | execute, optimize, monitor, dashboard_build |
| 8 | ReportSpecialist | `report_specialist.py` | Report generation | execute, optimize, monitor, report_generate |

### DevOps Specialists

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 9 | DevopsSpecialist | `devops_specialist.py` | DevOps automation | execute, optimize, monitor, devops_automate |
| 10 | CicdSpecialist | `cicd_specialist.py` | CI/CD pipelines | execute, optimize, monitor, cicd_manage |
| 11 | ContainerSpecialist | `container_specialist.py` | Containerization | execute, optimize, monitor, container_manage |
| 12 | KubernetesSpecialist | `kubernetes_specialist.py` | K8s orchestration | execute, optimize, monitor, k8s_manage |
| 13 | CloudSpecialist | `cloud_specialist.py` | Cloud architecture | execute, optimize, monitor, cloud_manage |
| 14 | ServerlessSpecialist | `serverless_specialist.py` | Serverless computing | execute, optimize, monitor, serverless_manage |

### Security Specialists

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 15 | SecuritySpecialist | `security_specialist.py` | Security hardening | execute, optimize, monitor, security_harden |
| 16 | FirewallSpecialist | `firewall_specialist.py` | Firewall configuration | execute, optimize, monitor, firewall_manage |
| 17 | IdsIpsSpecialist | `ids_ips_specialist.py` | Intrusion detection | execute, optimize, monitor, ids_manage |
| 18 | SiemSpecialist | `siem_specialist.py` | SIEM management | execute, optimize, monitor, siem_manage |
| 19 | ForensicsSpecialist | `forensics_specialist.py` | Digital forensics | execute, investigate, report, forensics_analyze |
| 20 | SslTlsSpecialist | `ssl_tls_specialist.py` | SSL/TLS management | execute, optimize, monitor, ssl_manage |

### Data Specialists

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 21 | AnalyticsSpecialist | `analytics_specialist.py` | Analytics processing | execute, optimize, monitor, analytics_process |
| 22 | MlSpecialist | `ml_specialist.py` | ML operations | execute, optimize, monitor, ml_manage |
| 23 | DataEngineeringSpecialist | `data_engineering_specialist.py` | Data pipelines | execute, optimize, monitor, pipeline_manage |
| 24 | EtlSpecialist | `etl_specialist.py` | ETL processes | execute, optimize, monitor, etl_manage |
| 25 | DataWarehouseSpecialist | `data_warehouse_specialist.py` | Data warehouse | execute, optimize, monitor, warehouse_manage |
| 26 | BiSpecialist | `bi_specialist.py` | Business intelligence | execute, optimize, monitor, bi_manage |

### Communication Specialists

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 27 | NotificationSpecialist | `notification_specialist.py` | Notification systems | execute, optimize, monitor, notify_manage |
| 28 | EmailSpecialist | `email_specialist.py` | Email infrastructure | execute, optimize, monitor, email_manage |
| 29 | SmsSpecialist | `sms_specialist.py` | SMS integration | execute, optimize, monitor, sms_manage |
| 30 | PushNotificationSpecialist | `push_notification_specialist.py` | Push notifications | execute, optimize, monitor, push_manage |
| 31 | WebhookSpecialist | `webhook_specialist.py` | Webhook management | execute, optimize, monitor, webhook_manage |

### Architecture Specialists

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 32 | MicroservicesSpecialist | `microservices_specialist.py` | Microservices | execute, optimize, monitor, microservices_manage |
| 33 | EventDrivenSpecialist | `event_driven_specialist.py` | Event-driven arch | execute, optimize, monitor, event_manage |
| 34 | MessageQueueSpecialist | `message_queue_specialist.py` | Message queues | execute, optimize, monitor, queue_manage |
| 35 | IntegrationSpecialist | `integration_specialist.py` | System integration | execute, optimize, monitor, integration_manage |
| 36 | LoadBalancerSpecialist | `load_balancer_specialist.py` | Load balancing | execute, optimize, monitor, lb_manage |
| 37 | CdnSpecialist | `cdn_specialist.py` | CDN optimization | execute, optimize, monitor, cdn_manage |
| 38 | DnsSpecialist | `dns_specialist.py` | DNS management | execute, optimize, monitor, dns_manage |

### Operations Specialists

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 39 | PerformanceSpecialist | `performance_specialist.py` | Performance optimization | execute, optimize, monitor, perf_optimize |
| 40 | MonitoringSpecialist | `monitoring_specialist.py` | Observability | execute, optimize, monitor, monitoring_manage |
| 41 | LoggingSpecialist | `logging_specialist.py` | Logging infrastructure | execute, optimize, monitor, logging_manage |
| 42 | TestingSpecialist | `testing_specialist.py` | Test automation | execute, optimize, monitor, test_manage |
| 43 | DocumentationSpecialist | `documentation_specialist.py` | Technical docs | execute, optimize, monitor, docs_manage |

### Governance Specialists

| # | Agent | File | Domain | Capabilities |
|---|-------|------|--------|--------------|
| 44 | ComplianceSpecialist | `compliance_specialist.py` | Compliance automation | execute, validate, monitor, compliance_manage |
| 45 | GovernanceSpecialist | `governance_specialist.py` | IT governance | execute, validate, monitor, governance_manage |
| 46 | RiskManagementSpecialist | `risk_management_specialist.py` | Risk management | execute, assess, monitor, risk_manage |
| 47 | IncidentManagementSpecialist | `incident_management_specialist.py` | Incident management | execute, manage, monitor, incident_manage |
| 48 | ChangeManagementSpecialist | `change_management_specialist.py` | Change management | execute, manage, monitor, change_manage |
| 49 | ReleaseManagementSpecialist | `release_management_specialist.py` | Release management | execute, manage, monitor, release_manage |
| 50 | SupportSpecialist | `support_specialist.py` | Technical support | execute, assist, monitor, support_manage |

---

## Agent Registration

### Registering New Agents

```python
from src.agents.registry import AgentRegistry, AGENT_TYPES
from src.colony_types.models import AgentType

# Register audit agent
registry = AgentRegistry()
registry.register_type(AgentType.SECURITY, SecurityAuditAgent)

# Register specialist agent
registry.register_type(AgentType.COLONY, BackendApiSpecialist)
```

### Creating Agents

```python
# Create agent instance
agent = registry.create_agent(
    agent_type=AgentType.SECURITY,
    spec={"agent_id": "audit_001", "colony_id": "colony_1"},
    tools=["scan", "report"]
)

# Execute task
result = await agent.execute({
    "action": "audit",
    "target": "src/",
    "depth": "full"
})
```

### Searching Agents

```python
# Search by capability
agents = registry.search_by_capability("security_audit")

# Get health reports
health = registry.get_all_health_reports()

# Get unhealthy agents
unhealthy = registry.get_unhealthy_agents(threshold=0.5)
```

---

## Usage Examples

### Running a Security Audit

```python
from src.agents.audit import SecurityAuditAgent

agent = SecurityAuditAgent(agent_id="sec_audit_001")
result = await agent.on_task({
    "action": "audit",
    "target": "src/",
    "scan_type": "full"
})
print(result)  # {success: True, findings: [...]}
```

### Running a Performance Audit

```python
from src.agents.audit import PerformanceAuditAgent

agent = PerformanceAuditAgent(agent_id="perf_audit_001")
result = await agent.on_task({
    "action": "audit",
    "target": "api/",
    "metrics": ["latency", "throughput", "errors"]
})
print(result)  # {success: True, metrics: {...}}
```

### Using a Specialist Agent

```python
from src.agents.specialists import DatabaseSpecialist

agent = DatabaseSpecialist(agent_id="db_spec_001")
result = await agent.on_task({
    "action": "optimize",
    "target": "queries/slow.sql",
    "strategy": "index"
})
print(result)  # {success: True, optimized: True}
```

### Running All Audit Agents

```python
from src.agents.audit import *

audit_agents = [
    SecurityAuditAgent("sec_001"),
    CodeQualityAuditAgent("code_001"),
    DependencyAuditAgent("dep_001"),
    # ... all 50 agents
]

results = []
for agent in audit_agents:
    result = await agent.on_task({"action": "audit", "target": "src/"})
    results.append({"agent": agent.agent_id, "result": result})
```

---

## Architecture

```
src/agents/
├── __init__.py
├── base.py                    # BaseAgent class
├── registry.py                # AgentRegistry
├── manus.py                   # ManusAgent
├── planner.py                 # PlannerAgent
├── executor.py                # ExecutorAgent
├── coder.py                   # CoderAgent
├── browser.py                 # BrowserAgent
├── voice.py                   # VoiceAgent
├── security.py                # SecurityAgent
├── researcher.py              # ResearcherAgent
├── colony.py                  # ColonyAgent
├── audit/                     # 50 Audit Agents
│   ├── __init__.py
│   ├── security_audit_agent.py
│   ├── code_quality_audit_agent.py
│   ├── dependency_audit_agent.py
│   ├── ... (47 more)
│   └── lifecycle_audit_agent.py
└── specialists/               # 50 Specialist Agents
    ├── __init__.py
    ├── backend_api_specialist.py
    ├── frontend_ui_specialist.py
    ├── database_specialist.py
    ├── ... (47 more)
    └── support_specialist.py
```

---

## Statistics

| Category | Count |
|----------|-------|
| Core Agents | 10 |
| Audit Agents | 50 |
| Specialist Agents | 50 |
| **Total** | **110** |

### Audit Agent Categories

| Category | Count |
|----------|-------|
| Security | 8 |
| Infrastructure | 6 |
| Code Quality | 6 |
| Performance | 5 |
| Operational | 7 |
| Business | 7 |
| Data | 5 |
| System | 6 |
| **Total** | **50** |

### Specialist Agent Categories

| Category | Count |
|----------|-------|
| Backend & API | 5 |
| Frontend | 3 |
| DevOps | 6 |
| Security | 6 |
| Data | 6 |
| Communication | 5 |
| Architecture | 7 |
| Operations | 5 |
| Governance | 7 |
| **Total** | **50** |

---

## Test Coverage

All agents follow the BaseAgent pattern and can be tested with:

```bash
python -m unittest discover -s src/agents -p "test_*.py"
```

---

## Documentation

- `AGENTS.md` — Agent overview and registry
- `AGENT_ROSTER.md` — This file (complete roster)
- `src/agents/base.py` — BaseAgent documentation
- `src/agents/registry.py` — Registry documentation
- `docs/plans/` — Implementation plans
