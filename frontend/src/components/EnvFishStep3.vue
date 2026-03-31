<template>
  <div class="envfish-step envfish-step3">
    <div class="hero">
      <div class="hero-copy">
        <div class="eyebrow">ENVFISH / STEP 3</div>
        <h2>推演播放与变量注入</h2>
        <p>
          以区域级状态矩阵驱动半定量污染扩散与人-自然反馈，支持时间滑块、区域评分和中途变量注入。
        </p>
      </div>

      <div class="hero-controls">
        <button class="ghost-btn" @click="handleGoBack">返回场景设计</button>
        <button class="ghost-btn" :disabled="isStopping" @click="handleStop">
          {{ isStopping ? '停止中...' : '停止推演' }}
        </button>
        <button class="primary-btn" :disabled="isGeneratingReport" @click="handleNextStep">
          {{ isGeneratingReport ? '报告生成中...' : '生成报告' }}
        </button>
      </div>
    </div>

    <div class="status-strip">
      <div class="status-card accent">
        <span>Round</span>
        <strong class="mono">{{ currentRoundNumber }}</strong>
      </div>
      <div class="status-card">
        <span>Template</span>
        <strong>{{ templateLabel }}</strong>
      </div>
      <div class="status-card">
        <span>Scenario</span>
        <strong>{{ scenarioLabel }}</strong>
      </div>
      <div class="status-card">
        <span>Regions</span>
        <strong>{{ regionRows.length }}</strong>
      </div>
      <div class="status-card">
        <span>Events</span>
        <strong>{{ spreadEvents.length }}</strong>
      </div>
      <div class="status-card">
        <span>Uncertainty</span>
        <strong>{{ uncertaintyLabel }}</strong>
      </div>
    </div>

    <section class="control-panel">
      <div class="control-head">
        <div>
          <div class="panel-title-row">
            <h3>播放控制</h3>
            <span class="hint">{{ runStageLabel }}</span>
          </div>
          <p class="progress-note">{{ runMessage || '系统会按轮次刷新区域状态、扩散事件和干预反馈。' }}</p>
        </div>
        <div class="mini-summary">
          <div class="mini-pill">
            <span>Current</span>
            <strong>{{ currentRoundNumber }}/{{ totalRoundsLabel }}</strong>
          </div>
          <div class="mini-pill">
            <span>Score Key</span>
            <strong>{{ selectedScoreKey }}</strong>
          </div>
        </div>
      </div>

      <div class="slider-shell">
        <input
          v-model.number="roundIndex"
          type="range"
          :min="0"
          :max="Math.max(roundSnapshots.length - 1, 0)"
          step="1"
          class="range"
        />
        <div class="range-labels">
          <span>Start</span>
          <span>Current snapshot: {{ selectedRoundLabel }}</span>
          <span>Latest</span>
        </div>
      </div>

      <div class="selector-row">
        <label class="selector">
          <span>区域评分</span>
          <select v-model="selectedScoreKey">
            <option v-for="key in scoreKeys" :key="key" :value="key">{{ key }}</option>
          </select>
        </label>

        <label class="selector">
          <span>快速回放</span>
          <select v-model.number="roundIndex">
            <option v-for="(snapshot, idx) in roundSnapshots" :key="snapshotKey(snapshot, idx)" :value="idx">
              R{{ extractRoundNumber(snapshot, idx) }}
            </option>
          </select>
        </label>
      </div>
    </section>

    <section v-if="riskObjects.length > 0" class="risk-panel-shell">
      <div class="panel-title-row">
        <h3>风险对象链路</h3>
        <span class="hint">
          {{ riskObjects.length }} objects / {{ riskObjectEntityNodes.length + riskObjectRegionNodes.length }} linked nodes
        </span>
      </div>

      <div class="risk-panel-grid">
        <div class="risk-card-list">
          <button
            v-for="item in riskObjects"
            :key="item.risk_object_id"
            type="button"
            class="risk-object-card"
            :class="{ active: item.risk_object_id === selectedRiskObjectId }"
            @click="selectedRiskObjectId = item.risk_object_id"
          >
            <div class="risk-card-head">
              <span class="risk-mode-tag">{{ item.mode || 'watch' }}</span>
              <span v-if="item.risk_object_id === primaryRiskObjectId" class="risk-primary-tag">PRIMARY</span>
            </div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.why_now || item.summary || '等待风险对象摘要。' }}</p>
            <div class="risk-card-meta">
              <span>Sev {{ normalizeScore(item.severity_score) }}</span>
              <span>Act {{ normalizeScore(item.actionability_score) }}</span>
              <span>Conf {{ formatPercent(item.confidence_score) }}</span>
            </div>
          </button>
        </div>

        <div v-if="selectedRiskObject" class="risk-detail">
          <div class="risk-detail-top">
            <div>
              <div class="eyebrow risk-eyebrow">
                {{ selectedRiskObject.mode === 'incident' ? 'INCIDENT RISK OBJECT' : 'WATCH RISK OBJECT' }}
              </div>
              <h3>{{ selectedRiskObject.title }}</h3>
              <p>{{ selectedRiskObject.summary || selectedRiskObject.why_now || '等待风险对象摘要。' }}</p>
            </div>

            <div class="risk-metrics">
              <div class="mini-pill">
                <span>Severity</span>
                <strong>{{ normalizeScore(selectedRiskObject.severity_score) }}</strong>
              </div>
              <div class="mini-pill">
                <span>Actionability</span>
                <strong>{{ normalizeScore(selectedRiskObject.actionability_score) }}</strong>
              </div>
              <div class="mini-pill">
                <span>Confidence</span>
                <strong>{{ formatPercent(selectedRiskObject.confidence_score) }}</strong>
              </div>
            </div>
          </div>

          <div class="risk-highlight-row">
            <div class="risk-note">
              <span>Why Now</span>
              <strong>{{ selectedRiskObject.why_now || '暂无 why now 描述' }}</strong>
            </div>
            <div class="risk-note">
              <span>Root Pressures</span>
              <strong>{{ formatInlineList(selectedRiskObject.root_pressures, '暂无根压力') }}</strong>
            </div>
          </div>

          <div class="risk-step-pills">
            <span v-for="step in selectedRiskObject.chain_steps || []" :key="step" class="risk-step-pill">{{ step }}</span>
          </div>

          <div class="risk-related-grid">
            <section class="risk-subpanel">
              <div class="subpanel-head">
                <h4>相关实体节点</h4>
                <span>{{ riskObjectEntityNodes.length }}</span>
              </div>
              <div v-if="riskObjectEntityNodes.length > 0" class="node-chip-list">
                <article v-for="node in riskObjectEntityNodes" :key="node.id" class="node-chip">
                  <div class="node-chip-head">
                    <strong>{{ node.name }}</strong>
                    <span class="node-chip-state" :class="{ matched: node.matched }">
                      {{ node.matched ? 'graph node' : 'risk ref' }}
                    </span>
                  </div>
                  <div class="node-chip-labels">
                    <span v-for="label in node.labels" :key="label" class="node-label">{{ label }}</span>
                  </div>
                  <p>{{ node.summary || '该节点当前仅作为风险对象引用出现。' }}</p>
                </article>
              </div>
              <div v-else class="empty-state">当前风险对象还没有映射到实体节点。</div>
            </section>

            <section class="risk-subpanel">
              <div class="subpanel-head">
                <h4>相关区域</h4>
                <span>{{ riskObjectRegionNodes.length }}</span>
              </div>
              <div v-if="riskObjectRegionNodes.length > 0" class="node-chip-list compact">
                <article v-for="region in riskObjectRegionNodes" :key="region.id" class="node-chip compact">
                  <div class="node-chip-head">
                    <strong>{{ region.name }}</strong>
                    <span class="node-chip-state" :class="{ matched: region.matched }">
                      {{ region.matched ? 'graph node' : 'scope' }}
                    </span>
                  </div>
                  <div class="node-chip-labels">
                    <span v-for="label in region.labels" :key="label" class="node-label">{{ label }}</span>
                  </div>
                  <p>{{ region.summary || '当前区域来自风险对象作用域。' }}</p>
                </article>
              </div>
              <div v-else class="empty-state">当前风险对象没有可展示的区域范围。</div>
            </section>

            <section class="risk-subpanel">
              <div class="subpanel-head">
                <h4>受影响群簇</h4>
                <span>{{ riskObjectClusters.length }}</span>
              </div>
              <div v-if="riskObjectClusters.length > 0" class="cluster-list">
                <article v-for="cluster in riskObjectClusters" :key="cluster.cluster_id" class="cluster-card">
                  <div class="cluster-head">
                    <strong>{{ cluster.name }}</strong>
                    <span class="pill">vul {{ normalizeScore(cluster.vulnerability_score) }}</span>
                  </div>
                  <p>{{ formatInlineList(cluster.dependency_profile, '暂无依赖结构描述') }}</p>
                  <div class="risk-card-meta">
                    <span>Mismatch {{ normalizeScore(cluster.mismatch_risk) }}</span>
                    <span>{{ cluster.cluster_type || 'cluster' }}</span>
                  </div>
                </article>
              </div>
              <div v-else class="empty-state">当前风险对象还没有聚合出人群簇。</div>
            </section>
          </div>

          <div class="risk-related-grid secondary">
            <section class="risk-subpanel">
              <div class="subpanel-head">
                <h4>转折点</h4>
                <span>{{ (selectedRiskObject.turning_points || []).length }}</span>
              </div>
              <ul v-if="(selectedRiskObject.turning_points || []).length > 0" class="bullet-list">
                <li v-for="point in selectedRiskObject.turning_points" :key="point">{{ point }}</li>
              </ul>
              <div v-else class="empty-state">当前对象还没有标出显式转折点。</div>
            </section>

            <section class="risk-subpanel">
              <div class="subpanel-head">
                <h4>分支比较</h4>
                <span>{{ (selectedRiskObject.scenario_branches || []).length }}</span>
              </div>
              <div v-if="(selectedRiskObject.scenario_branches || []).length > 0" class="branch-list">
                <article
                  v-for="branch in selectedRiskObject.scenario_branches"
                  :key="branch.branch_id"
                  class="branch-card"
                >
                  <div class="branch-head">
                    <strong>{{ branch.name }}</strong>
                    <span class="pill">{{ branch.branch_type || 'branch' }}</span>
                  </div>
                  <p>{{ branch.description || '等待分支说明。' }}</p>
                </article>
              </div>
              <div v-else class="empty-state">当前对象没有可对比的分支。</div>
            </section>
          </div>
        </div>
      </div>
    </section>

    <div class="workspace">
      <section class="panel region-panel">
        <div class="panel-title-row">
          <h3>区域状态矩阵</h3>
          <span class="hint">按 {{ selectedScoreKey }} 排序</span>
        </div>

        <div class="matrix-head">
          <span>Region</span>
          <span>Selected</span>
          <span>Exposure</span>
          <span>Panic</span>
          <span>Trust</span>
          <span>Vulnerability</span>
        </div>

        <div class="region-list">
          <article v-for="region in regionRows" :key="region.id" class="region-row">
            <div class="region-meta">
              <strong>{{ region.name }}</strong>
              <span>{{ region.tagline }}</span>
            </div>
            <div class="score-cell">
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: `${region.selectedScore}%` }"></div>
              </div>
              <span class="score-text mono">{{ region.selectedScore }}</span>
            </div>
            <span class="metric mono">{{ region.exposure_score }}</span>
            <span class="metric mono">{{ region.panic_level }}</span>
            <span class="metric mono">{{ region.public_trust }}</span>
            <span class="metric mono">{{ region.vulnerability_score }}</span>
          </article>
          <div v-if="regionRows.length === 0" class="empty-state">
            等待后端返回区域矩阵或轮次快照。
          </div>
        </div>
      </section>

      <section class="panel timeline-panel">
        <div class="panel-title-row">
          <h3>扩散与反馈事件</h3>
          <span class="hint">{{ spreadEvents.length }} events</span>
        </div>

        <div class="event-list">
          <article v-for="event in spreadEvents" :key="event.id || `${event.round}-${event.source}-${event.target}`" class="event-card">
            <div class="event-head">
              <strong>{{ event.title || event.label || event.event_type || 'spread event' }}</strong>
              <span class="event-round mono">R{{ event.round || event.round_num || currentRoundNumber }}</span>
            </div>
            <p>{{ event.summary || event.description || event.rationale || '扩散/反馈事件正在被记录。' }}</p>
            <div class="event-pills">
              <span v-if="event.source || event.source_region" class="pill">from {{ event.source || event.source_region }}</span>
              <span v-if="event.target || event.target_region" class="pill">to {{ event.target || event.target_region }}</span>
              <span v-if="event.intensity !== undefined" class="pill">intensity {{ normalizeScore(event.intensity) }}</span>
              <span v-if="event.confidence !== undefined" class="pill">confidence {{ Number(event.confidence).toFixed(2) }}</span>
            </div>
          </article>
          <div v-if="spreadEvents.length === 0" class="empty-state">
            当前轮次未返回显式事件，系统仍会刷新区域状态矩阵。
          </div>
        </div>

        <div class="loop-box">
          <div class="panel-title-row">
            <h3>反馈链路</h3>
            <span class="hint">human-nature loop</span>
          </div>
          <div class="loop-list">
            <span v-for="loop in feedbackLoops" :key="loop" class="loop-pill">{{ loop }}</span>
            <span v-if="feedbackLoops.length === 0" class="empty-loop">environment → ecology → livelihood → panic/media → policy</span>
          </div>
        </div>
      </section>

      <section class="panel injection-panel">
        <div class="panel-title-row">
          <h3>中途变量注入</h3>
          <span class="hint">污染 / 政策 / 约束</span>
        </div>

        <div class="injection-presets">
          <button class="preset-btn" @click="applyPreset('disaster')">污染激增</button>
          <button class="preset-btn" @click="applyPreset('policy')">强制撤离</button>
          <button class="preset-btn" @click="applyPreset('monitor')">监测增强</button>
        </div>

        <div class="form-stack">
          <div class="field-row">
            <label>
              类型
              <select v-model="injection.type">
                <option value="disaster">disaster</option>
                <option value="policy">policy</option>
              </select>
            </label>
            <label>
              干预模式
              <select v-model="injection.policy_mode">
                <option v-for="mode in policyModes" :key="mode" :value="mode">{{ mode }}</option>
              </select>
            </label>
          </div>

          <label>
            名称
            <input v-model="injection.name" type="text" placeholder="核废水排放 / 强制撤离 / 信息公开" />
          </label>

          <label>
            描述
            <textarea v-model="injection.description" rows="4" placeholder="描述该变量如何作用于生态、治理或社会行为。"></textarea>
          </label>

          <div class="field-row">
            <label>
              目标区域
              <input v-model="injection.target_regions_text" type="text" placeholder="滨海区,渔港,下游社区" />
            </label>
            <label>
              目标节点
              <input v-model="injection.target_nodes_text" type="text" placeholder="渔民,居民,环保局,海流" />
            </label>
          </div>

          <div class="field-row">
            <label>
              起始轮次
              <input v-model.number="injection.start_round" type="number" min="0" />
            </label>
            <label>
              持续轮次
              <input v-model.number="injection.duration_rounds" type="number" min="1" />
            </label>
            <label>
              强度
              <input v-model.number="injection.intensity" type="range" min="0" max="100" />
            </label>
          </div>
        </div>

        <div class="action-row">
          <button class="secondary-btn" @click="clearInjection">清空</button>
          <button class="primary-btn" :disabled="isInjecting" @click="handleInject">
            {{ isInjecting ? '注入中...' : '注入变量' }}
          </button>
        </div>

        <div class="injection-log">
          <div class="panel-title-row">
            <h3>注入历史</h3>
            <span class="hint">{{ injectionHistory.length }}</span>
          </div>
          <div v-if="injectionHistory.length > 0" class="history-list">
            <article v-for="item in injectionHistory" :key="item.id" class="history-card">
              <strong>{{ item.name }}</strong>
              <p>{{ item.summary }}</p>
            </article>
          </div>
          <div v-else class="empty-state">
            还没有中途注入记录。
          </div>
        </div>
      </section>
    </div>

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
import { useRoute, useRouter } from 'vue-router'
import { getRunStatus, getRunStatusDetail, getSimulation, getSimulationConfig, injectSimulationVariable, startSimulation, stopSimulation } from '../api/simulation'
import { generateReport } from '../api/report'

const props = defineProps({
  simulationId: String,
  maxRounds: Number,
  minutesPerRound: {
    type: Number,
    default: 30
  },
  projectData: Object,
  graphData: Object,
  systemLogs: Array,
  initialScenarioMode: String,
  initialDiffusionTemplate: String
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status', 'risk-object-focus'])

const route = useRoute()
const router = useRouter()

const isGeneratingReport = ref(false)
const isStarting = ref(false)
const isStopping = ref(false)
const runStatus = ref({})
const runDetail = ref({})
const simulationSnapshot = ref(null)
const configSnapshot = ref(null)
const currentScenarioMode = ref(props.initialScenarioMode || route.query.scenario_mode || 'baseline_mode')
const currentTemplate = ref(props.initialDiffusionTemplate || route.query.diffusion_template || 'marine')
const roundIndex = ref(0)
const selectedScoreKey = ref('vulnerability_score')
const injectionHistory = ref([])
const isInjecting = ref(false)
const injection = ref(createInjection())
const selectedRiskObjectId = ref('')

let statusTimer = null
let detailTimer = null

const scenarioLabel = computed(() => {
  return currentScenarioMode.value === 'crisis_mode' ? '灾难态' : '基线态'
})

const templateLabel = computed(() => {
  const map = { air: 'air', inland_water: 'inland_water', marine: 'marine' }
  return map[currentTemplate.value] || currentTemplate.value || 'marine'
})

const totalRoundsLabel = computed(() => {
  return runStatus.value.total_rounds || props.maxRounds || roundSnapshots.value.length || '-'
})

const runStageLabel = computed(() => {
  if (runStatus.value.runner_status === 'completed') return 'completed'
  if (runStatus.value.runner_status === 'stopped') return 'stopped'
  if (runStatus.value.runner_status === 'running') return 'running'
  if (isStarting.value) return 'starting'
  return 'idle'
})

const runMessage = computed(() => {
  return runDetail.value.message || runStatus.value.message || ''
})

const uncertaintyLabel = computed(() => {
  const value = runDetail.value.uncertainty_band || runDetail.value.uncertainty || runStatus.value.uncertainty_band
  if (value === undefined || value === null || value === '') return 'n/a'
  if (typeof value === 'number') return value.toFixed(2)
  return String(value)
})

const roundSnapshots = computed(() => {
  const source = runDetail.value.round_snapshots || runDetail.value.snapshots || runDetail.value.round_history || []
  return Array.isArray(source) ? source : []
})

const selectedRoundSnapshot = computed(() => {
  if (roundSnapshots.value.length === 0) {
    return runDetail.value.latest_round_snapshot || null
  }
  const safeIndex = Math.min(Math.max(roundIndex.value, 0), roundSnapshots.value.length - 1)
  return roundSnapshots.value[safeIndex] || null
})

const currentRoundNumber = computed(() => {
  if (selectedRoundSnapshot.value) return extractRoundNumber(selectedRoundSnapshot.value, roundIndex.value)
  return runStatus.value.current_round || runStatus.value.current_round_num || 0
})

const selectedRoundLabel = computed(() => {
  return selectedRoundSnapshot.value ? `R${currentRoundNumber.value}` : 'live'
})

const scoreKeys = computed(() => {
  const keys = new Set([
    'exposure_score',
    'spread_pressure',
    'ecosystem_integrity',
    'livelihood_stability',
    'public_trust',
    'panic_level',
    'service_capacity',
    'response_capacity',
    'economic_stress',
    'vulnerability_score'
  ])

  regionRows.value.forEach(row => {
    Object.keys(row).forEach(key => {
      if (key.endsWith('_score') || key.endsWith('_level') || key.endsWith('_stress') || key.endsWith('_capacity') || key.endsWith('_integrity') || key.endsWith('_stability')) {
        keys.add(key)
      }
    })
  })

  return Array.from(keys)
})

const regionRows = computed(() => {
  const snapshot = selectedRoundSnapshot.value || runDetail.value
  const regions = normalizeRegionRows(snapshot)
  const key = selectedScoreKey.value

  return regions
    .map(region => ({
      ...region,
      selectedScore: normalizeScore(region[key]),
      tagline: region.tagline || region.region_type || region.zone || 'region'
    }))
    .sort((a, b) => b.selectedScore - a.selectedScore)
})

const spreadEvents = computed(() => {
  const source = normalizeEvents(runDetail.value)
  const maxRound = currentRoundNumber.value || Number.MAX_SAFE_INTEGER
  return source.filter(event => (event.round || event.round_num || 0) <= maxRound)
})

const feedbackLoops = computed(() => {
  const loops = runDetail.value.feedback_loops || runDetail.value.loop_summary || runDetail.value.feedback_chain || []
  if (Array.isArray(loops)) return loops.map(String)
  if (typeof loops === 'string') {
    return loops.split('|').map(item => item.trim()).filter(Boolean)
  }
  return []
})

const riskObjects = computed(() => {
  const candidates = [
    runDetail.value?.risk_objects,
    simulationSnapshot.value?.risk_objects,
    configSnapshot.value?.risk_objects
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
    runDetail.value?.primary_risk_object?.risk_object_id ||
    runDetail.value?.risk_objects_summary?.primary_risk_object_id ||
    simulationSnapshot.value?.primary_risk_object?.risk_object_id ||
    simulationSnapshot.value?.risk_objects_summary?.primary_risk_object_id ||
    configSnapshot.value?.primary_risk_object_id ||
    riskObjects.value[0]?.risk_object_id ||
    ''
  )
})

const selectedRiskObject = computed(() => {
  if (riskObjects.value.length === 0) return null
  return riskObjects.value.find(item => item.risk_object_id === selectedRiskObjectId.value) || riskObjects.value[0]
})

const graphNodes = computed(() => collectGraphNodes(props.graphData))

const graphNodeMap = computed(() => {
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
    const name = String(node?.name || '').trim().toLowerCase()
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
    const node = graphNodeMap.value.get(uuid)
    const evidence = evidenceByUuid.get(uuid)
    return {
      id: node?.uuid || `risk-entity-${index}`,
      uuid,
      name: node?.name || evidence?.title || `entity_${index + 1}`,
      labels: normalizeLabels(node?.labels),
      summary: node?.summary || evidence?.summary || '',
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
      summary: node?.summary || '',
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

function addLog(msg) {
  emit('add-log', msg)
}

function createInjection() {
  return {
    type: 'disaster',
    name: '',
    description: '',
    target_regions_text: '',
    target_nodes_text: '',
    start_round: 0,
    duration_rounds: 3,
    intensity: 70,
    policy_mode: 'restrict'
  }
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
  if (Array.isArray(data?.nodes)) return data.nodes
  if (Array.isArray(data?.graph?.nodes)) return data.graph.nodes
  return []
}

function extractRoundNumber(snapshot, fallback = 0) {
  return snapshot?.round || snapshot?.round_num || snapshot?.step || fallback + 1
}

function snapshotKey(snapshot, idx) {
  return snapshot?.id || `${extractRoundNumber(snapshot, idx)}-${idx}`
}

function normalizeRegionRows(source) {
  const raw =
    source?.region_states ||
    source?.regions ||
    source?.region_matrix ||
    source?.state_matrix ||
    source?.matrix ||
    []

  const rows = []

  if (Array.isArray(raw)) {
    raw.forEach((item, idx) => {
      if (typeof item === 'string') {
        rows.push({ id: `${idx}`, name: item })
        return
      }
      const name = item.region || item.region_name || item.name || item.label || item.id || `region_${idx}`
      rows.push({
        id: item.id || `${name}-${idx}`,
        name,
        tagline: item.region_type || item.category || item.type || '',
        exposure_score: normalizeScore(item.exposure_score ?? item.exposure ?? 0),
        spread_pressure: normalizeScore(item.spread_pressure ?? item.spread ?? 0),
        ecosystem_integrity: normalizeScore(item.ecosystem_integrity ?? item.ecosystem ?? 100),
        livelihood_stability: normalizeScore(item.livelihood_stability ?? item.livelihood ?? 100),
        public_trust: normalizeScore(item.public_trust ?? item.trust ?? 100),
        panic_level: normalizeScore(item.panic_level ?? item.panic ?? 0),
        service_capacity: normalizeScore(item.service_capacity ?? item.service ?? 100),
        response_capacity: normalizeScore(item.response_capacity ?? item.response ?? 100),
        economic_stress: normalizeScore(item.economic_stress ?? item.stress ?? 0),
        vulnerability_score: normalizeScore(item.vulnerability_score ?? item.vulnerability ?? 0)
      })
    })
    return rows
  }

  if (raw && typeof raw === 'object') {
    Object.entries(raw).forEach(([key, value], idx) => {
      if (value && typeof value === 'object') {
        rows.push({
          id: key,
          name: value.region || value.name || key,
          tagline: value.region_type || value.category || '',
          exposure_score: normalizeScore(value.exposure_score ?? value.exposure ?? 0),
          spread_pressure: normalizeScore(value.spread_pressure ?? value.spread ?? 0),
          ecosystem_integrity: normalizeScore(value.ecosystem_integrity ?? value.ecosystem ?? 100),
          livelihood_stability: normalizeScore(value.livelihood_stability ?? value.livelihood ?? 100),
          public_trust: normalizeScore(value.public_trust ?? value.trust ?? 100),
          panic_level: normalizeScore(value.panic_level ?? value.panic ?? 0),
          service_capacity: normalizeScore(value.service_capacity ?? value.service ?? 100),
          response_capacity: normalizeScore(value.response_capacity ?? value.response ?? 100),
          economic_stress: normalizeScore(value.economic_stress ?? value.stress ?? 0),
          vulnerability_score: normalizeScore(value.vulnerability_score ?? value.vulnerability ?? 0)
        })
      } else {
        rows.push({ id: `${key}-${idx}`, name: key, selectedScore: normalizeScore(value) })
      }
    })
  }

  return rows
}

function normalizeEvents(source) {
  const raw =
    source?.spread_events ||
    source?.events ||
    source?.event_log ||
    source?.actions ||
    source?.all_actions ||
    []

  if (!Array.isArray(raw)) return []

  return raw.map((event, idx) => ({
    id: event.id || `${event.round || event.round_num || idx}-${idx}`,
    round: event.round || event.round_num || event.step || idx + 1,
    title: event.title || event.event_name || event.label || event.action_type || '',
    label: event.label,
    event_type: event.event_type || event.type || event.action_type || '',
    source: event.source || event.source_region || event.from || '',
    target: event.target || event.target_region || event.to || '',
    summary: event.summary || event.description || event.text || event.rationale || event.message || '',
    rationale: event.rationale || event.reason || '',
    intensity: event.intensity ?? event.transfer_intensity ?? event.score ?? undefined,
    confidence: event.confidence ?? event.probability ?? undefined
  }))
}

function applyPreset(type) {
  const presets = {
    disaster: {
      type: 'disaster',
      name: '污染激增',
      description: '环境载体出现高强度污染输入，检查扩散链条和首次跨界触发点。',
      target_regions_text: '沿海区,近岸海域',
      target_nodes_text: '海流,鱼类,渔民',
      start_round: currentRoundNumber.value,
      duration_rounds: 4,
      intensity: 85,
      policy_mode: 'restrict'
    },
    policy: {
      type: 'policy',
      name: '强制撤离',
      description: '对高暴露区域实施强制撤离，观察信任、顺从和次生摩擦。',
      target_regions_text: '居民区,高暴露区',
      target_nodes_text: '居民,地方官员,交通网',
      start_round: currentRoundNumber.value,
      duration_rounds: 3,
      intensity: 70,
      policy_mode: 'relocate'
    },
    monitor: {
      type: 'policy',
      name: '监测增强',
      description: '提高检测频率和信息公开，观察辟谣和预警传播效果。',
      target_regions_text: '全域',
      target_nodes_text: '环保局,媒体,医院',
      start_round: currentRoundNumber.value,
      duration_rounds: 2,
      intensity: 45,
      policy_mode: 'monitor'
    }
  }

  const preset = presets[type]
  if (!preset) return
  injection.value = { ...preset }
}

function clearInjection() {
  injection.value = createInjection()
}

async function handleInject() {
  if (!props.simulationId || isInjecting.value) return

  isInjecting.value = true
  try {
    const payload = {
      simulation_id: props.simulationId,
      type: injection.value.type,
      name: injection.value.name || (injection.value.type === 'policy' ? 'policy_injection' : 'disaster_injection'),
      description: injection.value.description || '',
      target_regions: splitList(injection.value.target_regions_text),
      target_nodes: splitList(injection.value.target_nodes_text),
      start_round: Number(injection.value.start_round) || 0,
      duration_rounds: Math.max(1, Number(injection.value.duration_rounds) || 1),
      intensity: normalizeScore(injection.value.intensity),
      policy_mode: injection.value.type === 'policy' ? injection.value.policy_mode : 'restrict'
    }

    const res = await injectSimulationVariable(payload)
    if (res.success) {
      const summary = `${payload.name} @ R${payload.start_round} (${payload.type}, ${payload.intensity})`
      injectionHistory.value.unshift({
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        name: payload.name,
        summary
      })
      addLog(`✓ 中途变量已注入: ${summary}`)
      await refreshDetail()
    } else {
      addLog(`✗ 注入失败: ${res.error || '未知错误'}`)
    }
  } catch (err) {
    addLog(`✗ 注入异常: ${err.message}`)
  } finally {
    isInjecting.value = false
  }
}

function splitList(value) {
  if (!value) return []
  return String(value)
    .split(/[,\n;]/)
    .map(item => item.trim())
    .filter(Boolean)
}

async function startRun() {
  if (!props.simulationId || isStarting.value) return

  isStarting.value = true
  emit('update-status', 'processing')
  addLog('正在启动 EnvFish 半定量推演...')

  try {
    const res = await startSimulation({
      simulation_id: props.simulationId,
      engine_mode: 'envfish',
      platform: 'envfish',
      scenario_mode: currentScenarioMode.value,
      diffusion_template: currentTemplate.value,
      max_rounds: props.maxRounds || undefined,
      enable_graph_memory_update: true,
      force: true
    })

    if (res.success && res.data) {
      runStatus.value = res.data
      addLog('✓ EnvFish 推演引擎已启动')
      addLog(`  ├─ PID: ${res.data.process_pid || '-'}`)
      addLog(`  └─ 模式: ${currentScenarioMode.value} / ${currentTemplate.value}`)
      startPolling()
      await refreshStatus()
      await refreshDetail()
    } else {
      emit('update-status', 'error')
      addLog(`✗ 启动失败: ${res.error || '未知错误'}`)
    }
  } catch (err) {
    emit('update-status', 'error')
    addLog(`✗ 启动异常: ${err.message}`)
  } finally {
    isStarting.value = false
  }
}

async function handleStop() {
  if (!props.simulationId || isStopping.value) return

  isStopping.value = true
  try {
    const res = await stopSimulation({ simulation_id: props.simulationId })
    if (res.success) {
      addLog('✓ 推演已停止')
      emit('update-status', 'completed')
      stopPolling()
      await refreshStatus()
      await refreshDetail()
    } else {
      addLog(`停止失败: ${res.error || '未知错误'}`)
    }
  } catch (err) {
    addLog(`停止异常: ${err.message}`)
  } finally {
    isStopping.value = false
  }
}

async function handleNextStep() {
  if (!props.simulationId) return

  if (isGeneratingReport.value) {
    addLog('报告生成请求已发送，请稍候...')
    return
  }

  isGeneratingReport.value = true
  addLog('正在生成 EnvFish 报告...')

  try {
    const res = await generateReport({
      simulation_id: props.simulationId,
      force_regenerate: true
    })

    if (res.success && res.data) {
      const reportId = res.data.report_id
      addLog(`✓ 报告生成任务已启动: ${reportId}`)
      router.push({ name: 'Report', params: { reportId } })
    } else {
      addLog(`✗ 报告生成失败: ${res.error || '未知错误'}`)
      isGeneratingReport.value = false
    }
  } catch (err) {
    addLog(`✗ 报告生成异常: ${err.message}`)
    isGeneratingReport.value = false
  }
}

function handleGoBack() {
  emit('go-back')
}

async function refreshSimulationContext() {
  if (!props.simulationId) return

  try {
    const [simulationRes, configRes] = await Promise.allSettled([
      getSimulation(props.simulationId),
      getSimulationConfig(props.simulationId)
    ])

    if (simulationRes.status === 'fulfilled' && simulationRes.value?.success) {
      simulationSnapshot.value = simulationRes.value.data || null
      currentScenarioMode.value = simulationSnapshot.value?.scenario_mode || currentScenarioMode.value
      currentTemplate.value = simulationSnapshot.value?.diffusion_template || currentTemplate.value
    }

    if (configRes.status === 'fulfilled' && configRes.value?.success && configRes.value.data) {
      configSnapshot.value = configRes.value.data
      if (configRes.value.data.scenario_mode) currentScenarioMode.value = configRes.value.data.scenario_mode
      if (configRes.value.data.diffusion_template) currentTemplate.value = configRes.value.data.diffusion_template
      if (configRes.value.data.max_rounds) roundIndex.value = 0
      if (configRes.value.data.time_config?.minutes_per_round) {
        addLog(`时间粒度: ${configRes.value.data.time_config.minutes_per_round} min / round`)
      }
    }
  } catch (err) {
    addLog(`加载推演上下文失败: ${err.message}`)
  }
}

async function refreshStatus() {
  if (!props.simulationId) return

  try {
    const res = await getRunStatus(props.simulationId)
    if (res.success && res.data) {
      runStatus.value = res.data
      if (runStatus.value.current_round !== undefined) {
        const latestIndex = Math.max((roundSnapshots.value.length || 1) - 1, 0)
        roundIndex.value = latestIndex
      }
      if (res.data.runner_status === 'completed' || res.data.runner_status === 'stopped') {
        emit('update-status', 'completed')
      }
    }
  } catch (err) {
    console.warn('run status failed', err)
  }
}

async function refreshDetail() {
  if (!props.simulationId) return

  try {
    const res = await getRunStatusDetail(props.simulationId)
    if (res.success && res.data) {
      runDetail.value = res.data
      if (runDetail.value.message) {
        addLog(runDetail.value.message)
      }

      if (roundSnapshots.value.length > 0) {
        roundIndex.value = Math.min(roundIndex.value, roundSnapshots.value.length - 1)
      }
    }
  } catch (err) {
    console.warn('run detail failed', err)
  }
}

function startPolling() {
  stopPolling()
  statusTimer = setInterval(refreshStatus, 2000)
  detailTimer = setInterval(refreshDetail, 3000)
}

function stopPolling() {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
  if (detailTimer) {
    clearInterval(detailTimer)
    detailTimer = null
  }
}

watch(
  () => props.initialScenarioMode,
  (value) => {
    if (value) currentScenarioMode.value = value
  }
)

watch(
  () => props.initialDiffusionTemplate,
  (value) => {
    if (value) currentTemplate.value = value
  }
)

watch(
  () => roundSnapshots.value.length,
  (value) => {
    if (value > 0) {
      roundIndex.value = value - 1
    }
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
  addLog('EnvFish Step3 初始化')
  await refreshSimulationContext()
  await startRun()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.envfish-step {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(255, 191, 105, 0.18), transparent 30%),
    radial-gradient(circle at top right, rgba(28, 196, 135, 0.16), transparent 28%),
    linear-gradient(180deg, #fffaf4 0%, #ffffff 100%);
  color: #1e2333;
}

.hero,
.control-panel,
.panel,
.log-shell {
  border: 1px solid rgba(44, 44, 66, 0.08);
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(10px);
  box-shadow: 0 12px 32px rgba(17, 31, 59, 0.06);
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 22px;
  border-radius: 24px;
}

.eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.2em;
  color: #9a6a2f;
}

.hero h2 {
  margin: 10px 0 8px;
  font-size: 28px;
  line-height: 1.1;
}

.hero p {
  margin: 0;
  max-width: 680px;
  color: #656779;
}

.hero-controls {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
}

.ghost-btn,
.primary-btn,
.preset-btn,
.secondary-btn {
  border: none;
  border-radius: 14px;
  padding: 10px 14px;
  cursor: pointer;
  font-weight: 700;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.ghost-btn,
.secondary-btn,
.preset-btn {
  background: rgba(29, 39, 58, 0.06);
  color: #27344a;
}

.primary-btn {
  background: linear-gradient(135deg, #0f3d63, #f08a24);
  color: #fff;
}

.ghost-btn:hover,
.secondary-btn:hover,
.primary-btn:hover,
.preset-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(31, 57, 98, 0.1);
}

.status-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.status-card {
  border-radius: 18px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(39, 56, 84, 0.08);
}

.status-card span,
.hint,
.panel-title-row span {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7d8393;
}

.status-card strong {
  display: block;
  margin-top: 8px;
  font-size: 18px;
  color: #183058;
}

.status-card.accent {
  background: linear-gradient(135deg, rgba(233, 243, 255, 0.98), rgba(255, 244, 225, 0.96));
}

.control-panel {
  border-radius: 24px;
  padding: 16px 18px;
}

.risk-panel-shell {
  border-radius: 24px;
  padding: 16px 18px;
  border: 1px solid rgba(44, 44, 66, 0.08);
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(10px);
  box-shadow: 0 12px 32px rgba(17, 31, 59, 0.06);
}

.control-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.panel-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-title-row h3 {
  margin: 0;
  font-size: 16px;
}

.mini-summary {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.mini-pill {
  border-radius: 16px;
  padding: 10px 12px;
  background: rgba(17, 31, 59, 0.05);
  min-width: 132px;
}

.mini-pill span {
  display: block;
  font-size: 11px;
  color: #7d8393;
}

.mini-pill strong {
  display: block;
  margin-top: 6px;
  color: #183058;
}

.slider-shell {
  margin-top: 14px;
}

.range {
  width: 100%;
}

.range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #808699;
  margin-top: 8px;
}

.selector-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.selector {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.selector span {
  font-size: 12px;
  color: #4f5568;
}

.selector select,
.form-stack input,
.form-stack select,
.form-stack textarea {
  width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(29, 39, 58, 0.12);
  background: #fff;
  color: #1e2333;
  padding: 10px 12px;
  font: inherit;
}

.workspace {
  display: grid;
  grid-template-columns: 1.2fr 1fr 0.9fr;
  gap: 14px;
  min-height: 0;
  flex: 1;
}

.risk-panel-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 14px;
}

.risk-card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.risk-object-card {
  width: 100%;
  border: 1px solid rgba(29, 39, 58, 0.08);
  border-radius: 18px;
  padding: 14px;
  background: linear-gradient(180deg, #fff, #f8fbff);
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.risk-object-card:hover,
.risk-object-card.active {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(17, 31, 59, 0.08);
  border-color: rgba(17, 61, 122, 0.22);
}

.risk-object-card.active {
  background: linear-gradient(180deg, rgba(232, 242, 255, 0.92), rgba(255, 245, 229, 0.92));
}

.risk-card-head,
.cluster-head,
.branch-head,
.subpanel-head,
.node-chip-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.risk-mode-tag,
.risk-primary-tag,
.node-chip-state {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.risk-mode-tag {
  background: rgba(17, 61, 122, 0.1);
  color: #113d7a;
}

.risk-primary-tag {
  background: rgba(240, 138, 36, 0.14);
  color: #9a5b11;
}

.risk-object-card strong,
.risk-detail h3 {
  display: block;
  margin-top: 10px;
  color: #173056;
}

.risk-object-card p,
.risk-detail p,
.node-chip p,
.cluster-card p,
.branch-card p {
  margin: 8px 0 0;
  color: #5f6577;
  line-height: 1.5;
  font-size: 13px;
}

.risk-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  font-size: 12px;
  color: #4f5568;
}

.risk-card-meta span {
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(17, 31, 59, 0.05);
}

.risk-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.risk-detail-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.risk-eyebrow {
  color: #0f517d;
}

.risk-metrics {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.risk-highlight-row,
.risk-related-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.risk-related-grid.secondary {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.risk-note,
.risk-subpanel {
  border-radius: 18px;
  padding: 14px;
  background: linear-gradient(180deg, #fff, #f8fbff);
  border: 1px solid rgba(29, 39, 58, 0.08);
}

.risk-note span,
.subpanel-head span {
  display: block;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7d8393;
}

.risk-note strong {
  display: block;
  margin-top: 8px;
  color: #1d355b;
  line-height: 1.5;
}

.risk-step-pills,
.node-chip-labels,
.branch-list,
.cluster-list,
.node-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.risk-step-pill {
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(17, 61, 122, 0.08);
  color: #113d7a;
  font-size: 12px;
}

.node-chip-list,
.cluster-list,
.branch-list {
  flex-direction: column;
}

.node-chip,
.cluster-card,
.branch-card {
  border-radius: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(29, 39, 58, 0.07);
}

.node-chip.compact {
  padding: 10px 12px;
}

.node-chip-state {
  background: rgba(124, 132, 147, 0.12);
  color: #6a7283;
}

.node-chip-state.matched {
  background: rgba(28, 196, 135, 0.14);
  color: #0c7850;
}

.node-label {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(240, 138, 36, 0.1);
  color: #9a5b11;
  font-size: 11px;
}

.bullet-list {
  margin: 0;
  padding-left: 18px;
  color: #4f5568;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
}

.panel {
  border-radius: 24px;
  padding: 16px;
  min-height: 0;
  overflow: auto;
}

.matrix-head,
.region-row {
  display: grid;
  grid-template-columns: 1.8fr 1.5fr 0.8fr 0.8fr 0.8fr 0.9fr;
  gap: 10px;
  align-items: center;
}

.matrix-head {
  margin-bottom: 10px;
  font-size: 11px;
  color: #7f8495;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.region-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.region-row {
  padding: 12px 10px;
  border-radius: 18px;
  background: linear-gradient(180deg, #fff, #f9fbff);
  border: 1px solid rgba(29, 39, 58, 0.08);
}

.region-meta strong {
  display: block;
  margin-bottom: 4px;
}

.region-meta span {
  display: block;
  font-size: 12px;
  color: #7d8393;
}

.score-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: rgba(19, 32, 51, 0.08);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #f08a24, #113d7a);
  border-radius: inherit;
}

.score-text,
.metric {
  font-size: 13px;
  font-weight: 700;
  color: #1e2333;
}

.event-list,
.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.event-card,
.history-card {
  border-radius: 18px;
  padding: 12px 14px;
  background: linear-gradient(180deg, #fff, #f8fafe);
  border: 1px solid rgba(29, 39, 58, 0.08);
}

.event-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.event-card p,
.history-card p,
.progress-note {
  margin: 8px 0 0;
  color: #5f6577;
  line-height: 1.5;
  font-size: 13px;
}

.event-pills,
.loop-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.pill,
.loop-pill,
.empty-loop {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(240, 138, 36, 0.1);
  color: #9a5b11;
  font-size: 12px;
}

.loop-box {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed rgba(29, 39, 58, 0.12);
}

.injection-presets,
.action-row,
.field-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.form-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.field-row label,
.form-stack > label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  font-size: 12px;
  color: #4f5568;
}

.injection-panel .action-row {
  margin-top: 14px;
}

.injection-log {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed rgba(29, 39, 58, 0.12);
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
}

.log-line {
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: 10px;
  font-size: 12px;
  color: #334055;
}

.log-time {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: #808699;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.empty-state {
  padding: 14px;
  border-radius: 16px;
  background: rgba(29, 39, 58, 0.04);
  color: #6f7588;
  font-size: 13px;
}

@media (max-width: 1280px) {
  .risk-panel-grid,
  .risk-highlight-row,
  .risk-related-grid,
  .risk-related-grid.secondary {
    grid-template-columns: 1fr;
  }

  .workspace {
    grid-template-columns: 1fr;
  }

  .status-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .hero {
    flex-direction: column;
  }
}
</style>
