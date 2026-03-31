"""
EnvFish simulation config synthesis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .envfish_models import (
    DEFAULT_TEMPLATE_RULES,
    ENVFISH_ENGINE_MODE,
    EnvAgentProfile,
    InjectedVariable,
    RegionNode,
    RiskObject,
    STATE_VECTOR_SCHEMA,
)

logger = get_logger("envfish.envfish_config")


@dataclass
class EnvSimulationConfig:
    simulation_id: str
    project_id: str
    graph_id: str
    engine_mode: str = ENVFISH_ENGINE_MODE
    scenario_mode: str = "baseline_mode"
    diffusion_template: str = "marine"
    simulation_requirement: str = ""
    document_digest: str = ""
    generation_reasoning: str = ""
    scenario_summary: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    llm_model: str = field(default_factory=lambda: Config.LLM_MODEL_NAME)
    time_config: Dict[str, Any] = field(default_factory=dict)
    round_policies: Dict[str, Any] = field(default_factory=dict)
    state_vector_schema: Dict[str, Any] = field(default_factory=lambda: dict(STATE_VECTOR_SCHEMA))
    region_graph: List[Dict[str, Any]] = field(default_factory=list)
    actor_profiles: List[Dict[str, Any]] = field(default_factory=list)
    agent_configs: List[Dict[str, Any]] = field(default_factory=list)
    injected_variables: List[Dict[str, Any]] = field(default_factory=list)
    risk_objects: List[Dict[str, Any]] = field(default_factory=list)
    primary_risk_object_id: str = ""
    data_grounding_summary: Dict[str, Any] = field(default_factory=dict)
    report_focus: List[str] = field(default_factory=list)
    uncertainty_policy: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "engine_mode": self.engine_mode,
            "scenario_mode": self.scenario_mode,
            "diffusion_template": self.diffusion_template,
            "simulation_requirement": self.simulation_requirement,
            "document_digest": self.document_digest,
            "generation_reasoning": self.generation_reasoning,
            "scenario_summary": self.scenario_summary,
            "generated_at": self.generated_at,
            "llm_model": self.llm_model,
            "time_config": self.time_config,
            "round_policies": self.round_policies,
            "state_vector_schema": self.state_vector_schema,
            "region_graph": self.region_graph,
            "actor_profiles": self.actor_profiles,
            "agent_configs": self.agent_configs,
            "injected_variables": self.injected_variables,
            "risk_objects": self.risk_objects,
            "primary_risk_object_id": self.primary_risk_object_id,
            "data_grounding_summary": self.data_grounding_summary,
            "report_focus": self.report_focus,
            "uncertainty_policy": self.uncertainty_policy,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class EnvSimulationConfigGenerator:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client
        if self.llm_client is None and Config.LLM_API_KEY:
            try:
                self.llm_client = LLMClient()
            except Exception as exc:
                logger.warning(f"Env config LLM init failed, using fallback config: {exc}")

    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        regions: List[RegionNode],
        profiles: List[EnvAgentProfile],
        scenario_mode: str = "baseline_mode",
        diffusion_template: str = "marine",
        injected_variables: Optional[List[InjectedVariable]] = None,
        data_grounding_summary: Optional[Dict[str, Any]] = None,
        risk_objects: Optional[List[RiskObject]] = None,
        primary_risk_object_id: str = "",
    ) -> EnvSimulationConfig:
        llm_plan = self._generate_plan_with_llm(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            regions=regions,
            profiles=profiles,
            scenario_mode=scenario_mode,
            diffusion_template=diffusion_template,
        )
        fallback = self._fallback_plan(
            scenario_mode=scenario_mode,
            diffusion_template=diffusion_template,
            region_count=len(regions),
            actor_count=len(profiles),
        )
        plan = {**fallback, **(llm_plan or {})}

        template_rules = DEFAULT_TEMPLATE_RULES.get(diffusion_template, DEFAULT_TEMPLATE_RULES["generic"])
        total_rounds = max(4, int(plan.get("total_rounds", fallback["total_rounds"])))
        minutes_per_round = max(10, int(plan.get("minutes_per_round", fallback["minutes_per_round"])))
        total_hours = round(total_rounds * minutes_per_round / 60, 1)

        config = EnvSimulationConfig(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            scenario_mode=scenario_mode,
            diffusion_template=diffusion_template,
            simulation_requirement=simulation_requirement,
            document_digest=document_text[:2000],
            generation_reasoning=str(
                plan.get("generation_reasoning")
                or f"Used {diffusion_template} template with {len(regions)} regions and {len(profiles)} actors."
            ),
            scenario_summary=str(
                plan.get("scenario_summary")
                or f"Region-level eco-social stress test in {scenario_mode} using {diffusion_template} diffusion."
            ),
            time_config={
                "total_rounds": total_rounds,
                "minutes_per_round": minutes_per_round,
                "total_simulation_hours": total_hours,
                "round_label": plan.get("round_label", "simulation round"),
            },
            round_policies={
                "diffusion_decay": template_rules["default_decay"],
                "default_lag_rounds": template_rules["default_lag_rounds"],
                "default_persistence": template_rules["default_persistence"],
                "max_neighbor_spread": template_rules["max_neighbor_spread"],
                "score_update_limit": 18,
            },
            region_graph=[region.to_dict() for region in regions],
            actor_profiles=[profile.to_dict() for profile in profiles],
            agent_configs=[profile.to_agent_config() for profile in profiles],
            injected_variables=[item.to_dict() for item in (injected_variables or [])],
            risk_objects=[item.to_dict() for item in (risk_objects or [])],
            primary_risk_object_id=primary_risk_object_id,
            data_grounding_summary=data_grounding_summary or {},
            report_focus=plan.get(
                "report_focus",
                [
                    "risk object summary",
                    "regional spread forecast",
                    "human-nature feedback loops",
                    "vulnerable regions and actors",
                    "intervention comparison",
                    "uncertainty and model limits",
                ],
            ),
            uncertainty_policy={
                "display_band": True,
                "per_round_confidence": True,
                "explanation": "Confidence reflects constrained LLM consistency, not physical certainty.",
            },
        )
        return config

    def _generate_plan_with_llm(
        self,
        simulation_requirement: str,
        document_text: str,
        regions: List[RegionNode],
        profiles: List[EnvAgentProfile],
        scenario_mode: str,
        diffusion_template: str,
    ) -> Optional[Dict[str, Any]]:
        if not self.llm_client:
            return None

        prompt = {
            "task": "Plan an EnvFish region-level scenario simulation configuration.",
            "scenario_mode": scenario_mode,
            "diffusion_template": diffusion_template,
            "simulation_requirement": simulation_requirement[:1500],
            "document_excerpt": document_text[:5000],
            "region_graph": [region.to_dict() for region in regions[:6]],
            "actor_samples": [profile.to_agent_config() for profile in profiles[:8]],
            "schema": {
                "scenario_summary": "string",
                "generation_reasoning": "string",
                "total_rounds": 8,
                "minutes_per_round": 30,
                "round_label": "string",
                "report_focus": ["item 1", "item 2"],
            },
            "rules": [
                "Keep total_rounds between 4 and 16.",
                "Keep minutes_per_round between 10 and 180.",
                "Favor explainability over realism.",
                "Return valid JSON only.",
            ],
        }
        try:
            return self.llm_client.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": "You return compact JSON for an EnvFish simulation config.",
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                temperature=0.25,
                max_tokens=1300,
            )
        except Exception as exc:
            logger.warning(f"Env config LLM generation failed, using fallback: {exc}")
            return None

    def _fallback_plan(
        self,
        scenario_mode: str,
        diffusion_template: str,
        region_count: int,
        actor_count: int,
    ) -> Dict[str, Any]:
        total_rounds = 10 if scenario_mode == "baseline_mode" else 8
        if diffusion_template == "air":
            minutes_per_round = 30
        elif diffusion_template == "inland_water":
            minutes_per_round = 45
        else:
            minutes_per_round = 60
        return {
            "scenario_summary": (
                f"Semi-quantitative {diffusion_template} diffusion scenario with "
                f"{region_count} regions and {actor_count} eco-social actors."
            ),
            "generation_reasoning": (
                "Fallback deterministic plan: keep the simulation short, region-level, and centered on "
                "spread, vulnerability, intervention friction, and human-nature feedback."
            ),
            "total_rounds": total_rounds,
            "minutes_per_round": minutes_per_round,
            "round_label": "EnvFish simulation round",
            "report_focus": [
                "regional spread forecast",
                "human-nature feedback loops",
                "vulnerability ranking",
                "intervention deltas",
                "uncertainty bands",
            ],
        }
