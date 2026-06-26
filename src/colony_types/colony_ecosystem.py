"""Type definitions for Colony Ecosystem: Radar, Mesh Bus, and Self-Nest."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field
from src.colony_types._pydantic_compat import model_dump, model_validate


class RadarDiscoveryMethod(str, Enum):
    LAN_BROADCAST = "lan_broadcast"
    DHT = "dht"
    RENDEZVOUS = "rendezvous"
    STATIC_PEER = "static_peer"
    DNS_DISCOVERY = "dns_discovery"


class RadarSignalType(str, Enum):
    ANNOUNCE = "announce"
    PING = "ping"
    PONG = "pong"
    ADVERTISE = "advertise"
    BYE = "bye"
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"


class ColonyIdentity(BaseModel):
    colony_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    instance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "unnamed-colony"
    version: str = "5.0.0"
    host: str = "0.0.0.0"
    port: int = 0
    public_endpoint: Optional[str] = None
    capabilities: list[str] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
    first_seen: float = Field(default_factory=time.time)
    last_seen: float = Field(default_factory=time.time)
    ttl: int = 300

    model_config = {"arbitrary_types_allowed": True}


class RadarSignal(BaseModel):
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_type: RadarSignalType
    sender: ColonyIdentity
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    ttl: int = 60

    model_config = {"arbitrary_types_allowed": True}


class MeshMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = "general"
    sender_id: str = ""
    sender_colony: str = ""
    target_colony: Optional[str] = None
    target_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 5
    ttl: int = 300
    correlation_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    hop_count: int = 0
    max_hops: int = 5
    signature: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}


class NestConfig(BaseModel):
    nest_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "blackhornet-nest"
    version: str = "5.0.0"

    data_dir: str = "data"
    log_dir: str = "logs"
    config_dir: str = "config"

    auto_restart: bool = True
    health_check_interval: int = 30
    max_restarts_per_hour: int = 10
    cooldown_seconds: int = 300

    dependencies: list[str] = Field(default_factory=lambda: ["python3", "pip3", "git"])
    required_packages: list[str] = Field(default_factory=list)
    env_file: str = "config/.env"
    entry_point: str = "blackhornet-doctor"

    heartbeat_port: int = 0
    api_port: int = 0
    mesh_port: int = 0

    supervisor: str = "auto"

    tags: dict[str, str] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class NestStatusReport(BaseModel):
    nest_id: str
    name: str
    status: str
    uptime: float = 0.0
    pid: Optional[int] = None
    memory_mb: float = 0.0
    cpu_pct: float = 0.0
    disk_pct: float = 0.0
    restart_count: int = 0
    last_restart: Optional[float] = None
    last_health_check: Optional[float] = None
    components: dict[str, str] = Field(default_factory=dict)
    peers_connected: int = 0
    errors: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
