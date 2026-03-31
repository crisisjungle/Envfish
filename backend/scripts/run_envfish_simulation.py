"""
EnvFish region-level simulation runner.

This is a constrained, semi-quantitative eco-social sandbox. It does not solve
physical equations; it produces region-level spread and human-nature feedback
using structured LLM output with deterministic validation and rule-based
fallbacks.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, ".."))
_project_root = os.path.abspath(os.path.join(_backend_dir, ".."))
sys.path.insert(0, _backend_dir)

from dotenv import load_dotenv

from app.services.envfish_models import (  # noqa: E402
    DEFAULT_TEMPLATE_RULES,
    clamp_probability,
    clamp_score,
    dump_json,
    merge_state_vectors,
    normalize_state_vector,
    score_band,
)
from app.services.simulation_ipc import CommandType, SimulationIPCServer  # noqa: E402
from app.utils.llm_client import LLMClient  # noqa: E402

if os.path.exists(os.path.join(_project_root, ".env")):
    load_dotenv(os.path.join(_project_root, ".env"))


def append_jsonl(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


class EnvFishRuntime:
    def __init__(self, config_path: str, max_rounds: Optional[int] = None, no_wait: bool = False):
        self.config_path = os.path.abspath(config_path)
        with open(self.config_path, "r", encoding="utf-8") as handle:
            self.config = json.load(handle)

        self.sim_dir = os.path.dirname(self.config_path)
        self.no_wait = no_wait
        self.template = self.config.get("diffusion_template", "generic")
        self.template_rules = DEFAULT_TEMPLATE_RULES.get(self.template, DEFAULT_TEMPLATE_RULES["generic"])
        total_rounds = int(self.config.get("time_config", {}).get("total_rounds", 8))
        self.total_rounds = min(total_rounds, max_rounds) if max_rounds else total_rounds
        self.minutes_per_round = int(self.config.get("time_config", {}).get("minutes_per_round", 60))
        self.region_graph = deepcopy(self.config.get("region_graph") or [])
        self.actor_profiles = deepcopy(self.config.get("actor_profiles") or self.config.get("agent_configs") or [])
        self.injections = deepcopy(self.config.get("injected_variables") or [])
        self.current_round = 0
        self.latest_summary = {}
        self.pending_transfers: List[Dict[str, Any]] = []
        self.closed = False

        self.twitter_dir = os.path.join(self.sim_dir, "twitter")
        self.reddit_dir = os.path.join(self.sim_dir, "reddit")
        os.makedirs(self.twitter_dir, exist_ok=True)
        os.makedirs(self.reddit_dir, exist_ok=True)

        self.twitter_log = os.path.join(self.twitter_dir, "actions.jsonl")
        self.reddit_log = os.path.join(self.reddit_dir, "actions.jsonl")
        self.spread_log = os.path.join(self.sim_dir, "spread_event_ledger.jsonl")
        self.state_matrix_log = os.path.join(self.sim_dir, "round_state_matrix.jsonl")
        self.intervention_log = os.path.join(self.sim_dir, "intervention_log.jsonl")
        self.interview_log = os.path.join(self.sim_dir, "interviews.jsonl")
        self.latest_snapshot_path = os.path.join(self.sim_dir, "latest_round_snapshot.json")
        self.region_graph_path = os.path.join(self.sim_dir, "region_graph_snapshot.json")

        dump_json(self.region_graph_path, self.region_graph)

        self.region_lookup = {item["region_id"]: item for item in self.region_graph}
        self.actor_lookup = {int(item.get("agent_id", idx)): item for idx, item in enumerate(self.actor_profiles)}

        self.ipc = SimulationIPCServer(self.sim_dir)
        self.llm = None
        try:
            self.llm = LLMClient()
        except Exception:
            self.llm = None

        for region in self.region_graph:
            region["state_vector"] = normalize_state_vector(region.get("state_vector") or {})
        for actor in self.actor_profiles:
            actor["state_vector"] = normalize_state_vector(actor.get("state_vector") or {})

    def run(self) -> None:
        self._write_platform_event("twitter", {"event_type": "simulation_start", "timestamp": self._now()})
        self._write_platform_event("reddit", {"event_type": "simulation_start", "timestamp": self._now()})
        self.ipc.start()
        self._write_env_status("alive")

        for round_num in range(1, self.total_rounds + 1):
            self.current_round = round_num
            self._drain_commands()

            active_variables = self._active_variables(round_num)
            diffusion = self._environmental_diffusion_update(round_num, active_variables)
            feedback = self._human_nature_feedback_update(round_num, active_variables, diffusion)
            snapshot = self._build_snapshot(round_num, active_variables, diffusion, feedback)
            self.latest_summary = snapshot

            append_jsonl(self.state_matrix_log, snapshot)
            dump_json(self.latest_snapshot_path, snapshot)

            simulated_hours = round(round_num * self.minutes_per_round / 60, 2)
            self._write_platform_event(
                "twitter",
                {
                    "event_type": "round_end",
                    "round": round_num,
                    "simulated_hours": simulated_hours,
                    "timestamp": self._now(),
                },
            )
            self._write_platform_event(
                "reddit",
                {
                    "event_type": "round_end",
                    "round": round_num,
                    "simulated_hours": simulated_hours,
                    "timestamp": self._now(),
                },
            )

            self._inter_round_poll()

        self._write_platform_event(
            "twitter",
            {
                "event_type": "simulation_end",
                "round": self.total_rounds,
                "total_rounds": self.total_rounds,
                "timestamp": self._now(),
            },
        )
        self._write_platform_event(
            "reddit",
            {
                "event_type": "simulation_end",
                "round": self.total_rounds,
                "total_rounds": self.total_rounds,
                "timestamp": self._now(),
            },
        )

        if self.no_wait:
            self._write_env_status("stopped")
            self.ipc.stop()
            return

        while not self.closed:
            self._drain_commands()
            time.sleep(0.4)

        self._write_env_status("stopped")
        self.ipc.stop()

    def _environmental_diffusion_update(
        self,
        round_num: int,
        active_variables: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        due_transfers = [item for item in self.pending_transfers if item["apply_round"] <= round_num]
        self.pending_transfers = [item for item in self.pending_transfers if item["apply_round"] > round_num]
        llm_result = self._llm_diffusion(round_num, active_variables, due_transfers)
        if not llm_result:
            llm_result = self._fallback_diffusion(round_num, active_variables, due_transfers)

        valid_transfers = []
        for transfer in llm_result.get("transfers") or []:
            validated = self._validate_transfer(transfer, active_variables)
            if validated:
                valid_transfers.append(validated)
                if validated["delay_rounds"] > 0:
                    scheduled = dict(validated)
                    scheduled["apply_round"] = round_num + int(validated["delay_rounds"])
                    self.pending_transfers.append(scheduled)

        immediate = [transfer for transfer in valid_transfers if transfer["delay_rounds"] <= 0]
        region_updates = defaultdict(lambda: defaultdict(float))
        for transfer in due_transfers + immediate:
            target = self.region_lookup.get(transfer["target_region"])
            if not target:
                continue
            delta = min(18.0, transfer["transfer_intensity"] * 0.18)
            region_updates[target["region_id"]]["exposure_score"] += delta
            region_updates[target["region_id"]]["spread_pressure"] += max(3.0, delta * 0.65)
            region_updates[target["region_id"]]["ecosystem_integrity"] -= max(2.0, delta * 0.22)

            append_jsonl(
                self.spread_log,
                {
                    "round": round_num,
                    "timestamp": self._now(),
                    "source_region": transfer["source_region"],
                    "target_region": transfer["target_region"],
                    "transfer_intensity": transfer["transfer_intensity"],
                    "delay_rounds": transfer["delay_rounds"],
                    "persistence": transfer["persistence"],
                    "confidence": transfer["confidence"],
                    "rationale": transfer["rationale"],
                },
            )
            self._write_action(
                platform="twitter",
                round_num=round_num,
                agent_id=500000 + self._region_index(transfer["source_region"]),
                agent_name=self.region_lookup.get(transfer["source_region"], {}).get("name", "EnvField"),
                action_type="SPREAD_UPDATE",
                action_args=transfer,
                result=transfer["rationale"],
            )

        for region_id, deltas in region_updates.items():
            region = self.region_lookup.get(region_id)
            if region:
                region["state_vector"] = merge_state_vectors(region["state_vector"], deltas)

        ranking = sorted(
            [
                {
                    "region_id": region["region_id"],
                    "name": region["name"],
                    "exposure_score": region["state_vector"]["exposure_score"],
                    "severity_band": score_band(region["state_vector"]["exposure_score"]),
                }
                for region in self.region_graph
            ],
            key=lambda item: item["exposure_score"],
            reverse=True,
        )
        return {
            "transfers": valid_transfers,
            "applied_transfers": due_transfers + immediate,
            "region_ranking": ranking,
            "likely_next_impacted_regions": [item["name"] for item in ranking[:3]],
        }

    def _human_nature_feedback_update(
        self,
        round_num: int,
        active_variables: List[Dict[str, Any]],
        diffusion: Dict[str, Any],
    ) -> Dict[str, Any]:
        llm_result = self._llm_feedback(round_num, active_variables, diffusion)
        if not llm_result:
            llm_result = self._fallback_feedback(round_num, active_variables, diffusion)

        actor_decisions = []
        ecological_impacts = []
        feedback_propagation = []

        for item in llm_result.get("ecological_impacts") or []:
            region = self.region_lookup.get(item.get("region_id"))
            if not region:
                continue
            delta = {
                "ecosystem_integrity": -abs(float(item.get("ecosystem_integrity_delta", 0))),
                "vulnerability_score": abs(float(item.get("vulnerability_delta", 0))),
                "livelihood_stability": -abs(float(item.get("livelihood_delta", 0))),
            }
            region["state_vector"] = merge_state_vectors(region["state_vector"], delta)
            ecological_impacts.append(
                {
                    "region_id": region["region_id"],
                    "region_name": region["name"],
                    "note": item.get("note", ""),
                    "delta": delta,
                }
            )
            self._write_action(
                platform="twitter",
                round_num=round_num,
                agent_id=600000 + self._region_index(region["region_id"]),
                agent_name=region["name"],
                action_type="ECO_IMPACT",
                action_args=delta,
                result=item.get("note", ""),
            )

        for item in llm_result.get("actor_decisions") or []:
            agent_id = int(item.get("agent_id", -1))
            actor = self.actor_lookup.get(agent_id)
            if not actor:
                continue
            delta = {
                "panic_level": float(item.get("panic_delta", 0)),
                "public_trust": float(item.get("trust_delta", 0)),
                "economic_stress": float(item.get("economic_delta", 0)),
                "response_capacity": float(item.get("response_delta", 0)),
            }
            actor["state_vector"] = merge_state_vectors(actor["state_vector"], delta)
            action_type = str(item.get("action_type") or "DECISION")
            actor_decisions.append(
                {
                    "agent_id": agent_id,
                    "agent_name": actor.get("username") or actor.get("name"),
                    "action_type": action_type,
                    "rationale": item.get("rationale", ""),
                    "delta": delta,
                }
            )
            self._write_action(
                platform="reddit",
                round_num=round_num,
                agent_id=agent_id,
                agent_name=actor.get("username") or actor.get("name"),
                action_type=action_type,
                action_args=delta,
                result=item.get("rationale", ""),
            )

        for item in llm_result.get("feedback_propagation") or []:
            region = self.region_lookup.get(item.get("region_id"))
            if not region:
                continue
            delta = {
                "panic_level": float(item.get("panic_delta", 0)),
                "public_trust": float(item.get("trust_delta", 0)),
                "economic_stress": float(item.get("economic_delta", 0)),
                "livelihood_stability": float(item.get("livelihood_delta", 0)),
                "service_capacity": float(item.get("service_delta", 0)),
            }
            region["state_vector"] = merge_state_vectors(region["state_vector"], delta)
            feedback_propagation.append(
                {
                    "region_id": region["region_id"],
                    "region_name": region["name"],
                    "delta": delta,
                    "loop": item.get("loop", ""),
                }
            )

        return {
            "ecological_impacts": ecological_impacts,
            "actor_decisions": actor_decisions,
            "feedback_propagation": feedback_propagation,
            "turning_points": llm_result.get("turning_points") or [],
        }

    def _build_snapshot(
        self,
        round_num: int,
        active_variables: List[Dict[str, Any]],
        diffusion: Dict[str, Any],
        feedback: Dict[str, Any],
    ) -> Dict[str, Any]:
        regions = []
        for region in self.region_graph:
            vector = normalize_state_vector(region.get("state_vector") or {})
            regions.append(
                {
                    "region_id": region["region_id"],
                    "name": region["name"],
                    "region_type": region.get("region_type"),
                    "neighbors": region.get("neighbors", []),
                    "state_vector": vector,
                    **vector,
                    "severity_band": score_band(vector["exposure_score"]),
                    "uncertainty_band": self._uncertainty_band(vector),
                }
            )
        vulnerability_ranking = sorted(
            [
                {
                    "region_id": item["region_id"],
                    "name": item["name"],
                    "vulnerability_score": item["state_vector"]["vulnerability_score"],
                    "exposure_score": item["state_vector"]["exposure_score"],
                }
                for item in regions
            ],
            key=lambda item: (item["vulnerability_score"], item["exposure_score"]),
            reverse=True,
        )
        return {
            "round": round_num,
            "timestamp": self._now(),
            "active_variables": active_variables,
            "regions": regions,
            "top_regions": regions[:3],
            "diffusion": diffusion,
            "feedback": feedback,
            "vulnerability_ranking": vulnerability_ranking,
        }

    def _llm_diffusion(
        self,
        round_num: int,
        active_variables: List[Dict[str, Any]],
        due_transfers: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not self.llm:
            return None
        prompt = {
            "task": "Return constrained JSON for region-level pollution spread.",
            "round": round_num,
            "template": self.template,
            "rules": self.template_rules,
            "regions": [
                {
                    "region_id": region["region_id"],
                    "name": region["name"],
                    "neighbors": region.get("neighbors", []),
                    "state_vector": region.get("state_vector", {}),
                }
                for region in self.region_graph
            ],
            "active_variables": active_variables,
            "due_transfers": due_transfers,
            "schema": {
                "transfers": [
                    {
                        "source_region": "region_id",
                        "target_region": "region_id",
                        "transfer_intensity": 0,
                        "delay_rounds": 0,
                        "persistence": 0,
                        "confidence": 0.5,
                        "rationale": "string",
                    }
                ]
            },
            "constraints": [
                "Only connect neighbors or self.",
                "No teleporting spread.",
                "Keep transfer_intensity between 0 and 100.",
                "If there is no active pressure, return an empty transfer list.",
            ],
        }
        try:
            return self.llm.chat_json(
                messages=[
                    {"role": "system", "content": "Return compact JSON only. Respect constraints."},
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                temperature=0.2,
                max_tokens=1400,
            )
        except Exception:
            return None

    def _fallback_diffusion(
        self,
        round_num: int,
        active_variables: List[Dict[str, Any]],
        due_transfers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        transfers = []
        decay = self.template_rules["default_decay"]
        lag = self.template_rules["default_lag_rounds"]
        for variable in active_variables:
            source_regions = variable.get("target_regions") or [self.region_graph[0]["region_id"]]
            for source in source_regions:
                transfers.append(
                    {
                        "source_region": source,
                        "target_region": source,
                        "transfer_intensity": clamp_score(variable.get("intensity_0_100", 50)),
                        "delay_rounds": 0,
                        "persistence": clamp_score(self.template_rules["default_persistence"] + variable.get("intensity_0_100", 50) * 0.1),
                        "confidence": 0.62,
                        "rationale": f"Direct pressure from injected variable {variable.get('name')}.",
                    }
                )
                region = self.region_lookup.get(source, {})
                for neighbor in region.get("neighbors", [])[: self.template_rules["max_neighbor_spread"]]:
                    transfers.append(
                        {
                            "source_region": source,
                            "target_region": neighbor,
                            "transfer_intensity": clamp_score(variable.get("intensity_0_100", 50) * decay),
                            "delay_rounds": lag,
                            "persistence": clamp_score(self.template_rules["default_persistence"]),
                            "confidence": 0.56,
                            "rationale": f"Template-driven diffusion from {source} to connected region.",
                        }
                    )
        for due in due_transfers:
            target_region = self.region_lookup.get(due["target_region"], {})
            for neighbor in target_region.get("neighbors", [])[:1]:
                transfers.append(
                    {
                        "source_region": due["target_region"],
                        "target_region": neighbor,
                        "transfer_intensity": clamp_score(due["transfer_intensity"] * decay * 0.8),
                        "delay_rounds": lag,
                        "persistence": clamp_score(due["persistence"] * decay),
                        "confidence": 0.5,
                        "rationale": "Secondary propagation from already impacted region.",
                    }
                )
        return {"transfers": transfers}

    def _llm_feedback(
        self,
        round_num: int,
        active_variables: List[Dict[str, Any]],
        diffusion: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not self.llm:
            return None
        top_regions = diffusion.get("region_ranking", [])[:4]
        top_actors = sorted(
            self.actor_profiles,
            key=lambda actor: actor.get("state_vector", {}).get("vulnerability_score", 0),
            reverse=True,
        )[:8]
        prompt = {
            "task": "Produce constrained JSON for ecological impact, actor decisions, and feedback propagation.",
            "round": round_num,
            "active_variables": active_variables,
            "top_regions": top_regions,
            "top_actors": top_actors,
            "schema": {
                "ecological_impacts": [
                    {
                        "region_id": "region_id",
                        "ecosystem_integrity_delta": 0,
                        "vulnerability_delta": 0,
                        "livelihood_delta": 0,
                        "note": "string",
                    }
                ],
                "actor_decisions": [
                    {
                        "agent_id": 0,
                        "action_type": "DISCLOSE|PANIC_POST|MARKET_SHIFT|RESTRICT|RELOCATE",
                        "panic_delta": 0,
                        "trust_delta": 0,
                        "economic_delta": 0,
                        "response_delta": 0,
                        "rationale": "string",
                    }
                ],
                "feedback_propagation": [
                    {
                        "region_id": "region_id",
                        "panic_delta": 0,
                        "trust_delta": 0,
                        "economic_delta": 0,
                        "livelihood_delta": 0,
                        "service_delta": 0,
                        "loop": "string",
                    }
                ],
                "turning_points": ["string"],
            },
            "constraints": [
                "Keep all deltas between -20 and 20.",
                "Use real agent_id values only.",
                "Keep at most 5 actor decisions.",
                "Return valid JSON only.",
            ],
        }
        try:
            return self.llm.chat_json(
                messages=[
                    {"role": "system", "content": "Return compact JSON only."},
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                temperature=0.25,
                max_tokens=1800,
            )
        except Exception:
            return None

    def _fallback_feedback(
        self,
        round_num: int,
        active_variables: List[Dict[str, Any]],
        diffusion: Dict[str, Any],
    ) -> Dict[str, Any]:
        top_regions = diffusion.get("region_ranking", [])[:3]
        ecological_impacts = []
        feedback_propagation = []
        for item in top_regions:
            ecological_impacts.append(
                {
                    "region_id": item["region_id"],
                    "ecosystem_integrity_delta": clamp_score(item["exposure_score"] * 0.08, 0, 20),
                    "vulnerability_delta": clamp_score(item["exposure_score"] * 0.05, 0, 20),
                    "livelihood_delta": clamp_score(item["exposure_score"] * 0.04, 0, 20),
                    "note": "Exposure degrades ecological integrity and nearby livelihoods.",
                }
            )
            feedback_propagation.append(
                {
                    "region_id": item["region_id"],
                    "panic_delta": min(16, item["exposure_score"] * 0.07),
                    "trust_delta": -min(14, item["exposure_score"] * 0.05),
                    "economic_delta": min(16, item["exposure_score"] * 0.06),
                    "livelihood_delta": -min(14, item["exposure_score"] * 0.05),
                    "service_delta": -min(10, item["exposure_score"] * 0.03),
                    "loop": "environment -> ecology -> livelihood -> panic/media -> market behavior",
                }
            )

        actor_decisions = []
        for actor in self.actor_profiles[: min(5, len(self.actor_profiles))]:
            primary_region = self.region_lookup.get(actor.get("primary_region"))
            if not primary_region:
                continue
            exposure = primary_region.get("state_vector", {}).get("exposure_score", 0)
            if actor.get("node_family") == "GovernmentActor":
                actor_decisions.append(
                    {
                        "agent_id": actor["agent_id"],
                        "action_type": "DISCLOSE" if exposure < 60 else "RESTRICT",
                        "panic_delta": -4 if exposure < 60 else 3,
                        "trust_delta": 4 if exposure < 60 else -2,
                        "economic_delta": 2 if exposure >= 60 else 0,
                        "response_delta": 5,
                        "rationale": "Authorities react by disclosure in moderate cases and restrictions in severe cases.",
                    }
                )
            elif actor.get("node_family") in {"HumanActor", "OrganizationActor"}:
                actor_decisions.append(
                    {
                        "agent_id": actor["agent_id"],
                        "action_type": "MARKET_SHIFT" if exposure > 45 else "PANIC_POST",
                        "panic_delta": 4 if exposure > 35 else 2,
                        "trust_delta": -2,
                        "economic_delta": 5 if exposure > 45 else 1,
                        "response_delta": -1,
                        "rationale": "Affected actors react through rumor amplification or adaptive market behavior.",
                    }
                )

        return {
            "ecological_impacts": ecological_impacts,
            "actor_decisions": actor_decisions[:5],
            "feedback_propagation": feedback_propagation,
            "turning_points": [f"Round {round_num} increased visible stress in {item['name']}" for item in top_regions[:2]],
        }

    def _validate_transfer(self, transfer: Dict[str, Any], active_variables: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        source = transfer.get("source_region")
        target = transfer.get("target_region")
        if source not in self.region_lookup or target not in self.region_lookup:
            return None
        if source != target and target not in self.region_lookup[source].get("neighbors", []):
            return None
        validated = {
            "source_region": source,
            "target_region": target,
            "transfer_intensity": clamp_score(transfer.get("transfer_intensity", 0)),
            "delay_rounds": max(0, int(transfer.get("delay_rounds", 0))),
            "persistence": clamp_score(transfer.get("persistence", self.template_rules["default_persistence"])),
            "confidence": clamp_probability(transfer.get("confidence", 0.5)),
            "rationale": str(transfer.get("rationale", "")),
        }
        if not active_variables and validated["transfer_intensity"] > 18:
            validated["transfer_intensity"] = 18
        return validated

    def _active_variables(self, round_num: int) -> List[Dict[str, Any]]:
        active = []
        for variable in self.injections:
            start = int(variable.get("start_round", 1))
            duration = int(variable.get("duration_rounds", 1))
            if start <= round_num < start + duration:
                active.append(variable)
        return active

    def _drain_commands(self) -> None:
        while True:
            command = self.ipc.poll_commands()
            if not command:
                return
            try:
                if command.command_type == CommandType.CLOSE_ENV:
                    self.closed = True
                    self.ipc.send_success(command.command_id, {"message": "EnvFish environment closing"})
                elif command.command_type == CommandType.INJECT_VARIABLE:
                    variable = command.args.get("variable") or {}
                    if "start_round" not in variable or not variable["start_round"]:
                        variable["start_round"] = self.current_round + 1 if self.current_round else 1
                    self.injections.append(variable)
                    append_jsonl(
                        self.intervention_log,
                        {
                            "timestamp": self._now(),
                            "round": self.current_round,
                            "variable": variable,
                            "status": "accepted",
                        },
                    )
                    self.ipc.send_success(
                        command.command_id,
                        {"message": "variable queued", "variable": variable, "current_round": self.current_round},
                    )
                elif command.command_type == CommandType.INTERVIEW:
                    result = self._interview_single(
                        agent_id=int(command.args.get("agent_id", -1)),
                        prompt=str(command.args.get("prompt", "")),
                    )
                    self.ipc.send_success(command.command_id, result)
                elif command.command_type == CommandType.BATCH_INTERVIEW:
                    interviews = command.args.get("interviews") or []
                    results = {}
                    for item in interviews:
                        result = self._interview_single(
                            agent_id=int(item.get("agent_id", -1)),
                            prompt=str(item.get("prompt", "")),
                        )
                        if result.get("results"):
                            results.update(result["results"])
                    self.ipc.send_success(
                        command.command_id,
                        {"results": results, "engine_mode": "envfish", "interviews_count": len(interviews)},
                    )
                else:
                    self.ipc.send_error(command.command_id, f"Unsupported command: {command.command_type}")
            except Exception as exc:
                self.ipc.send_error(command.command_id, str(exc))

    def _inter_round_poll(self) -> None:
        started = time.time()
        while time.time() - started < 0.9:
            self._drain_commands()
            time.sleep(0.15)

    def _interview_single(self, agent_id: int, prompt: str) -> Dict[str, Any]:
        actor = self.actor_lookup.get(agent_id)
        if not actor:
            raise ValueError(f"Unknown agent_id: {agent_id}")
        region = self.region_lookup.get(actor.get("primary_region"), {})
        response = self._answer_interview(actor, region, prompt)
        record = {
            "timestamp": self._now(),
            "round": self.current_round,
            "agent_id": agent_id,
            "agent_name": actor.get("username") or actor.get("name"),
            "profession": actor.get("profession"),
            "prompt": prompt,
            "response": response,
            "region": region.get("name"),
        }
        append_jsonl(self.interview_log, record)
        result = {
            f"reddit_{agent_id}": {
                "agent_id": agent_id,
                "agent_name": actor.get("username") or actor.get("name"),
                "profession": actor.get("profession"),
                "response": response,
                "answer": response,
            },
            f"twitter_{agent_id}": {
                "agent_id": agent_id,
                "agent_name": actor.get("username") or actor.get("name"),
                "profession": actor.get("profession"),
                "response": response,
                "answer": response,
            },
        }
        return {"results": result, "engine_mode": "envfish"}

    def _answer_interview(self, actor: Dict[str, Any], region: Dict[str, Any], prompt: str) -> str:
        if self.llm:
            payload = {
                "task": "Answer in first person as an EnvFish simulated actor.",
                "actor": {
                    "name": actor.get("name"),
                    "username": actor.get("username"),
                    "profession": actor.get("profession"),
                    "node_family": actor.get("node_family"),
                    "persona": actor.get("persona"),
                    "bio": actor.get("bio"),
                    "state_vector": actor.get("state_vector"),
                },
                "region": {
                    "name": region.get("name"),
                    "state_vector": region.get("state_vector"),
                },
                "latest_summary": self.latest_summary.get("feedback", {}),
                "question": prompt,
                "rules": [
                    "Respond in first person.",
                    "Stay within the simulation context.",
                    "Do not mention being an AI model.",
                    "Keep the answer under 180 words.",
                ],
            }
            try:
                return self.llm.chat(
                    messages=[
                        {"role": "system", "content": "You are roleplaying a simulation actor. Be concise and grounded."},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                    temperature=0.5,
                    max_tokens=300,
                )
            except Exception:
                pass

        exposure = region.get("state_vector", {}).get("exposure_score", 0)
        panic = region.get("state_vector", {}).get("panic_level", 0)
        return (
            f"我主要关注 {region.get('name', '本地区')} 的局势。现在暴露压力大约在 {exposure:.0f}/100，"
            f"社会恐慌大约在 {panic:.0f}/100。以我的角色来看，最明显的问题是"
            f"{actor.get('profession', actor.get('role_type', '相关主体'))}需要在生态风险和生计压力之间做取舍。"
        )

    def _write_action(
        self,
        platform: str,
        round_num: int,
        agent_id: int,
        agent_name: str,
        action_type: str,
        action_args: Dict[str, Any],
        result: str = "",
    ) -> None:
        payload = {
            "round": round_num,
            "timestamp": self._now(),
            "agent_id": agent_id,
            "agent_name": agent_name,
            "action_type": action_type,
            "action_args": action_args,
            "result": result,
            "success": True,
            "platform": platform,
        }
        append_jsonl(self.twitter_log if platform == "twitter" else self.reddit_log, payload)

    def _write_platform_event(self, platform: str, payload: Dict[str, Any]) -> None:
        append_jsonl(self.twitter_log if platform == "twitter" else self.reddit_log, payload)

    def _write_env_status(self, status: str) -> None:
        dump_json(
            os.path.join(self.sim_dir, "env_status.json"),
            {
                "status": status,
                "timestamp": self._now(),
                "engine_mode": "envfish",
                "twitter_available": True,
                "reddit_available": True,
            },
        )

    def _region_index(self, region_id: str) -> int:
        for index, region in enumerate(self.region_graph):
            if region["region_id"] == region_id:
                return index
        return 0

    def _uncertainty_band(self, vector: Dict[str, Any]) -> Dict[str, Any]:
        trust = clamp_score(vector.get("public_trust", 50))
        exposure = clamp_score(vector.get("exposure_score", 0))
        confidence = clamp_probability((trust / 100 * 0.3) + (1 - exposure / 100) * 0.4 + 0.3)
        return {
            "confidence": confidence,
            "label": "higher" if confidence >= 0.7 else "medium" if confidence >= 0.45 else "low",
        }

    def _now(self) -> str:
        return datetime.now().isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--max-rounds", type=int)
    parser.add_argument("--no-wait", action="store_true")
    args = parser.parse_args()

    runtime = EnvFishRuntime(config_path=args.config, max_rounds=args.max_rounds, no_wait=args.no_wait)
    runtime.run()


if __name__ == "__main__":
    random.seed(42)
    main()
