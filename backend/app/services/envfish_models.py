"""
EnvFish shared domain models and helper utilities.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


ENVFISH_ENGINE_MODE = "envfish"

SCENARIO_MODES = {"baseline_mode", "crisis_mode"}
DIFFUSION_TEMPLATES = {"air", "inland_water", "marine", "generic"}
VARIABLE_TYPES = {"disaster", "policy"}
POLICY_MODES = {
    "restrict",
    "relocate",
    "subsidize",
    "monitor",
    "disclose",
    "repair",
    "ban",
    "reopen",
}

STATE_VECTOR_SCHEMA = {
    "exposure_score": {
        "label": "Exposure",
        "description": "Regional or actor exposure to the hazard.",
    },
    "spread_pressure": {
        "label": "Spread Pressure",
        "description": "Local pressure that can propagate to neighbors.",
    },
    "ecosystem_integrity": {
        "label": "Ecosystem Integrity",
        "description": "Overall ecological health and resilience.",
    },
    "livelihood_stability": {
        "label": "Livelihood Stability",
        "description": "Stability of jobs, fisheries, farming, and incomes.",
    },
    "public_trust": {
        "label": "Public Trust",
        "description": "Trust in institutions and public information.",
    },
    "panic_level": {
        "label": "Panic Level",
        "description": "Social fear, rumor, and emotional escalation.",
    },
    "service_capacity": {
        "label": "Service Capacity",
        "description": "Capacity of infrastructure and public services.",
    },
    "response_capacity": {
        "label": "Response Capacity",
        "description": "Operational response capacity of authorities and organizations.",
    },
    "economic_stress": {
        "label": "Economic Stress",
        "description": "Pressure on production, trade, and consumption.",
    },
    "vulnerability_score": {
        "label": "Vulnerability",
        "description": "Composite fragility of the actor or region.",
    },
}

BASELINE_STATE_VECTOR = {
    "exposure_score": 12,
    "spread_pressure": 10,
    "ecosystem_integrity": 78,
    "livelihood_stability": 74,
    "public_trust": 64,
    "panic_level": 16,
    "service_capacity": 72,
    "response_capacity": 66,
    "economic_stress": 24,
    "vulnerability_score": 34,
}

CRISIS_STATE_VECTOR = {
    "exposure_score": 58,
    "spread_pressure": 54,
    "ecosystem_integrity": 43,
    "livelihood_stability": 36,
    "public_trust": 28,
    "panic_level": 66,
    "service_capacity": 40,
    "response_capacity": 38,
    "economic_stress": 61,
    "vulnerability_score": 72,
}

DEFAULT_TEMPLATE_RULES = {
    "air": {
        "default_lag_rounds": 1,
        "default_decay": 0.84,
        "default_persistence": 48,
        "max_neighbor_spread": 3,
    },
    "inland_water": {
        "default_lag_rounds": 1,
        "default_decay": 0.9,
        "default_persistence": 62,
        "max_neighbor_spread": 2,
    },
    "marine": {
        "default_lag_rounds": 2,
        "default_decay": 0.92,
        "default_persistence": 70,
        "max_neighbor_spread": 4,
    },
    "generic": {
        "default_lag_rounds": 1,
        "default_decay": 0.88,
        "default_persistence": 55,
        "max_neighbor_spread": 2,
    },
}

NODE_FAMILY_KEYWORDS = {
    "Region": ("region", "city", "county", "district", "province", "coast", "bay", "port", "island"),
    "EnvironmentalCarrier": ("current", "river", "air", "wind", "soil", "water", "ocean", "stream"),
    "EcologicalReceptor": ("fish", "bird", "habitat", "species", "crop", "reef", "forest", "wetland"),
    "HumanActor": ("resident", "fisher", "farmer", "consumer", "worker", "tourist", "citizen", "family"),
    "OrganizationActor": ("enterprise", "company", "ngo", "media", "school", "hospital", "market", "association"),
    "GovernmentActor": ("gov", "government", "agency", "authority", "bureau", "office", "regulator"),
    "Infrastructure": ("port", "plant", "hub", "road", "transport", "pipeline", "market", "hospital"),
}


def utcnow_iso() -> str:
    return datetime.now().isoformat()


def clamp_score(value: Any, lower: float = 0.0, upper: float = 100.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = lower
    if math.isnan(number) or math.isinf(number):
        number = lower
    return round(max(lower, min(upper, number)), 2)


def clamp_probability(value: Any) -> float:
    return clamp_score(value, 0.0, 1.0)


def normalize_state_vector(values: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    values = values or {}
    normalized = {}
    for field_name in STATE_VECTOR_SCHEMA:
        normalized[field_name] = clamp_score(values.get(field_name, BASELINE_STATE_VECTOR[field_name]))
    return normalized


def merge_state_vectors(base: Dict[str, Any], delta: Optional[Dict[str, Any]]) -> Dict[str, float]:
    result = normalize_state_vector(base)
    for field_name, value in (delta or {}).items():
        if field_name in result:
            result[field_name] = clamp_score(result[field_name] + float(value))
    return result


def default_state_vector(
    scenario_mode: str = "baseline_mode",
    node_family: str = "HumanActor",
) -> Dict[str, float]:
    family_offsets = {
        "EnvironmentalCarrier": {
            "spread_pressure": 14,
            "ecosystem_integrity": -6,
            "vulnerability_score": -8,
        },
        "EcologicalReceptor": {
            "ecosystem_integrity": -12,
            "livelihood_stability": -4,
            "vulnerability_score": 12,
        },
        "GovernmentActor": {
            "public_trust": 8,
            "response_capacity": 12,
            "panic_level": -6,
        },
        "OrganizationActor": {
            "service_capacity": 8,
            "economic_stress": 6,
        },
        "Infrastructure": {
            "service_capacity": 10,
            "vulnerability_score": 8,
        },
        "Region": {
            "response_capacity": 4,
            "service_capacity": 4,
        },
    }
    vector = dict(CRISIS_STATE_VECTOR if scenario_mode == "crisis_mode" else BASELINE_STATE_VECTOR)
    for key, delta in family_offsets.get(node_family, {}).items():
        vector[key] = clamp_score(vector[key] + delta)
    return normalize_state_vector(vector)


def ensure_unique_slug(name: str, used: set[str]) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_") or "region"
    slug = "_".join(part for part in slug.split("_") if part)
    candidate = slug
    index = 2
    while candidate in used:
        candidate = f"{slug}_{index}"
        index += 1
    used.add(candidate)
    return candidate


def infer_node_family(entity_type: Optional[str], name: str = "", summary: str = "") -> str:
    haystack = f"{entity_type or ''} {name} {summary}".lower()
    for family, keywords in NODE_FAMILY_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return family
    return "HumanActor"


def score_band(value: Any) -> str:
    score = clamp_score(value)
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


@dataclass
class RegionNode:
    region_id: str
    name: str
    region_type: str = "region"
    description: str = ""
    neighbors: List[str] = field(default_factory=list)
    carriers: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    state_vector: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["state_vector"] = normalize_state_vector(self.state_vector)
        payload["neighbors"] = sorted(set(self.neighbors))
        payload["carriers"] = sorted(set(self.carriers))
        payload["tags"] = sorted(set(self.tags))
        return payload


@dataclass
class InjectedVariable:
    variable_id: str
    type: str
    template: str
    name: str
    description: str = ""
    target_regions: List[str] = field(default_factory=list)
    target_nodes: List[int] = field(default_factory=list)
    start_round: int = 1
    duration_rounds: int = 1
    intensity_0_100: float = 50.0
    policy_mode: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable_id": self.variable_id,
            "type": self.type if self.type in VARIABLE_TYPES else "disaster",
            "template": self.template if self.template in DIFFUSION_TEMPLATES else "generic",
            "name": self.name,
            "description": self.description,
            "target_regions": self.target_regions,
            "target_nodes": self.target_nodes,
            "start_round": max(1, int(self.start_round)),
            "duration_rounds": max(1, int(self.duration_rounds)),
            "intensity_0_100": clamp_score(self.intensity_0_100),
            "policy_mode": self.policy_mode if self.policy_mode in POLICY_MODES else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], default_index: int = 1) -> "InjectedVariable":
        return cls(
            variable_id=str(data.get("variable_id") or f"var_{default_index}"),
            type=str(data.get("type") or "disaster"),
            template=str(data.get("template") or "generic"),
            name=str(data.get("name") or data.get("title") or f"Variable {default_index}"),
            description=str(data.get("description") or ""),
            target_regions=list(data.get("target_regions") or []),
            target_nodes=[int(item) for item in (data.get("target_nodes") or []) if str(item).isdigit()],
            start_round=int(data.get("start_round") or 1),
            duration_rounds=int(data.get("duration_rounds") or 1),
            intensity_0_100=clamp_score(data.get("intensity_0_100", data.get("intensity", 50))),
            policy_mode=data.get("policy_mode"),
        )


@dataclass
class EnvAgentProfile:
    agent_id: int
    username: str
    name: str
    node_family: str
    role_type: str
    bio: str
    persona: str
    profession: str
    primary_region: str
    influenced_regions: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    sensitivities: List[str] = field(default_factory=list)
    state_vector: Dict[str, float] = field(default_factory=dict)
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["state_vector"] = normalize_state_vector(self.state_vector)
        payload["influenced_regions"] = list(dict.fromkeys(self.influenced_regions or [self.primary_region]))
        return payload

    def to_agent_config(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.username,
            "name": self.name,
            "node_family": self.node_family,
            "role_type": self.role_type,
            "profession": self.profession,
            "primary_region": self.primary_region,
            "influenced_regions": list(dict.fromkeys(self.influenced_regions or [self.primary_region])),
            "goals": self.goals,
            "sensitivities": self.sensitivities,
            "state_vector": normalize_state_vector(self.state_vector),
            "bio": self.bio,
            "persona": self.persona,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
        }

    def to_reddit_format(self) -> Dict[str, Any]:
        profile = {
            "user_id": self.agent_id,
            "username": self.username,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "profession": self.profession,
            "primary_region": self.primary_region,
            "node_family": self.node_family,
            "role_type": self.role_type,
            "interested_topics": self.goals[:6],
            "created_at": self.created_at,
        }
        profile.update(normalize_state_vector(self.state_vector))
        return profile

    def to_twitter_format(self) -> Dict[str, Any]:
        profile = {
            "user_id": self.agent_id,
            "username": self.username,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "profession": self.profession,
            "primary_region": self.primary_region,
            "node_family": self.node_family,
            "role_type": self.role_type,
            "friend_count": 80 + self.agent_id * 3,
            "follower_count": 120 + self.agent_id * 5,
            "statuses_count": 40 + self.agent_id * 4,
            "created_at": self.created_at,
        }
        profile.update(normalize_state_vector(self.state_vector))
        return profile


@dataclass
class EnvProfileGenerationResult:
    regions: List[RegionNode]
    profiles: List[EnvAgentProfile]
    grounding_summary: Dict[str, Any]
    generation_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regions": [region.to_dict() for region in self.regions],
            "profiles": [profile.to_dict() for profile in self.profiles],
            "grounding_summary": self.grounding_summary,
            "generation_notes": self.generation_notes,
        }


@dataclass
class RiskEvidence:
    evidence_id: str
    source_type: str
    title: str
    summary: str
    confidence: float = 0.6
    source_ref: str = ""
    related_chain_steps: List[str] = field(default_factory=list)
    region_scope: List[str] = field(default_factory=list)
    entity_refs: List[str] = field(default_factory=list)
    extracted_facts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["confidence"] = clamp_probability(self.confidence)
        payload["related_chain_steps"] = list(dict.fromkeys(self.related_chain_steps))
        payload["region_scope"] = list(dict.fromkeys(self.region_scope))
        payload["entity_refs"] = list(dict.fromkeys(self.entity_refs))
        payload["extracted_facts"] = list(dict.fromkeys(self.extracted_facts))
        return payload


@dataclass
class RiskAffectedCluster:
    cluster_id: str
    name: str
    cluster_type: str
    primary_regions: List[str] = field(default_factory=list)
    actor_ids: List[int] = field(default_factory=list)
    dependency_profile: List[str] = field(default_factory=list)
    early_loss_signals: List[str] = field(default_factory=list)
    vulnerability_score: float = 0.0
    mismatch_risk: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["primary_regions"] = list(dict.fromkeys(self.primary_regions))
        payload["actor_ids"] = sorted(set(self.actor_ids))
        payload["dependency_profile"] = list(dict.fromkeys(self.dependency_profile))
        payload["early_loss_signals"] = list(dict.fromkeys(self.early_loss_signals))
        payload["vulnerability_score"] = clamp_score(self.vulnerability_score)
        payload["mismatch_risk"] = clamp_score(self.mismatch_risk)
        return payload


@dataclass
class RiskInterventionOption:
    intervention_id: str
    name: str
    policy_type: str
    description: str = ""
    target_chain_steps: List[str] = field(default_factory=list)
    expected_direct_effects: List[str] = field(default_factory=list)
    expected_second_order_effects: List[str] = field(default_factory=list)
    benefit_clusters: List[str] = field(default_factory=list)
    hurt_clusters: List[str] = field(default_factory=list)
    friction_points: List[str] = field(default_factory=list)
    confidence: float = 0.55
    source_variable_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["policy_type"] = self.policy_type if self.policy_type in POLICY_MODES else "monitor"
        payload["target_chain_steps"] = list(dict.fromkeys(self.target_chain_steps))
        payload["expected_direct_effects"] = list(dict.fromkeys(self.expected_direct_effects))
        payload["expected_second_order_effects"] = list(dict.fromkeys(self.expected_second_order_effects))
        payload["benefit_clusters"] = list(dict.fromkeys(self.benefit_clusters))
        payload["hurt_clusters"] = list(dict.fromkeys(self.hurt_clusters))
        payload["friction_points"] = list(dict.fromkeys(self.friction_points))
        payload["confidence"] = clamp_probability(self.confidence)
        return payload


@dataclass
class RiskScenarioBranch:
    branch_id: str
    name: str
    description: str
    assumptions: List[str] = field(default_factory=list)
    target_interventions: List[str] = field(default_factory=list)
    comparison_focus: List[str] = field(default_factory=list)
    branch_type: str = "baseline"

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["assumptions"] = list(dict.fromkeys(self.assumptions))
        payload["target_interventions"] = list(dict.fromkeys(self.target_interventions))
        payload["comparison_focus"] = list(dict.fromkeys(self.comparison_focus))
        return payload


@dataclass
class RiskObject:
    risk_object_id: str
    title: str
    summary: str
    why_now: str
    risk_type: str
    mode: str = "watch"
    status: str = "candidate"
    time_horizon: str = "30d"
    region_scope: List[str] = field(default_factory=list)
    primary_regions: List[str] = field(default_factory=list)
    severity_score: float = 0.0
    confidence_score: float = 0.0
    actionability_score: float = 0.0
    novelty_score: float = 0.0
    root_pressures: List[str] = field(default_factory=list)
    chain_steps: List[str] = field(default_factory=list)
    turning_points: List[str] = field(default_factory=list)
    amplifiers: List[str] = field(default_factory=list)
    buffers: List[str] = field(default_factory=list)
    source_entity_uuids: List[str] = field(default_factory=list)
    source_variable_ids: List[str] = field(default_factory=list)
    evidence: List[RiskEvidence] = field(default_factory=list)
    affected_clusters: List[RiskAffectedCluster] = field(default_factory=list)
    intervention_options: List[RiskInterventionOption] = field(default_factory=list)
    scenario_branches: List[RiskScenarioBranch] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_object_id": self.risk_object_id,
            "title": self.title,
            "summary": self.summary,
            "why_now": self.why_now,
            "risk_type": self.risk_type,
            "mode": self.mode,
            "status": self.status,
            "time_horizon": self.time_horizon,
            "region_scope": list(dict.fromkeys(self.region_scope)),
            "primary_regions": list(dict.fromkeys(self.primary_regions)),
            "severity_score": clamp_score(self.severity_score),
            "confidence_score": clamp_probability(self.confidence_score),
            "actionability_score": clamp_score(self.actionability_score),
            "novelty_score": clamp_score(self.novelty_score),
            "root_pressures": list(dict.fromkeys(self.root_pressures)),
            "chain_steps": list(dict.fromkeys(self.chain_steps)),
            "turning_points": list(dict.fromkeys(self.turning_points)),
            "amplifiers": list(dict.fromkeys(self.amplifiers)),
            "buffers": list(dict.fromkeys(self.buffers)),
            "source_entity_uuids": list(dict.fromkeys(self.source_entity_uuids)),
            "source_variable_ids": list(dict.fromkeys(self.source_variable_ids)),
            "evidence": [item.to_dict() for item in self.evidence],
            "affected_clusters": [item.to_dict() for item in self.affected_clusters],
            "intervention_options": [item.to_dict() for item in self.intervention_options],
            "scenario_branches": [item.to_dict() for item in self.scenario_branches],
            "created_at": self.created_at,
        }


@dataclass
class RiskObjectBuildResult:
    risk_objects: List[RiskObject]
    primary_risk_object_id: str = ""
    generation_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        primary = None
        if self.primary_risk_object_id:
            for item in self.risk_objects:
                if item.risk_object_id == self.primary_risk_object_id:
                    primary = item.to_dict()
                    break
        return {
            "primary_risk_object_id": self.primary_risk_object_id,
            "risk_objects_count": len(self.risk_objects),
            "risk_objects": [item.to_dict() for item in self.risk_objects],
            "primary_risk_object": primary,
            "generation_notes": self.generation_notes,
        }


def dump_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def write_profiles_csv(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    rows = list(rows)
    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
