<template>
  <div class="envfish-step envfish-step2">
    <div class="hero">
      <div class="hero-copy">
        <div class="eyebrow">ENVFISH / STEP 2</div>
        <h2>生态社会场景设计</h2>
        <p>
          从稳态报告或危机报告中提取区域、角色和关系，生成可注入变量的半定量推演场景。
        </p>
      </div>

      <div class="hero-metrics">
        <div class="metric-card">
          <span class="metric-label">Simulation</span>
          <span class="metric-value mono">{{ simulationId || 'pending' }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Regions</span>
          <span class="metric-value">{{ graphStats.regions }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Actors</span>
          <span class="metric-value">{{ graphStats.actors }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Relations</span>
          <span class="metric-value">{{ graphStats.edges }}</span>
        </div>
      </div>
    </div>

    <div class="workspace">
      <section class="panel scenic">
        <div class="panel-title-row">
          <h3>场景模式</h3>
          <span class="hint">基线 / 灾难态</span>
        </div>
        <div class="mode-grid">
          <button
            v-for="mode in scenarioModes"
            :key="mode.value"
            class="mode-card"
            :class="{ active: scenarioMode === mode.value }"
            @click="scenarioMode = mode.value"
          >
            <span class="mode-tag">{{ mode.tag }}</span>
            <span class="mode-name">{{ mode.label }}</span>
            <p>{{ mode.description }}</p>
          </button>
        </div>

        <div class="slider-shell">
          <div class="panel-title-row">
            <h3>推演轮数上限</h3>
            <span class="hint mono">{{ maxRounds }}</span>
          </div>
          <input
            v-model.number="maxRounds"
            type="range"
            min="12"
            max="72"
            step="4"
            class="range"
          />
          <div class="range-labels">
            <span>12</span>
            <span>36</span>
            <span>72</span>
          </div>
        </div>

        <div class="panel-title-row">
          <h3>扩散模板</h3>
          <span class="hint">模板只定义传播语法，不接真实物理场</span>
        </div>
        <div class="template-grid">
          <button
            v-for="template in diffusionTemplates"
            :key="template.value"
            class="template-card"
            :class="{ active: diffusionTemplate === template.value }"
            @click="diffusionTemplate = template.value"
          >
            <div class="template-head">
              <span class="template-name">{{ template.label }}</span>
              <span class="template-badge">{{ template.scope }}</span>
            </div>
            <p>{{ template.description }}</p>
          </button>
        </div>
      </section>

      <section class="panel variables">
        <div class="panel-title-row">
          <h3>中途变量</h3>
          <button class="ghost-btn" @click="addVariable('disaster')">+ 灾难变量</button>
        </div>

        <div class="variable-list">
          <article v-for="(variable, index) in injectedVariables" :key="variable.id" class="variable-card">
            <div class="variable-header">
              <div>
                <span class="variable-index">V{{ index + 1 }}</span>
                <strong>{{ variable.type === 'policy' ? '政策/干预变量' : '灾难变量' }}</strong>
              </div>
              <button class="remove-btn" @click="removeVariable(variable.id)">删除</button>
            </div>

            <div class="field-row">
              <label>
                类型
                <select v-model="variable.type">
                  <option value="disaster">disaster</option>
                  <option value="policy">policy</option>
                </select>
              </label>
              <label>
                变量名
                <input v-model="variable.name" type="text" placeholder="核废水排放 / 强制撤离" />
              </label>
            </div>

            <label>
              描述
              <textarea v-model="variable.description" rows="3" placeholder="一句话描述变量如何改变生态或社会状态"></textarea>
            </label>

            <div class="field-row">
              <label>
                目标区域
                <input v-model="variable.targetRegions" type="text" placeholder="滨海区,渔港,近岸海域" />
              </label>
              <label>
                目标节点
                <input v-model="variable.targetNodes" type="text" placeholder="渔民,海流,环保局" />
              </label>
            </div>

            <div class="field-row">
              <label>
                起始轮次
                <input v-model.number="variable.startRound" type="number" min="0" />
              </label>
              <label>
                持续轮次
                <input v-model.number="variable.durationRounds" type="number" min="1" />
              </label>
              <label>
                强度
                <input v-model.number="variable.intensity" type="range" min="0" max="100" />
              </label>
            </div>

            <div v-if="variable.type === 'policy'" class="policy-row">
              <label>
                干预模式
                <select v-model="variable.policyMode">
                  <option v-for="mode in policyModes" :key="mode.value" :value="mode.value">
                    {{ mode.label }}
                  </option>
                </select>
              </label>
            </div>
          </article>
        </div>
      </section>

      <section class="panel summary">
        <div class="panel-title-row">
          <h3>图谱概览</h3>
          <span class="hint">来自知识图谱的区域/角色骨架</span>
        </div>

        <div class="summary-grid">
          <div class="summary-card">
            <span>Region nodes</span>
            <strong>{{ graphStats.regions }}</strong>
          </div>
          <div class="summary-card">
            <span>Human actors</span>
            <strong>{{ graphStats.humanActors }}</strong>
          </div>
          <div class="summary-card">
            <span>Eco receptors</span>
            <strong>{{ graphStats.ecologyActors }}</strong>
          </div>
          <div class="summary-card">
            <span>Gov / Infra</span>
            <strong>{{ graphStats.governanceActors + graphStats.infrastructureActors }}</strong>
          </div>
        </div>

        <div class="catalog">
          <div class="catalog-title">候选区域</div>
          <div class="chip-wrap">
            <span v-for="region in regionCandidates.slice(0, 10)" :key="region" class="chip">{{ region }}</span>
            <span v-if="regionCandidates.length === 0" class="empty-chip">系统将自动从 Seed 中解析区域骨架</span>
          </div>
        </div>

        <div class="catalog">
          <div class="catalog-title">数据地基</div>
          <div class="grounding-box">
            <p>{{ groundingSummary }}</p>
            <div class="grounding-list">
              <span v-for="item in groundingHints" :key="item" class="grounding-item">{{ item }}</span>
            </div>
          </div>
        </div>

        <div class="payload-box">
          <div class="catalog-title">待提交配置</div>
          <pre>{{ payloadPreview }}</pre>
        </div>
      </section>
    </div>

    <section class="risk-preview-shell">
      <div class="panel-title-row">
        <h3>风险对象预览</h3>
        <span class="hint">{{ riskObjects.length }} objects / step 2 preview</span>
      </div>

      <div v-if="riskObjects.length > 0" class="risk-preview-grid">
        <div class="risk-preview-list">
          <button
            v-for="item in riskObjects"
            :key="item.risk_object_id"
            type="button"
            class="risk-preview-card"
            :class="{ active: item.risk_object_id === selectedRiskObjectId }"
            @click="selectedRiskObjectId = item.risk_object_id"
          >
            <div class="risk-preview-head">
              <span class="risk-mode-tag">{{ item.mode || 'watch' }}</span>
              <span v-if="item.risk_object_id === primaryRiskObjectId" class="risk-primary-tag">PRIMARY</span>
            </div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.why_now || item.summary || '等待风险对象摘要。' }}</p>
            <div class="risk-meta">
              <span>Sev {{ normalizeScore(item.severity_score) }}</span>
              <span>Act {{ normalizeScore(item.actionability_score) }}</span>
            </div>
          </button>
        </div>

        <div v-if="selectedRiskObject" class="risk-preview-detail">
          <div class="risk-detail-top">
            <div>
              <div class="eyebrow risk-eyebrow">
                {{ selectedRiskObject.mode === 'incident' ? 'INCIDENT PREVIEW' : 'WATCH PREVIEW' }}
              </div>
              <h3>{{ selectedRiskObject.title }}</h3>
              <p>{{ selectedRiskObject.summary || selectedRiskObject.why_now || '等待风险对象摘要。' }}</p>
            </div>

            <div class="risk-score-strip">
              <div class="summary-card compact">
                <span>Severity</span>
                <strong>{{ normalizeScore(selectedRiskObject.severity_score) }}</strong>
              </div>
              <div class="summary-card compact">
                <span>Confidence</span>
                <strong>{{ formatPercent(selectedRiskObject.confidence_score) }}</strong>
              </div>
            </div>
          </div>

          <div class="risk-note-box">
            <span>Why Now</span>
            <strong>{{ selectedRiskObject.why_now || '场景配置完成后会显示 why now。' }}</strong>
          </div>

          <div class="risk-step-list">
            <span v-for="step in selectedRiskObject.chain_steps || []" :key="step" class="chip">{{ step }}</span>
          </div>

          <div class="risk-node-grid">
            <section class="risk-mini-panel">
              <div class="catalog-title">相关实体节点</div>
              <div v-if="riskObjectEntityNodes.length > 0" class="node-list">
                <article v-for="node in riskObjectEntityNodes" :key="node.id" class="node-card">
                  <div class="node-card-head">
                    <strong>{{ node.name }}</strong>
                    <span class="node-state" :class="{ matched: node.matched }">{{ node.matched ? 'graph node' : 'risk ref' }}</span>
                  </div>
                  <div class="tag-wrap">
                    <span v-for="label in node.labels" :key="label" class="mini-tag">{{ label }}</span>
                  </div>
                </article>
              </div>
              <div v-else class="empty-state">生成配置后将展示相关实体节点。</div>
            </section>

            <section class="risk-mini-panel">
              <div class="catalog-title">相关区域</div>
              <div v-if="riskObjectRegionNodes.length > 0" class="node-list">
                <article v-for="region in riskObjectRegionNodes" :key="region.id" class="node-card">
                  <div class="node-card-head">
                    <strong>{{ region.name }}</strong>
                    <span class="node-state" :class="{ matched: region.matched }">{{ region.matched ? 'graph node' : 'scope' }}</span>
                  </div>
                  <div class="tag-wrap">
                    <span v-for="label in region.labels" :key="label" class="mini-tag">{{ label }}</span>
                  </div>
                </article>
              </div>
              <div v-else class="empty-state">当前没有可映射的区域节点。</div>
            </section>
          </div>

          <div class="risk-node-grid secondary">
            <section class="risk-mini-panel">
              <div class="catalog-title">受影响群簇</div>
              <div v-if="riskObjectClusters.length > 0" class="cluster-list">
                <article v-for="cluster in riskObjectClusters" :key="cluster.cluster_id" class="cluster-mini-card">
                  <div class="node-card-head">
                    <strong>{{ cluster.name }}</strong>
                    <span class="mini-tag accent">Mismatch {{ normalizeScore(cluster.mismatch_risk) }}</span>
                  </div>
                  <p>{{ formatInlineList(cluster.dependency_profile, '暂无依赖结构') }}</p>
                </article>
              </div>
              <div v-else class="empty-state">当前还没有受影响群簇预览。</div>
            </section>

            <section class="risk-mini-panel">
              <div class="catalog-title">转折点</div>
              <ul v-if="(selectedRiskObject.turning_points || []).length > 0" class="bullet-list">
                <li v-for="point in selectedRiskObject.turning_points" :key="point">{{ point }}</li>
              </ul>
              <div v-else class="empty-state">当前对象还没有显式转折点。</div>
            </section>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        生成场景配置后，这里会出现风险对象预览，并可联动左侧图谱高亮相关节点。
      </div>
    </section>

    <section class="progress-shell">
      <div class="progress-head">
        <div>
          <div class="panel-title-row">
            <h3>准备进度</h3>
            <span class="hint">{{ prepareStageLabel }}</span>
          </div>
          <p class="progress-note">{{ prepareMessage || '等待用户触发场景配置生成' }}</p>
        </div>
        <div class="progress-score mono">{{ prepareProgress }}%</div>
      </div>

      <div class="progress-bar">
        <div class="progress-bar-fill" :style="{ width: `${prepareProgress}%` }"></div>
      </div>

      <div class="action-row">
        <button class="secondary-btn" @click="$emit('go-back')">返回图谱构建</button>
        <button class="primary-btn" :disabled="isPreparing" @click="handlePrepare">
          {{ isPreparing ? '生成中...' : (phase === 'ready' ? '重算场景配置' : '生成场景配置') }}
        </button>
        <button class="secondary-btn" :disabled="!isReady" @click="handleNextStep">
          进入推演
        </button>
      </div>
    </section>

    <section class="log-shell">
      <div class="panel-title-row">
        <h3>系统日志</h3>
        <span class="hint mono">{{ simulationId || 'NO_SIMULATION' }}</span>
      </div>
      <div class="logs">
        <div v-for="(log, index) in systemLogs" :key="index" class="log-line">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { getPrepareStatus, getSimulationConfig, getSimulationConfigRealtime, prepareSimulation, getSimulation } from '../api/simulation'

const props = defineProps({
  simulationId: String,
  projectData: Object,
  graphData: Object,
  systemLogs: Array,
  initialScenarioMode: String,
  initialDiffusionTemplate: String
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status', 'risk-object-focus'])

const scenarioModes = [
  {
    value: 'baseline_mode',
    tag: 'BASELINE',
    label: '常态 + 灾难变量注入',
    description: '从平稳生态和社会网络出发，观察变量首次跨界触发后的破窗效应。'
  },
  {
    value: 'crisis_mode',
    tag: 'CRISIS',
    label: '灾难态 + 干预变量注入',
    description: '从破碎结构出发，评估政策执行摩擦、信任崩塌与次生灾害。'
  }
]

const diffusionTemplates = [
  {
    value: 'air',
    label: 'AIR',
    scope: '气团',
    description: '邻接扩散、滞后传播、衰减延展，适合大气污染与跨区漂移。'
  },
  {
    value: 'inland_water',
    label: 'WATER',
    scope: '河网',
    description: '沿上游/下游、支流与库区传播，适合内陆水体和流域污染。'
  },
  {
    value: 'marine',
    label: 'MARINE',
    scope: '海洋',
    description: '沿岸流和海流驱动，扩散更慢但影响范围更宽。'
  }
]

const policyModes = [
  { value: 'restrict', label: 'restrict' },
  { value: 'relocate', label: 'relocate' },
  { value: 'subsidize', label: 'subsidize' },
  { value: 'monitor', label: 'monitor' },
  { value: 'disclose', label: 'disclose' },
  { value: 'repair', label: 'repair' },
  { value: 'ban', label: 'ban' },
  { value: 'reopen', label: 'reopen' }
]

const scenarioMode = ref(props.initialScenarioMode || 'baseline_mode')
const diffusionTemplate = ref(props.initialDiffusionTemplate || 'marine')
const maxRounds = ref(36)
const injectedVariables = ref([createVariable('disaster')])
const phase = ref('idle')
const prepareProgress = ref(0)
const prepareMessage = ref('')
const prepareStage = ref('')
const prepareTaskId = ref('')
const isPreparing = ref(false)
const configSnapshot = ref(null)
const configRealtime = ref(null)
const simulationSnapshot = ref(null)

let progressTimer = null
let configTimer = null

const graphNodes = computed(() => collectGraphNodes(props.graphData))
const graphEdges = computed(() => collectGraphEdges(props.graphData))

const graphStats = computed(() => {
  const nodes = graphNodes.value
  const edges = graphEdges.value
  const families = categorizeNodes(nodes)
  return {
    regions: families.regions.length,
    humanActors: families.human.length,
    ecologyActors: families.ecology.length,
    governanceActors: families.governance.length,
    infrastructureActors: families.infrastructure.length,
    actors: families.human.length + families.ecology.length + families.governance.length + families.infrastructure.length,
    edges: edges.length
  }
})

const regionCandidates = computed(() => {
  const families = categorizeNodes(graphNodes.value)
  return families.regions.map(node => node.label).filter(Boolean)
})

const groundingSummary = computed(() => {
  const source = configRealtime.value?.data_grounding_summary || configSnapshot.value?.data_grounding_summary
  if (typeof source === 'string' && source.trim()) return source
  if (Array.isArray(source) && source.length > 0) return source.join(' · ')
  return '无外部数据时使用报告先验与图谱结构初始化。'
})

const groundingHints = computed(() => {
  const hints = []
  if (configRealtime.value?.grounding_sources) {
    const value = configRealtime.value.grounding_sources
    if (Array.isArray(value)) hints.push(...value.map(String))
  }
  if (hints.length === 0) {
    hints.push('EPA / USGS / Copernicus / NOAA 均可作为可选地基')
  }
  return hints
})

const selectedRiskObjectId = ref('')

const riskObjects = computed(() => {
  const candidates = [
    configRealtime.value?.risk_objects,
    configSnapshot.value?.risk_objects,
    simulationSnapshot.value?.risk_objects
  ]

  for (const items of candidates) {
    if (Array.isArray(items) && items.length > 0) {
      return items
    }
  }

  return []
})

const primaryRiskObjectId = computed(() => {
  return (
    configRealtime.value?.primary_risk_object_id ||
    configSnapshot.value?.primary_risk_object_id ||
    simulationSnapshot.value?.primary_risk_object?.risk_object_id ||
    simulationSnapshot.value?.risk_objects_summary?.primary_risk_object_id ||
    riskObjects.value[0]?.risk_object_id ||
    ''
  )
})

const selectedRiskObject = computed(() => {
  if (riskObjects.value.length === 0) return null
  return riskObjects.value.find(item => item.risk_object_id === selectedRiskObjectId.value) || riskObjects.value[0]
})

const graphNodeByUuid = computed(() => {
  const map = new Map()
  graphNodes.value.forEach(node => {
    if (node?.uuid) {
      map.set(node.uuid, node)
    }
  })
  return map
})

const graphNodesByName = computed(() => {
  const map = new Map()
  graphNodes.value.forEach(node => {
    const name = String(node?.name || node?.label || '').trim().toLowerCase()
    if (!name) return
    if (!map.has(name)) {
      map.set(name, [])
    }
    map.get(name).push(node)
  })
  return map
})

const riskObjectEntityNodes = computed(() => {
  if (!selectedRiskObject.value) return []

  const evidenceByUuid = new Map()
  ;(selectedRiskObject.value.evidence || []).forEach(item => {
    ;(item.entity_refs || []).forEach(uuid => {
      if (uuid && !evidenceByUuid.has(uuid)) {
        evidenceByUuid.set(uuid, item)
      }
    })
  })

  return uniqueList(selectedRiskObject.value.source_entity_uuids || []).map((uuid, index) => {
    const node = graphNodeByUuid.value.get(uuid)
    const evidence = evidenceByUuid.get(uuid)
    return {
      id: node?.uuid || `risk-entity-${index}`,
      uuid,
      name: node?.name || evidence?.title || `entity_${index + 1}`,
      labels: normalizeLabels(node?.labels),
      matched: Boolean(node)
    }
  })
})

const riskObjectRegionNodes = computed(() => {
  if (!selectedRiskObject.value) return []

  return uniqueList([
    ...(selectedRiskObject.value.primary_regions || []),
    ...(selectedRiskObject.value.region_scope || [])
  ]).map((name, index) => {
    const matched = graphNodesByName.value.get(String(name).toLowerCase()) || []
    const node = matched[0]
    return {
      id: node?.uuid || `risk-region-${index}`,
      name,
      labels: normalizeLabels(node?.labels),
      matched: Boolean(node)
    }
  })
})

const riskObjectClusters = computed(() => {
  if (!selectedRiskObject.value || !Array.isArray(selectedRiskObject.value.affected_clusters)) return []
  return selectedRiskObject.value.affected_clusters
})

const riskObjectHighlightPayload = computed(() => {
  if (!selectedRiskObject.value) {
    return {
      label: '',
      riskObjectId: '',
      nodeIds: [],
      nodeNames: []
    }
  }

  return {
    label: selectedRiskObject.value.title || '',
    riskObjectId: selectedRiskObject.value.risk_object_id || '',
    nodeIds: uniqueList(riskObjectEntityNodes.value.map(item => item.uuid)),
    nodeNames: uniqueList([
      ...riskObjectEntityNodes.value.map(item => item.name),
      ...riskObjectRegionNodes.value.map(item => item.name)
    ])
  }
})

const isReady = computed(() => phase.value === 'ready' || Boolean(configSnapshot.value))

const prepareStageLabel = computed(() => {
  if (phase.value === 'ready') return 'ready'
  if (phase.value === 'preparing') return prepareStage.value || 'preparing'
  if (phase.value === 'error') return 'failed'
  return 'idle'
})

const payloadPreview = computed(() => {
  return JSON.stringify({
    simulation_id: props.simulationId,
    engine_mode: 'envfish',
    scenario_mode: scenarioMode.value,
    diffusion_template: diffusionTemplate.value,
    max_rounds: maxRounds.value,
    spatial_grain: 'region',
    injected_variables: injectedVariables.value.map(serializeVariable)
  }, null, 2)
})

const addLog = (msg) => {
  emit('add-log', msg)
}

function createVariable(type = 'disaster') {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    type,
    name: '',
    description: '',
    targetRegions: '',
    targetNodes: '',
    startRound: 0,
    durationRounds: 4,
    intensity: 70,
    policyMode: 'restrict'
  }
}

function serializeVariable(variable) {
  return {
    type: variable.type,
    name: variable.name || (variable.type === 'policy' ? 'policy_injection' : 'disaster_injection'),
    description: variable.description || '',
    target_regions: splitList(variable.targetRegions),
    target_nodes: splitList(variable.targetNodes),
    start_round: Number(variable.startRound) || 0,
    duration_rounds: Math.max(1, Number(variable.durationRounds) || 1),
    intensity: clamp(Number(variable.intensity) || 0, 0, 100),
    policy_mode: variable.type === 'policy' ? variable.policyMode : undefined
  }
}

function splitList(value) {
  if (!value) return []
  return String(value)
    .split(/[,\n;]/)
    .map(item => item.trim())
    .filter(Boolean)
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function normalizeScore(value) {
  const number = Number(value)
  if (Number.isNaN(number)) return 0
  return Math.max(0, Math.min(100, Math.round(number)))
}

function formatPercent(value) {
  const number = Number(value)
  if (Number.isNaN(number)) return 'n/a'
  if (number <= 1) return `${Math.round(number * 100)}%`
  return `${Math.round(Math.max(0, Math.min(100, number)))}%`
}

function formatInlineList(items, fallback = '—') {
  const values = uniqueList(Array.isArray(items) ? items : [])
  return values.length > 0 ? values.join(' · ') : fallback
}

function uniqueList(items) {
  return Array.from(
    new Set(
      (items || [])
        .map(item => String(item || '').trim())
        .filter(Boolean)
    )
  )
}

function normalizeLabels(labels) {
  return uniqueList(Array.isArray(labels) ? labels : []).slice(0, 3)
}

function collectGraphNodes(data) {
  if (!data) return []
  if (Array.isArray(data.nodes)) return data.nodes
  if (Array.isArray(data.graph?.nodes)) return data.graph.nodes
  if (Array.isArray(data.data?.nodes)) return data.data.nodes
  return []
}

function collectGraphEdges(data) {
  if (!data) return []
  if (Array.isArray(data.edges)) return data.edges
  if (Array.isArray(data.graph?.edges)) return data.graph.edges
  if (Array.isArray(data.data?.edges)) return data.data.edges
  return []
}

function getNodeLabel(node, fallback = '') {
  return node?.label || node?.name || node?.title || node?.entity_name || node?.username || fallback
}

function getNodeType(node) {
  return String(node?.type || node?.entity_type || node?.category || node?.node_type || '').toLowerCase()
}

function categorizeNodes(nodes) {
  const grouped = {
    regions: [],
    human: [],
    ecology: [],
    governance: [],
    infrastructure: []
  }

  nodes.forEach((node, index) => {
    const type = getNodeType(node)
    const label = getNodeLabel(node, `node_${index}`)
    const normalized = { ...node, label }

    if (type.includes('region') || type.includes('city') || type.includes('district') || type.includes('zone') || type.includes('bay') || type.includes('coast') || type.includes('basin')) {
      grouped.regions.push(normalized)
      return
    }

    if (type.includes('resident') || type.includes('fisher') || type.includes('farmer') || type.includes('consumer') || type.includes('tourist') || type.includes('human') || type.includes('actor')) {
      grouped.human.push(normalized)
      return
    }

    if (type.includes('fish') || type.includes('bird') || type.includes('crop') || type.includes('species') || type.includes('eco') || type.includes('receptor')) {
      grouped.ecology.push(normalized)
      return
    }

    if (type.includes('gov') || type.includes('agency') || type.includes('office') || type.includes('authority') || type.includes('ngo') || type.includes('media') || type.includes('school') || type.includes('hospital')) {
      grouped.governance.push(normalized)
      return
    }

    if (type.includes('port') || type.includes('market') || type.includes('plant') || type.includes('transport') || type.includes('infra')) {
      grouped.infrastructure.push(normalized)
    }
  })

  return grouped
}

function addVariable(type = 'disaster') {
  injectedVariables.value.push(createVariable(type))
}

function removeVariable(id) {
  if (injectedVariables.value.length === 1) return
  injectedVariables.value = injectedVariables.value.filter(variable => variable.id !== id)
}

async function bootstrapSimulation() {
  if (!props.simulationId) return

  try {
    const [simulationRes, configRes, realtimeRes] = await Promise.allSettled([
      getSimulation(props.simulationId),
      getSimulationConfig(props.simulationId),
      getSimulationConfigRealtime(props.simulationId)
    ])

    if (simulationRes.status === 'fulfilled' && simulationRes.value?.success) {
      simulationSnapshot.value = simulationRes.value.data || null
    }

    if (configRes.status === 'fulfilled' && configRes.value?.success && configRes.value.data) {
      configSnapshot.value = configRes.value.data
      phase.value = 'ready'
      prepareProgress.value = 100
      prepareMessage.value = '已存在可复用的场景配置'
    }

    if (realtimeRes.status === 'fulfilled' && realtimeRes.value?.success && realtimeRes.value.data) {
      configRealtime.value = realtimeRes.value.data
      if (realtimeRes.value.data.generation_stage) {
        prepareStage.value = realtimeRes.value.data.generation_stage
      }
      if (realtimeRes.value.data.progress !== undefined) {
        prepareProgress.value = realtimeRes.value.data.progress
      }
    }
  } catch (err) {
    addLog(`加载场景上下文失败: ${err.message}`)
  }
}

function startTimers(taskId = '') {
  stopTimers()
  prepareTaskId.value = taskId
  progressTimer = setInterval(pollPrepareStatus, 2000)
  configTimer = setInterval(fetchConfigRealtime, 2500)
}

function stopTimers() {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
  if (configTimer) {
    clearInterval(configTimer)
    configTimer = null
  }
}

async function handlePrepare() {
  if (!props.simulationId || isPreparing.value) return

  isPreparing.value = true
  phase.value = 'preparing'
  prepareProgress.value = 0
  prepareMessage.value = '正在提交 EnvFish 场景配置'
  emit('update-status', 'processing')
  addLog(`提交 EnvFish 场景配置: ${scenarioMode.value} / ${diffusionTemplate.value}`)

  try {
    const res = await prepareSimulation({
      simulation_id: props.simulationId,
      engine_mode: 'envfish',
      scenario_mode: scenarioMode.value,
      diffusion_template: diffusionTemplate.value,
      max_rounds: maxRounds.value,
      region_granularity: 'region',
      injected_variables: injectedVariables.value.map(serializeVariable)
    })

    if (res.success && res.data) {
      if (res.data.already_prepared) {
        phase.value = 'ready'
        prepareProgress.value = 100
        prepareMessage.value = '检测到已完成的场景配置'
        addLog('✓ 场景配置已存在，直接复用')
        await bootstrapSimulation()
      } else {
        prepareTaskId.value = res.data.task_id || ''
        addLog(`✓ 准备任务已启动${prepareTaskId.value ? `: ${prepareTaskId.value}` : ''}`)
        if (res.data.expected_entities_count) {
          addLog(`预期角色/节点数: ${res.data.expected_entities_count}`)
        }
        startTimers(prepareTaskId.value)
        await fetchConfigRealtime()
      }
    } else {
      phase.value = 'error'
      emit('update-status', 'error')
      addLog(`✗ 场景配置提交失败: ${res.error || '未知错误'}`)
    }
  } catch (err) {
    phase.value = 'error'
    emit('update-status', 'error')
    addLog(`✗ 场景配置异常: ${err.message}`)
  } finally {
    isPreparing.value = false
  }
}

async function pollPrepareStatus() {
  if (!props.simulationId) return

  try {
    const res = await getPrepareStatus({
      simulation_id: props.simulationId,
      task_id: prepareTaskId.value || undefined
    })

    if (res.success && res.data) {
      const data = res.data
      if (data.progress !== undefined) prepareProgress.value = clamp(Number(data.progress) || 0, 0, 100)
      if (data.message) prepareMessage.value = data.message
      if (data.progress_detail?.current_stage_name) {
        prepareStage.value = data.progress_detail.current_stage_name
      } else if (data.current_stage_name) {
        prepareStage.value = data.current_stage_name
      }

      if (data.status === 'completed' || data.already_prepared) {
        phase.value = 'ready'
        prepareProgress.value = 100
        prepareMessage.value = '场景配置已完成'
        emit('update-status', 'completed')
        addLog('✓ EnvFish 场景配置完成')
        stopTimers()
        await fetchConfigRealtime()
      } else if (data.status === 'failed') {
        phase.value = 'error'
        emit('update-status', 'error')
        addLog(`✗ 场景配置失败: ${data.error || '未知错误'}`)
        stopTimers()
      }
    }
  } catch (err) {
    console.warn('poll prepare failed', err)
  }
}

async function fetchConfigRealtime() {
  if (!props.simulationId) return

  try {
    const res = await getSimulationConfigRealtime(props.simulationId)
    if (res.success && res.data) {
      configRealtime.value = res.data
      if (res.data.generation_stage) prepareStage.value = res.data.generation_stage
      if (res.data.progress !== undefined) prepareProgress.value = clamp(Number(res.data.progress) || 0, 0, 100)
      if (res.data.message) prepareMessage.value = res.data.message
      if (res.data.scenario_mode) scenarioMode.value = res.data.scenario_mode
      if (res.data.diffusion_template) diffusionTemplate.value = res.data.diffusion_template
    }
  } catch (err) {
    console.warn('fetch config realtime failed', err)
  }
}

function handleNextStep() {
  emit('next-step', {
    scenarioMode: scenarioMode.value,
    diffusionTemplate: diffusionTemplate.value,
    maxRounds: maxRounds.value,
    variableCount: injectedVariables.value.length,
    injectedVariables: injectedVariables.value.map(serializeVariable)
  })
}

watch(
  () => props.initialScenarioMode,
  (value) => {
    if (value) scenarioMode.value = value
  }
)

watch(
  () => props.initialDiffusionTemplate,
  (value) => {
    if (value) diffusionTemplate.value = value
  }
)

watch(
  [riskObjects, primaryRiskObjectId],
  ([items, primaryId]) => {
    if (!items.length) {
      selectedRiskObjectId.value = ''
      return
    }

    const hasSelected = items.some(item => item.risk_object_id === selectedRiskObjectId.value)
    if (hasSelected) return

    const fallback = items.some(item => item.risk_object_id === primaryId)
      ? primaryId
      : items[0].risk_object_id

    selectedRiskObjectId.value = fallback
  },
  { immediate: true }
)

watch(
  riskObjectHighlightPayload,
  (payload) => {
    emit('risk-object-focus', payload)
  },
  { immediate: true, deep: true }
)

onMounted(async () => {
  addLog('EnvFish Step2 初始化')
  await bootstrapSimulation()
  if (props.simulationId) {
    emit('update-status', phase.value === 'ready' ? 'completed' : 'processing')
  }
})

onUnmounted(() => {
  stopTimers()
})
</script>

<style scoped>
.envfish-step {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(88, 159, 255, 0.18), transparent 32%),
    radial-gradient(circle at top right, rgba(28, 196, 135, 0.16), transparent 30%),
    linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  color: #132033;
}

.hero,
.panel,
.progress-shell,
.log-shell {
  border: 1px solid rgba(20, 33, 61, 0.08);
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(10px);
  box-shadow: 0 12px 32px rgba(17, 31, 59, 0.06);
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  border-radius: 24px;
  padding: 20px 22px;
}

.eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.2em;
  color: #5d78a7;
}

.hero h2 {
  margin: 10px 0 8px;
  font-size: 28px;
  line-height: 1.1;
}

.hero p {
  margin: 0;
  max-width: 680px;
  color: #5d687f;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(120px, 1fr));
  gap: 10px;
  min-width: 280px;
}

.metric-card,
.summary-card {
  border-radius: 18px;
  padding: 12px 14px;
  background: linear-gradient(180deg, rgba(245, 248, 255, 0.98), rgba(235, 242, 255, 0.86));
  border: 1px solid rgba(97, 125, 175, 0.14);
}

.metric-label,
.summary-card span,
.hint,
.catalog-title {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7382a3;
}

.metric-value {
  display: block;
  margin-top: 8px;
  font-size: 17px;
  font-weight: 800;
  color: #183058;
}

.workspace {
  display: grid;
  grid-template-columns: 1.05fr 1fr 0.8fr;
  gap: 16px;
  min-height: 0;
  flex: 1;
}

.panel {
  border-radius: 24px;
  padding: 18px;
  overflow: auto;
}

.panel-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-title-row h3 {
  margin: 0;
  font-size: 16px;
}

.mode-grid,
.template-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.mode-card,
.template-card {
  text-align: left;
  border-radius: 18px;
  border: 1px solid rgba(20, 33, 61, 0.1);
  background: linear-gradient(180deg, #fff, #f3f7ff);
  padding: 14px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.mode-card:hover,
.template-card:hover,
.ghost-btn:hover,
.secondary-btn:hover,
.primary-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(31, 57, 98, 0.1);
}

.mode-card.active,
.template-card.active {
  border-color: rgba(47, 110, 255, 0.55);
  background: linear-gradient(180deg, rgba(240, 245, 255, 1), rgba(227, 237, 255, 0.95));
}

.mode-tag,
.template-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 10px;
  font-weight: 700;
  background: rgba(48, 89, 178, 0.1);
  color: #3357a8;
}

.mode-name,
.template-name {
  display: block;
  margin-top: 8px;
  font-weight: 800;
}

.mode-card p,
.template-card p,
.progress-note,
.grounding-box p {
  margin: 8px 0 0;
  color: #5e6782;
  line-height: 1.5;
  font-size: 13px;
}

.slider-shell {
  margin: 18px 0 16px;
  padding: 14px;
  border-radius: 18px;
  background: rgba(240, 244, 252, 0.8);
  border: 1px solid rgba(20, 33, 61, 0.08);
}

.range {
  width: 100%;
  margin-top: 10px;
}

.range-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 11px;
  color: #7b86a3;
}

.field-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 10px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #4d5874;
}

input,
select,
textarea {
  width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(20, 33, 61, 0.12);
  background: #fff;
  color: #132033;
  padding: 10px 12px;
  font: inherit;
}

textarea {
  resize: vertical;
}

.variable-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.variable-card {
  border-radius: 18px;
  padding: 14px;
  border: 1px solid rgba(20, 33, 61, 0.08);
  background: linear-gradient(180deg, #ffffff, #f7faff);
}

.variable-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.variable-index {
  display: inline-flex;
  margin-right: 8px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(43, 94, 215, 0.08);
  color: #2e5cc8;
  font-size: 10px;
  font-weight: 800;
}

.remove-btn,
.ghost-btn,
.secondary-btn,
.primary-btn {
  border: none;
  border-radius: 14px;
  padding: 10px 14px;
  font-weight: 700;
  cursor: pointer;
}

.remove-btn,
.ghost-btn,
.secondary-btn {
  background: rgba(24, 48, 88, 0.06);
  color: #213553;
}

.primary-btn {
  background: linear-gradient(135deg, #113a7a, #2f76f1);
  color: #fff;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.summary-card.compact {
  min-width: 132px;
}

.summary-card strong {
  display: block;
  margin-top: 8px;
  font-size: 18px;
  color: #16315a;
}

.catalog {
  margin-top: 14px;
}

.chip-wrap,
.grounding-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip,
.grounding-item,
.empty-chip {
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  background: rgba(28, 68, 154, 0.08);
  color: #21427d;
}

.grounding-box,
.payload-box {
  border-radius: 18px;
  padding: 14px;
  background: rgba(242, 246, 255, 0.72);
  border: 1px solid rgba(20, 33, 61, 0.08);
}

.payload-box pre {
  margin: 10px 0 0;
  max-height: 220px;
  overflow: auto;
  font-size: 11px;
  line-height: 1.5;
  color: #24314a;
  white-space: pre-wrap;
}

.risk-preview-shell {
  border-radius: 24px;
  padding: 16px 18px;
  border: 1px solid rgba(20, 33, 61, 0.08);
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(10px);
  box-shadow: 0 12px 32px rgba(17, 31, 59, 0.06);
}

.risk-preview-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 14px;
}

.risk-preview-list,
.node-list,
.cluster-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.risk-preview-card {
  width: 100%;
  text-align: left;
  border-radius: 18px;
  border: 1px solid rgba(20, 33, 61, 0.1);
  background: linear-gradient(180deg, #fff, #f4f8ff);
  padding: 14px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.risk-preview-card:hover,
.risk-preview-card.active {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(31, 57, 98, 0.08);
  border-color: rgba(47, 110, 255, 0.32);
}

.risk-preview-card.active {
  background: linear-gradient(180deg, rgba(240, 245, 255, 1), rgba(227, 237, 255, 0.95));
}

.risk-preview-head,
.risk-detail-top,
.risk-score-strip,
.node-card-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}

.risk-mode-tag,
.risk-primary-tag,
.node-state,
.mini-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 10px;
  font-weight: 700;
}

.risk-mode-tag {
  background: rgba(48, 89, 178, 0.1);
  color: #3357a8;
}

.risk-primary-tag {
  background: rgba(28, 196, 135, 0.12);
  color: #13805c;
}

.risk-preview-card strong,
.risk-preview-detail h3 {
  display: block;
  margin-top: 8px;
  color: #16315a;
}

.risk-preview-card p,
.risk-preview-detail p,
.cluster-mini-card p {
  margin: 8px 0 0;
  color: #5e6782;
  line-height: 1.5;
  font-size: 13px;
}

.risk-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.risk-meta span,
.mini-tag.accent {
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(24, 48, 88, 0.06);
  color: #213553;
  font-size: 12px;
}

.risk-preview-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-eyebrow {
  color: #4f69a5;
}

.risk-note-box,
.risk-mini-panel {
  border-radius: 18px;
  padding: 14px;
  background: rgba(242, 246, 255, 0.72);
  border: 1px solid rgba(20, 33, 61, 0.08);
}

.risk-note-box span {
  display: block;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7382a3;
}

.risk-note-box strong {
  display: block;
  margin-top: 8px;
  color: #183058;
  line-height: 1.5;
}

.risk-step-list,
.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.risk-step-list {
  margin-top: 2px;
}

.risk-node-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.risk-node-grid.secondary {
  align-items: start;
}

.node-card,
.cluster-mini-card {
  border-radius: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(20, 33, 61, 0.08);
}

.node-state {
  background: rgba(123, 134, 163, 0.12);
  color: #6a7897;
}

.node-state.matched {
  background: rgba(47, 110, 255, 0.12);
  color: #2d5be3;
}

.mini-tag {
  background: rgba(48, 89, 178, 0.08);
  color: #3357a8;
}

.empty-state {
  padding: 14px;
  border-radius: 16px;
  background: rgba(24, 48, 88, 0.04);
  color: #65728f;
  font-size: 13px;
}

.bullet-list {
  margin: 0;
  padding-left: 18px;
  color: #4d5874;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
}

.progress-shell {
  border-radius: 24px;
  padding: 16px 18px;
}

.progress-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.progress-score {
  font-size: 22px;
  font-weight: 900;
  color: #183058;
}

.progress-bar {
  height: 10px;
  border-radius: 999px;
  background: rgba(22, 44, 88, 0.08);
  overflow: hidden;
  margin-top: 12px;
}

.progress-bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2d5be3, #35c98b);
  transition: width 0.25s ease;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.log-shell {
  border-radius: 24px;
  padding: 16px 18px;
  min-height: 0;
}

.logs {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 180px;
  overflow: auto;
  padding-right: 4px;
}

.log-line {
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: 10px;
  font-size: 12px;
  color: #31425f;
}

.log-time {
  color: #7b86a3;
  font-family: monospace;
}

.log-msg {
  line-height: 1.45;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

@media (max-width: 1280px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .risk-preview-grid,
  .risk-node-grid {
    grid-template-columns: 1fr;
  }

  .hero {
    flex-direction: column;
  }
}
</style>
