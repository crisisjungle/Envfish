"""
EnvFish actor and region generation from Zep entities.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .data_grounding import PublicDataGroundingService
from .envfish_models import (
    DIFFUSION_TEMPLATES,
    EnvAgentProfile,
    EnvProfileGenerationResult,
    RegionNode,
    default_state_vector,
    ensure_unique_slug,
    infer_node_family,
    normalize_state_vector,
)
from .zep_entity_reader import EntityNode

logger = get_logger("envfish.envfish_profile")


@dataclass
class PreparedEntityContext:
    entity: EntityNode
    entity_type: str
    node_family: str
    summary: str
    relation_hints: List[str]


class EnvProfileGenerator:
    """
    Builds an EnvFish region graph and mixed eco-social actor set.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        grounding_service: Optional[PublicDataGroundingService] = None,
    ):
        self.llm_client = llm_client
        self.grounding_service = grounding_service or PublicDataGroundingService()
        if self.llm_client is None and Config.LLM_API_KEY:
            try:
                self.llm_client = LLMClient()
            except Exception as exc:
                logger.warning(f"EnvProfileGenerator LLM init failed, will use fallbacks: {exc}")

    def generate_from_entities(
        self,
        entities: List[EntityNode],
        simulation_requirement: str,
        document_text: str,
        scenario_mode: str = "baseline_mode",
        diffusion_template: str = "marine",
        use_llm: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        parallel_count: int = 3,
    ) -> EnvProfileGenerationResult:
        prepared_entities = [self._prepare_entity(entity) for entity in entities]
        regions = self._build_regions(
            prepared_entities=prepared_entities,
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            scenario_mode=scenario_mode,
            diffusion_template=diffusion_template,
        )
        grounding_summary = self.grounding_service.ground(
            regions=[region.to_dict() for region in regions],
            diffusion_template=diffusion_template,
            document_text=document_text,
        )
        self._apply_grounding_priors(regions, grounding_summary)

        profiles: List[EnvAgentProfile] = []
        total = len(prepared_entities)
        if progress_callback:
            progress_callback(0, total, "开始生成 EnvFish 角色")

        def build_profile(args: Tuple[int, PreparedEntityContext]) -> EnvAgentProfile:
            index, prepared = args
            return self._build_profile(
                index=index,
                prepared=prepared,
                regions=regions,
                scenario_mode=scenario_mode,
                simulation_requirement=simulation_requirement,
                use_llm=use_llm,
            )

        if parallel_count > 1 and total > 1:
            with ThreadPoolExecutor(max_workers=min(parallel_count, total)) as executor:
                future_map = {
                    executor.submit(build_profile, item): item[0] for item in enumerate(prepared_entities)
                }
                completed = 0
                ordered: Dict[int, EnvAgentProfile] = {}
                for future in as_completed(future_map):
                    ordered[future_map[future]] = future.result()
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, f"已生成 {completed}/{total} 个角色")
                profiles = [ordered[index] for index in sorted(ordered.keys())]
        else:
            for index, prepared in enumerate(prepared_entities):
                profiles.append(build_profile((index, prepared)))
                if progress_callback:
                    progress_callback(index + 1, total, f"已生成 {index + 1}/{total} 个角色")

        notes = [
            f"Generated {len(regions)} regions and {len(profiles)} actor profiles.",
            f"Diffusion template: {diffusion_template}",
            f"Scenario mode: {scenario_mode}",
        ]
        if grounding_summary.get("successful_sources"):
            notes.append(f"Grounding sources: {', '.join(grounding_summary['successful_sources'])}")

        return EnvProfileGenerationResult(
            regions=regions,
            profiles=profiles,
            grounding_summary=grounding_summary,
            generation_notes=notes,
        )

    def _prepare_entity(self, entity: EntityNode) -> PreparedEntityContext:
        entity_type = entity.get_entity_type() or "Entity"
        relation_hints = []
        for item in entity.related_nodes[:6]:
            related_name = item.get("name")
            related_label = item.get("entity_type") or ""
            if related_name:
                relation_hints.append(f"{related_name} ({related_label})")
        summary = entity.summary or entity.attributes.get("description") or entity.attributes.get("summary") or entity.name
        return PreparedEntityContext(
            entity=entity,
            entity_type=entity_type,
            node_family=infer_node_family(entity_type, entity.name, summary),
            summary=summary,
            relation_hints=relation_hints,
        )

    def _build_regions(
        self,
        prepared_entities: List[PreparedEntityContext],
        simulation_requirement: str,
        document_text: str,
        scenario_mode: str,
        diffusion_template: str,
    ) -> List[RegionNode]:
        if diffusion_template not in DIFFUSION_TEMPLATES:
            diffusion_template = "generic"

        region_candidates = self._region_candidates_from_entities(prepared_entities)
        llm_regions = self._build_regions_with_llm(
            region_candidates=region_candidates,
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            scenario_mode=scenario_mode,
            diffusion_template=diffusion_template,
        )
        if llm_regions:
            return llm_regions
        return self._build_regions_rule_based(region_candidates, scenario_mode, diffusion_template)

    def _region_candidates_from_entities(self, prepared_entities: List[PreparedEntityContext]) -> List[Dict[str, Any]]:
        candidates = []
        for prepared in prepared_entities:
            haystack = f"{prepared.entity_type} {prepared.entity.name} {prepared.summary}".lower()
            if prepared.node_family == "Region" or any(
                token in haystack for token in ("region", "city", "county", "district", "province", "coast", "bay", "port", "river")
            ):
                candidates.append(
                    {
                        "name": prepared.entity.name,
                        "description": prepared.summary,
                        "entity_type": prepared.entity_type,
                        "tags": [prepared.entity_type, prepared.node_family],
                    }
                )

        if not candidates and prepared_entities:
            first = prepared_entities[0]
            candidates.append(
                {
                    "name": first.entity.attributes.get("location")
                    or first.entity.attributes.get("region")
                    or "Core Region",
                    "description": "Fallback region synthesized from the seed report.",
                    "entity_type": "Region",
                    "tags": ["fallback"],
                }
            )
        return candidates[:8]

    def _build_regions_with_llm(
        self,
        region_candidates: List[Dict[str, Any]],
        simulation_requirement: str,
        document_text: str,
        scenario_mode: str,
        diffusion_template: str,
    ) -> List[RegionNode]:
        if not self.llm_client or not document_text.strip():
            return []

        prompt = {
            "task": "Build a region-level adjacency graph for an eco-social disaster simulation.",
            "scenario_mode": scenario_mode,
            "diffusion_template": diffusion_template,
            "region_candidates": region_candidates,
            "requirement": simulation_requirement[:1500],
            "document_excerpt": document_text[:6000],
            "output_schema": {
                "regions": [
                    {
                        "name": "Region name",
                        "region_type": "coastal_zone/city/river_basin/port/industrial_zone/residential_zone",
                        "description": "short explanation",
                        "neighbors": ["neighbor names"],
                        "carriers": ["air_mass/river_segment/coastal_current/soil_zone"],
                        "tags": ["coastal", "fishery", "urban"],
                    }
                ]
            },
            "rules": [
                "Return 1-6 regions only.",
                "Neighbors must refer to other listed regions.",
                "Prefer region-level units, not single buildings.",
                "If information is sparse, still return at least one region.",
            ],
        }

        try:
            result = self.llm_client.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": "You produce compact, valid JSON for a region-level eco-social simulation graph.",
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                temperature=0.2,
                max_tokens=2500,
            )
        except Exception as exc:
            logger.warning(f"Region graph LLM generation failed, falling back: {exc}")
            return []

        raw_regions = result.get("regions") or []
        if not isinstance(raw_regions, list) or not raw_regions:
            return []

        used: set[str] = set()
        regions: List[RegionNode] = []
        name_to_id: Dict[str, str] = {}
        for item in raw_regions[:6]:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            region_id = ensure_unique_slug(name, used)
            name_to_id[name] = region_id
            regions.append(
                RegionNode(
                    region_id=region_id,
                    name=name,
                    region_type=str(item.get("region_type") or "region"),
                    description=str(item.get("description") or ""),
                    carriers=[str(carrier) for carrier in (item.get("carriers") or [])[:4]],
                    tags=[str(tag) for tag in (item.get("tags") or [])[:6]],
                    state_vector=default_state_vector(scenario_mode, "Region"),
                )
            )

        if not regions:
            return []

        raw_lookup = {str(item.get("name") or "").strip(): item for item in raw_regions}
        for region in regions:
            raw_item = raw_lookup.get(region.name, {})
            for neighbor_name in raw_item.get("neighbors") or []:
                neighbor_id = name_to_id.get(str(neighbor_name).strip())
                if neighbor_id and neighbor_id != region.region_id:
                    region.neighbors.append(neighbor_id)
        self._ensure_region_connectivity(regions, diffusion_template)
        return regions

    def _build_regions_rule_based(
        self,
        region_candidates: List[Dict[str, Any]],
        scenario_mode: str,
        diffusion_template: str,
    ) -> List[RegionNode]:
        if not region_candidates:
            region_candidates = [{"name": "Core Region", "description": "Fallback region", "tags": ["fallback"]}]

        used: set[str] = set()
        regions: List[RegionNode] = []
        for item in region_candidates[:4]:
            name = str(item.get("name") or "Region").strip()
            region_id = ensure_unique_slug(name, used)
            regions.append(
                RegionNode(
                    region_id=region_id,
                    name=name,
                    region_type=str(item.get("entity_type") or "region"),
                    description=str(item.get("description") or ""),
                    carriers=self._default_carriers(diffusion_template),
                    tags=[str(tag) for tag in (item.get("tags") or [])[:4]],
                    state_vector=default_state_vector(scenario_mode, "Region"),
                )
            )

        self._ensure_region_connectivity(regions, diffusion_template)
        return regions

    def _ensure_region_connectivity(self, regions: List[RegionNode], diffusion_template: str) -> None:
        if len(regions) <= 1:
            return
        for index, region in enumerate(regions):
            if not region.carriers:
                region.carriers = self._default_carriers(diffusion_template)
            if index > 0 and regions[index - 1].region_id not in region.neighbors:
                region.neighbors.append(regions[index - 1].region_id)
            if index < len(regions) - 1 and regions[index + 1].region_id not in region.neighbors:
                region.neighbors.append(regions[index + 1].region_id)

    def _default_carriers(self, diffusion_template: str) -> List[str]:
        if diffusion_template == "air":
            return ["air_mass"]
        if diffusion_template == "inland_water":
            return ["river_segment"]
        if diffusion_template == "marine":
            return ["coastal_current"]
        return ["environmental_link"]

    def _apply_grounding_priors(self, regions: List[RegionNode], grounding_summary: Dict[str, Any]) -> None:
        records = grounding_summary.get("records") or []
        lookup = {region.name: region for region in regions}
        for record in records:
            region_name = record.get("metadata", {}).get("region")
            region = lookup.get(region_name)
            if not region:
                continue
            merged = dict(region.state_vector)
            for key, value in (record.get("priors") or {}).items():
                if key in merged:
                    merged[key] = max(0.0, min(100.0, (merged[key] + float(value)) / 2))
            region.state_vector = normalize_state_vector(merged)

    def _build_profile(
        self,
        index: int,
        prepared: PreparedEntityContext,
        regions: List[RegionNode],
        scenario_mode: str,
        simulation_requirement: str,
        use_llm: bool,
    ) -> EnvAgentProfile:
        primary_region = self._match_region(prepared, regions)
        state_vector = default_state_vector(scenario_mode, prepared.node_family)
        base_goals = self._default_goals(prepared.node_family, primary_region.name)
        sensitivities = self._default_sensitivities(prepared.node_family, primary_region.name)

        llm_payload = None
        if use_llm and self.llm_client:
            llm_payload = self._generate_profile_with_llm(
                prepared=prepared,
                primary_region=primary_region,
                simulation_requirement=simulation_requirement,
            )

        username = self._username_from_name(prepared.entity.name, index)
        profession = (
            (llm_payload or {}).get("profession")
            or prepared.entity.attributes.get("role")
            or prepared.entity.attributes.get("profession")
            or prepared.entity_type
        )
        bio = (
            (llm_payload or {}).get("bio")
            or f"{prepared.entity.name} is a {prepared.entity_type} rooted in {primary_region.name}."
        )
        persona = (
            (llm_payload or {}).get("persona")
            or f"{prepared.entity.name} tracks local ecological change, social pressure, and risk trade-offs."
        )
        goals = [str(item) for item in ((llm_payload or {}).get("goals") or base_goals)][:6]
        sensitivities = [str(item) for item in ((llm_payload or {}).get("sensitivities") or sensitivities)][:6]
        influenced_regions = [primary_region.region_id] + [
            region.region_id
            for region in regions
            if region.region_id != primary_region.region_id and region.region_id in primary_region.neighbors[:2]
        ]

        return EnvAgentProfile(
            agent_id=index,
            username=username,
            name=prepared.entity.name,
            node_family=prepared.node_family,
            role_type=prepared.entity_type,
            bio=bio,
            persona=persona,
            profession=str(profession),
            primary_region=primary_region.region_id,
            influenced_regions=influenced_regions,
            goals=goals,
            sensitivities=sensitivities,
            state_vector=state_vector,
            source_entity_uuid=prepared.entity.uuid,
            source_entity_type=prepared.entity_type,
        )

    def _match_region(self, prepared: PreparedEntityContext, regions: List[RegionNode]) -> RegionNode:
        haystack = f"{prepared.entity.name} {prepared.summary} {json.dumps(prepared.entity.attributes, ensure_ascii=False)}".lower()
        for region in regions:
            if region.name.lower() in haystack or region.region_id.replace("_", " ") in haystack:
                return region
        return regions[0]

    def _generate_profile_with_llm(
        self,
        prepared: PreparedEntityContext,
        primary_region: RegionNode,
        simulation_requirement: str,
    ) -> Optional[Dict[str, Any]]:
        prompt = {
            "task": "Create a compact eco-social simulation role profile as JSON.",
            "entity_name": prepared.entity.name,
            "entity_type": prepared.entity_type,
            "node_family": prepared.node_family,
            "summary": prepared.summary,
            "attributes": prepared.entity.attributes,
            "relation_hints": prepared.relation_hints,
            "primary_region": primary_region.to_dict(),
            "requirement": simulation_requirement[:800],
            "schema": {
                "profession": "short string",
                "bio": "1-2 sentences",
                "persona": "2-3 sentences in third person",
                "goals": ["goal 1", "goal 2"],
                "sensitivities": ["sensitivity 1", "sensitivity 2"],
            },
        }
        try:
            return self.llm_client.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": "Return only valid JSON. Keep descriptions grounded and concise.",
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                temperature=0.3,
                max_tokens=900,
            )
        except Exception as exc:
            logger.debug(f"Profile LLM generation failed for {prepared.entity.name}: {exc}")
            return None

    def _default_goals(self, node_family: str, region_name: str) -> List[str]:
        defaults = {
            "EnvironmentalCarrier": [f"propagate changes across {region_name}", "reflect current transport conditions"],
            "EcologicalReceptor": [f"maintain habitat quality in {region_name}", "avoid prolonged exposure"],
            "GovernmentActor": [f"stabilize {region_name}", "coordinate response legitimacy"],
            "OrganizationActor": [f"protect operations in {region_name}", "manage reputational risk"],
            "Infrastructure": [f"keep services operating in {region_name}", "reduce disruption spillover"],
        }
        return defaults.get(node_family, [f"protect interests in {region_name}", "adapt to changing environmental conditions"])

    def _default_sensitivities(self, node_family: str, region_name: str) -> List[str]:
        defaults = {
            "EnvironmentalCarrier": ["upstream/downstream pressure", "weather and current shifts"],
            "EcologicalReceptor": ["toxicity persistence", "habitat fragmentation"],
            "GovernmentActor": ["trust collapse", "resource constraints"],
            "OrganizationActor": ["consumer sentiment", "supply chain interruption"],
            "Infrastructure": ["service overload", "contamination shutdowns"],
        }
        return defaults.get(node_family, [f"rapid sentiment change in {region_name}", "policy uncertainty"])

    def _username_from_name(self, name: str, index: int) -> str:
        normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
        normalized = "_".join(part for part in normalized.split("_") if part) or "agent"
        return f"{normalized[:20]}_{index}"
