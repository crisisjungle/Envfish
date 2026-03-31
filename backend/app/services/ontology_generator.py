"""
本体生成服务
接口1：分析文本内容，生成适合社会模拟的实体和关系类型定义
"""

import json
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient


# 本体生成的系统提示词
ONTOLOGY_SYSTEM_PROMPT = """你是一个专业的知识图谱本体设计专家。你的任务是分析给定的文本内容和模拟需求，设计适合 **EnvFish 生态-社会影响推演** 的实体类型和关系类型。

**重要：你必须输出有效的 JSON 格式数据，不要输出任何其他内容。**

## 核心任务背景

我们正在构建一个生态社会影响推演沙盘。系统要同时表示：
- 区域和环境载体（海流、河段、大气、土壤等）
- 生态受体（鱼类、鸟类、作物、栖息地、保护物种等）
- 人类角色（居民、渔民、农民、消费者、游客、工人等）
- 组织与政府角色（企业、媒体、NGO、学校、医院、环保局、应急部门等）
- 基础设施（港口、水厂、交通枢纽、市场、医院等）

实体必须是 **真实存在或可被建模的生态/社会主体**，而不是抽象概念。

## 输出格式

请输出 JSON，包含以下结构：

```json
{
  "entity_types": [
    {
      "name": "实体类型名称（英文，PascalCase）",
      "description": "简短描述（英文，不超过100字符）",
      "attributes": [
        {
          "name": "属性名（英文，snake_case）",
          "type": "text",
          "description": "属性描述"
        }
      ],
      "examples": ["示例1", "示例2"]
    }
  ],
  "edge_types": [
    {
      "name": "关系类型名称（英文，UPPER_SNAKE_CASE）",
      "description": "简短描述（英文，不超过100字符）",
      "source_targets": [
        {"source": "源实体类型", "target": "目标实体类型"}
      ],
      "attributes": []
    }
  ],
  "analysis_summary": "对文本内容的简要分析说明（中文）"
}
```

## 设计指南

### 1. 实体类型设计

**数量要求：必须正好 10 个实体类型。**

你的 10 个实体类型中，必须包含以下 7 个基础家族（放在列表后 7 个也可以）：
- `Region`
- `EnvironmentalCarrier`
- `EcologicalReceptor`
- `HumanActor`
- `OrganizationActor`
- `GovernmentActor`
- `Infrastructure`

其余 3 个类型请根据文本内容补充更具体的领域子类，例如：
- `CoastalCurrent`
- `FishStock`
- `ResidentGroup`
- `PortAuthority`
- `WaterPlant`
- `ProtectedHabitat`

### 2. 关系类型设计

数量：6-10 个。优先覆盖以下关系语义：
- `FLOWS_TO`
- `DEPENDS_ON`
- `EXPOSED_TO`
- `REGULATES`
- `SUPPLIES`
- `TRUSTS`
- `INFORMS`
- `RESTRICTS`
- `RESTORES`
- `CONFLICTS_WITH`

### 3. 属性设计

- 每个实体类型 1-3 个关键属性
- 属性名不能使用 `name`、`uuid`、`group_id`、`created_at`、`summary`
- 推荐使用：`region_name`, `location`, `role`, `carrier_type`, `habitat_type`, `jurisdiction`, `service_scope`

### 4. 严格限制

- 不要输出抽象概念，如“风险”“舆论”“恐慌”
- 不要输出事件、主题、政策口号本身作为实体
- 要让图谱支持“环境 -> 生态 -> 生计 -> 治理 -> 舆情/市场”链条
"""


class OntologyGenerator:
    """
    本体生成器
    分析文本内容，生成实体和关系类型定义
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
    
    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成本体定义
        
        Args:
            document_texts: 文档文本列表
            simulation_requirement: 模拟需求描述
            additional_context: 额外上下文
            
        Returns:
            本体定义（entity_types, edge_types等）
        """
        # 构建用户消息
        user_message = self._build_user_message(
            document_texts, 
            simulation_requirement,
            additional_context
        )
        
        messages = [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        # 调用LLM
        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )
        
        # 验证和后处理
        result = self._validate_and_process(result)
        
        return result
    
    # 传给 LLM 的文本最大长度（5万字）
    MAX_TEXT_LENGTH_FOR_LLM = 50000
    
    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """构建用户消息"""
        
        # 合并文本
        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)
        
        # 如果文本超过5万字，截断（仅影响传给LLM的内容，不影响图谱构建）
        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(原文共{original_length}字，已截取前{self.MAX_TEXT_LENGTH_FOR_LLM}字用于本体分析)..."
        
        message = f"""## 模拟需求

{simulation_requirement}

## 文档内容

{combined_text}
"""
        
        if additional_context:
            message += f"""
## 额外说明

{additional_context}
"""
        
        message += """
请根据以上内容，设计适合生态-社会影响推演的实体类型和关系类型。

**必须遵守的规则**：
1. 必须正好输出10个实体类型
2. 必须包含7个基础家族：Region、EnvironmentalCarrier、EcologicalReceptor、HumanActor、OrganizationActor、GovernmentActor、Infrastructure
3. 其余3个类型根据文本内容设计为更具体的子类
4. 所有实体类型必须是可建模的生态或社会主体，不能是抽象概念
5. 属性名不能使用 name、uuid、group_id 等保留字
"""
        
        return message
    
    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证和后处理结果"""
        
        # 确保必要字段存在
        if "entity_types" not in result:
            result["entity_types"] = []
        if "edge_types" not in result:
            result["edge_types"] = []
        if "analysis_summary" not in result:
            result["analysis_summary"] = ""
        
        # 验证实体类型
        for entity in result["entity_types"]:
            if "attributes" not in entity:
                entity["attributes"] = []
            if "examples" not in entity:
                entity["examples"] = []
            # 确保description不超过100字符
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."
        
        # 验证关系类型
        for edge in result["edge_types"]:
            if "source_targets" not in edge:
                edge["source_targets"] = []
            if "attributes" not in edge:
                edge["attributes"] = []
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."
        
        # Zep API 限制：最多 10 个自定义实体类型，最多 10 个自定义边类型
        MAX_ENTITY_TYPES = 10
        MAX_EDGE_TYPES = 10
        
        required_families = [
            {
                "name": "Region",
                "description": "A geographic or administrative region used for region-level simulation.",
                "attributes": [
                    {"name": "region_name", "type": "text", "description": "Name of the region"},
                    {"name": "location", "type": "text", "description": "Geographic scope or area"}
                ],
                "examples": ["coastal district", "river basin"]
            },
            {
                "name": "EnvironmentalCarrier",
                "description": "A carrier that transports or mediates environmental pressure.",
                "attributes": [
                    {"name": "carrier_type", "type": "text", "description": "Carrier category"},
                    {"name": "location", "type": "text", "description": "Main area of movement"}
                ],
                "examples": ["coastal current", "river segment"]
            },
            {
                "name": "EcologicalReceptor",
                "description": "A species, habitat, or ecosystem unit that receives ecological impact.",
                "attributes": [
                    {"name": "habitat_type", "type": "text", "description": "Habitat or ecological niche"},
                    {"name": "location", "type": "text", "description": "Main ecological area"}
                ],
                "examples": ["fish stock", "wetland habitat"]
            },
            {
                "name": "HumanActor",
                "description": "A human group or social population that reacts to environmental change.",
                "attributes": [
                    {"name": "role", "type": "text", "description": "Social role"},
                    {"name": "location", "type": "text", "description": "Primary area of activity"}
                ],
                "examples": ["resident group", "fisher group"]
            },
            {
                "name": "OrganizationActor",
                "description": "A non-government organization, company, institution, or media body.",
                "attributes": [
                    {"name": "org_type", "type": "text", "description": "Organization category"},
                    {"name": "service_scope", "type": "text", "description": "Area or population served"}
                ],
                "examples": ["enterprise", "hospital"]
            },
            {
                "name": "GovernmentActor",
                "description": "A state or regulatory actor with response or governance authority.",
                "attributes": [
                    {"name": "jurisdiction", "type": "text", "description": "Jurisdiction or mandate"},
                    {"name": "role", "type": "text", "description": "Governance function"}
                ],
                "examples": ["environment agency", "emergency office"]
            },
            {
                "name": "Infrastructure",
                "description": "A critical facility or service node affected by environmental disruption.",
                "attributes": [
                    {"name": "infrastructure_type", "type": "text", "description": "Facility category"},
                    {"name": "location", "type": "text", "description": "Operational area"}
                ],
                "examples": ["port", "water plant"]
            }
        ]

        entity_names = {e["name"] for e in result["entity_types"]}
        missing_families = [family for family in required_families if family["name"] not in entity_names]

        if missing_families:
            current_count = len(result["entity_types"])
            needed_slots = len(missing_families)
            if current_count + needed_slots > MAX_ENTITY_TYPES:
                to_remove = current_count + needed_slots - MAX_ENTITY_TYPES
                result["entity_types"] = result["entity_types"][:-to_remove]
            result["entity_types"].extend(missing_families)
        
        # 最终确保不超过限制（防御性编程）
        if len(result["entity_types"]) > MAX_ENTITY_TYPES:
            result["entity_types"] = result["entity_types"][:MAX_ENTITY_TYPES]

        required_edge_templates = [
            {
                "name": "FLOWS_TO",
                "description": "Environmental flow or transfer between carriers or regions.",
                "source_targets": [
                    {"source": "EnvironmentalCarrier", "target": "Region"},
                    {"source": "Region", "target": "Region"}
                ],
                "attributes": []
            },
            {
                "name": "DEPENDS_ON",
                "description": "A node depends on another node for function or livelihood.",
                "source_targets": [
                    {"source": "HumanActor", "target": "EcologicalReceptor"},
                    {"source": "OrganizationActor", "target": "Infrastructure"}
                ],
                "attributes": []
            },
            {
                "name": "EXPOSED_TO",
                "description": "A node is exposed to an environmental carrier or region condition.",
                "source_targets": [
                    {"source": "EcologicalReceptor", "target": "EnvironmentalCarrier"},
                    {"source": "HumanActor", "target": "Region"}
                ],
                "attributes": []
            },
            {
                "name": "REGULATES",
                "description": "A government actor regulates another actor or infrastructure.",
                "source_targets": [
                    {"source": "GovernmentActor", "target": "OrganizationActor"},
                    {"source": "GovernmentActor", "target": "Infrastructure"}
                ],
                "attributes": []
            },
            {
                "name": "INFORMS",
                "description": "An actor informs or signals another actor or public.",
                "source_targets": [
                    {"source": "OrganizationActor", "target": "HumanActor"},
                    {"source": "GovernmentActor", "target": "HumanActor"}
                ],
                "attributes": []
            }
        ]

        edge_names = {e["name"] for e in result["edge_types"]}
        for edge_template in required_edge_templates:
            if edge_template["name"] not in edge_names and len(result["edge_types"]) < MAX_EDGE_TYPES:
                result["edge_types"].append(edge_template)

        if len(result["edge_types"]) > MAX_EDGE_TYPES:
            result["edge_types"] = result["edge_types"][:MAX_EDGE_TYPES]
        
        return result
    
    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """
        将本体定义转换为Python代码（类似ontology.py）
        
        Args:
            ontology: 本体定义
            
        Returns:
            Python代码字符串
        """
        code_lines = [
            '"""',
            '自定义实体类型定义',
            '由Envfish自动生成，用于社会舆论模拟',
            '"""',
            '',
            'from pydantic import Field',
            'from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel',
            '',
            '',
            '# ============== 实体类型定义 ==============',
            '',
        ]
        
        # 生成实体类型
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            desc = entity.get("description", f"A {name} entity.")
            
            code_lines.append(f'class {name}(EntityModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = entity.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        code_lines.append('# ============== 关系类型定义 ==============')
        code_lines.append('')
        
        # 生成关系类型
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            # 转换为PascalCase类名
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            desc = edge.get("description", f"A {name} relationship.")
            
            code_lines.append(f'class {class_name}(EdgeModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = edge.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        # 生成类型字典
        code_lines.append('# ============== 类型配置 ==============')
        code_lines.append('')
        code_lines.append('ENTITY_TYPES = {')
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            code_lines.append(f'    "{name}": {name},')
        code_lines.append('}')
        code_lines.append('')
        code_lines.append('EDGE_TYPES = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            code_lines.append(f'    "{name}": {class_name},')
        code_lines.append('}')
        code_lines.append('')
        
        # 生成边的source_targets映射
        code_lines.append('EDGE_SOURCE_TARGETS = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            source_targets = edge.get("source_targets", [])
            if source_targets:
                st_list = ', '.join([
                    f'{{"source": "{st.get("source", "Entity")}", "target": "{st.get("target", "Entity")}"}}'
                    for st in source_targets
                ])
                code_lines.append(f'    "{name}": [{st_list}],')
        code_lines.append('}')
        
        return '\n'.join(code_lines)
