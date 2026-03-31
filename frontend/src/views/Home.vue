<template>
  <div class="env-home">
    <div class="ambient ambient-a"></div>
    <div class="ambient ambient-b"></div>
    <div class="ambient ambient-c"></div>

    <header class="topbar">
      <button class="brand-lockup" type="button" @click="scrollToTop">
        <span class="brand-mark">EF</span>
        <span class="brand-copy">
          <strong>ENVFISH</strong>
          <small>Ecological Foresight Engine</small>
        </span>
      </button>

      <div class="topbar-links">
        <button class="ghost-link" type="button" @click="scrollToComposer">启动推演</button>
        <button class="ghost-link" type="button" @click="scrollToHistory">历史记录</button>
        <a
          class="repo-link"
          href="https://github.com/crisisjungle/Envfish"
          target="_blank"
          rel="noreferrer"
        >
          GitHub ↗
        </a>
      </div>
    </header>

    <main class="page-shell">
      <section class="hero-grid">
        <div class="hero-copy">
          <div class="eyebrow-row">
            <span class="eyebrow-pill">生态推演引擎</span>
            <span class="eyebrow-note">多智能体环境仿真 / Envfish v0.1</span>
          </div>

          <h1 class="hero-title">把环境变量丢进沙盘，让系统自己演化。</h1>

          <p class="hero-lead">
            Envfish 将报告、访谈、政策草案和事件材料转成可干预的生态场景。你定义变量，我们生成图谱、角色、环境与多轮模拟，再返回报告与交互入口。
          </p>

          <div class="hero-actions">
            <button class="primary-cta" type="button" @click="scrollToComposer">
              进入首页控制台
            </button>
            <button class="secondary-cta" type="button" @click="scrollToHistory">
              查看推演记录
            </button>
          </div>

          <div class="metric-grid">
            <article v-for="item in heroMetrics" :key="item.label" class="metric-card">
              <span class="metric-label">{{ item.label }}</span>
              <strong class="metric-value">{{ item.value }}</strong>
              <p class="metric-note">{{ item.note }}</p>
            </article>
          </div>
        </div>

        <div class="hero-stage">
          <div class="stage-frame">
            <div class="stage-ribbon">LIVE PIPELINE</div>
            <div class="stage-card">
              <div class="stage-header">
                <div>
                  <p class="stage-label">生态推演控制面板</p>
                  <h2>从种子材料到环境输出</h2>
                </div>
                <span class="stage-status">READY</span>
              </div>

              <div class="stage-stream">
                <div v-for="stream in stageStreams" :key="stream.title" class="stream-card">
                  <span class="stream-index">{{ stream.index }}</span>
                  <div>
                    <h3>{{ stream.title }}</h3>
                    <p>{{ stream.desc }}</p>
                  </div>
                </div>
              </div>
            </div>

            <div class="signal-card">
              <div class="signal-header">
                <span>Scenario Lens</span>
                <span>{{ selectedFileSummary }}</span>
              </div>
              <div class="signal-grid">
                <div v-for="tag in signalTags" :key="tag.title" class="signal-item">
                  <strong>{{ tag.title }}</strong>
                  <p>{{ tag.desc }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="prompt-band">
        <div class="section-copy">
          <span class="section-kicker">Prompt Seeds</span>
          <h2>先选一个生态切口，再把变量写进系统。</h2>
          <p>
            下方模板只负责起笔。真正的输入仍然是你的材料与约束条件，首页会把它们送进现有流程，不会额外制造新的入口。
          </p>
        </div>

        <div class="prompt-grid">
          <button
            v-for="idea in promptIdeas"
            :key="idea.title"
            class="prompt-card"
            type="button"
            @click="applyPrompt(idea.prompt)"
          >
            <span class="prompt-type">{{ idea.type }}</span>
            <strong>{{ idea.title }}</strong>
            <p>{{ idea.desc }}</p>
          </button>
        </div>
      </section>

      <section class="workflow-section">
        <div class="section-copy">
          <span class="section-kicker">Workflow</span>
          <h2>保留原有 5 步流程，但首页入口全部重排。</h2>
          <p>
            图谱构建、环境搭建、模拟、报告和互动能力仍然沿用现有工作台；变化的是首页的信息组织方式和品牌表达。
          </p>
        </div>

        <div class="workflow-grid">
          <article v-for="step in workflowSteps" :key="step.id" class="workflow-card">
            <span class="workflow-id">{{ step.id }}</span>
            <h3>{{ step.title }}</h3>
            <p>{{ step.desc }}</p>
          </article>
        </div>
      </section>

      <section id="launch-composer" class="launch-section">
        <div class="launch-copy">
          <span class="section-kicker">Launch Console</span>
          <h2>把材料、目标和变量一次交给 Envfish。</h2>
          <p>
            首页只做一件事：把输入准备干净，然后无缝送入 `/process/new`。后续图谱和仿真工作流仍在现有页面里继续。
          </p>

          <div class="mode-switch">
            <button
              v-for="mode in launchModes"
              :key="mode.value"
              class="mode-switch-btn"
              :class="{ active: launchMode === mode.value }"
              type="button"
              @click="launchMode = mode.value"
            >
              {{ mode.label }}
            </button>
          </div>

          <div class="launch-points">
            <article v-for="point in launchPoints" :key="point.title" class="launch-point">
              <strong>{{ point.title }}</strong>
              <p>{{ point.desc }}</p>
            </article>
          </div>
        </div>

        <div class="launch-console">
          <template v-if="launchMode === 'document'">
            <div class="console-card">
              <div class="console-header">
                <div>
                  <span class="console-label">01 / Seed Intake</span>
                  <h3>现实材料上传</h3>
                </div>
                <span class="console-meta">支持 PDF / MD / TXT</span>
              </div>

              <div
                class="upload-zone"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt"
                  :disabled="loading"
                  class="hidden-input"
                  @change="handleFileSelect"
                />

                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-glyph">∿</div>
                  <strong>拖拽材料到这里</strong>
                  <p>也可以点击区域，直接从本地文件系统选取</p>
                </div>

                <div v-else class="file-stack">
                  <div v-for="(file, index) in files" :key="`${file.name}-${file.size}-${index}`" class="file-chip">
                    <div class="file-chip-copy">
                      <strong>{{ file.name }}</strong>
                      <span>{{ formatFileSize(file.size) }}</span>
                    </div>
                    <button class="remove-file" type="button" @click.stop="removeFile(index)">×</button>
                  </div>
                </div>
              </div>

              <div class="format-row">
                <span v-for="format in acceptedFormats" :key="format" class="format-pill">{{ format }}</span>
              </div>
            </div>

            <div class="console-card">
              <div class="console-header">
                <div>
                  <span class="console-label">02 / Simulation Brief</span>
                  <h3>生态变量与目标</h3>
                </div>
                <span class="console-meta">建议写清楚对象、触发条件、时间窗</span>
              </div>

              <textarea
                v-model="formData.simulationRequirement"
                class="brief-input"
                rows="8"
                :disabled="loading"
                placeholder="// 例：在一场城市滨海湿地修复计划中，如果同时加入极端天气、游客增长和排污政策收紧三个变量，生态网络会如何演化？"
              ></textarea>

              <div class="composer-footer">
                <div class="engine-note">
                  <span class="engine-pulse"></span>
                  引擎: Envfish Ecological Simulation Stack
                </div>
                <button
                  class="primary-cta launch-button"
                  type="button"
                  :disabled="!canSubmit || loading"
                  @click="startSimulation"
                >
                  <span v-if="loading">初始化中...</span>
                  <span v-else>进入推演流程</span>
                </button>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="console-card map-console-card">
              <div class="console-header">
                <div>
                  <span class="console-label">01 / Map Seed</span>
                  <h3>地图选点建模</h3>
                </div>
                <span class="console-meta">开放数据 + 卫星图 + LLM 代理节点</span>
              </div>

              <div class="map-intro">
                <p>
                  先在地图上选点，系统会自动收集周边空间要素、生态底图和设施骨架，再生成可切换的实景图谱。
                </p>
                <div class="map-intro-grid">
                  <article v-for="item in mapIntroCards" :key="item.title" class="map-intro-card">
                    <strong>{{ item.title }}</strong>
                    <p>{{ item.desc }}</p>
                  </article>
                </div>
              </div>

              <div class="composer-footer">
                <div class="engine-note">
                  <span class="engine-pulse"></span>
                  引擎: Map-First Seed Workspace
                </div>
                <button class="primary-cta launch-button" type="button" @click="openMapWorkspace">
                  打开地图工作台
                </button>
              </div>
            </div>

            <div class="console-card">
              <div class="console-header">
                <div>
                  <span class="console-label">02 / Output</span>
                  <h3>输出形式</h3>
                </div>
                <span class="console-meta">实景图谱 / 纯图谱可切换</span>
              </div>

              <div class="format-row map-output-row">
                <span v-for="format in mapOutputFormats" :key="format" class="format-pill">{{ format }}</span>
              </div>
              <p class="map-output-note">
                地图模式不会替换现有文档流程，只是提供一条更轻的输入路径，适合从地理位置直接起步。
              </p>
            </div>
          </template>
        </div>
      </section>

      <section id="history-records" class="history-section">
        <div class="section-copy history-copy">
          <span class="section-kicker">History</span>
          <h2>历史推演仍然保留，只是换了首页入口。</h2>
          <p>这里沿用现有项目记录能力，便于直接回放已有图谱、环境和报告。</p>
        </div>

        <HistoryDatabase />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'

const router = useRouter()

const acceptedFormats = ['PDF', 'MD', 'TXT']
const heroMetrics = [
  { label: '输入形态', value: '非结构化材料', note: '报告、访谈、笔记与长文本都能作为生态种子。' },
  { label: '推演核心', value: '环境变量注入', note: '把政策、资源、冲击事件写进同一个系统。' },
  { label: '输出结果', value: '图谱 + 报告 + 互动', note: '保留现有工作台与回放链路，不拆用户习惯。' }
]
const stageStreams = [
  { index: '01', title: 'Seed', desc: '材料归档、事实抽取、上下文对齐。' },
  { index: '02', title: 'Habitat', desc: '角色画像、关系网和环境约束注入。' },
  { index: '03', title: 'Simulation', desc: '多轮演化、变量扰动、报告生成。' }
]
const signalTags = [
  { title: '政策冲击', desc: '监管变化如何重排环境参与者。' },
  { title: '生态恢复', desc: '修复动作是否真的改善系统稳定性。' },
  { title: '舆情扩散', desc: '群体感知如何反过来影响真实环境。' }
]
const promptIdeas = [
  {
    type: 'Wetland',
    title: '湿地修复推演',
    desc: '评估治理计划、极端天气和游客密度叠加后的生态走向。',
    prompt: '围绕一项滨海湿地修复计划进行生态推演：请综合考虑极端天气、游客增长和污染治理预算波动，分析不同主体互动后生态网络的演化趋势。'
  },
  {
    type: 'River',
    title: '流域协同治理',
    desc: '观察上游排污、工业调整和公共传播如何共同影响系统。',
    prompt: '针对流域协同治理场景，模拟上游排污反弹、地方产业转型和环保宣传同步发生时，不同参与者关系与环境指标会怎样变化。'
  },
  {
    type: 'Coastline',
    title: '海岸带风险联动',
    desc: '把产业、灾害和资源调度放进同一张生态沙盘。',
    prompt: '建立一个海岸带生态推演场景，加入风暴潮预警、港口扩容和渔业资源恢复计划三个变量，预测系统稳定性与利益博弈的变化。'
  }
]
const launchModes = [
  { value: 'document', label: '文档模式' },
  { value: 'map', label: '地图模式' }
]
const mapIntroCards = [
  { title: '空间锚点', desc: '点一下地图，系统就围绕这个位置自动展开。' },
  { title: '生态底图', desc: '优先拉取地表覆盖、气象、保护地和水系要素。' },
  { title: '代理节点', desc: '人类主体由 LLM 结合空间事实做中粒度推断。' }
]
const mapOutputFormats = ['实景图谱', '纯图谱', '环境基线', '风险对象']
const workflowSteps = [
  { id: '01', title: '图谱构建', desc: '把现实材料拆成实体、关系与时序记忆，为后续生态推演建立骨架。' },
  { id: '02', title: '环境搭建', desc: '抽取角色、场景与资源约束，把变量真正注入环境。' },
  { id: '03', title: '开始模拟', desc: '按轮次推进系统演化，持续记录冲突、扩散和反馈。' },
  { id: '04', title: '报告生成', desc: '自动归纳演化路径、关键拐点和可操作建议。' },
  { id: '05', title: '深度互动', desc: '继续和报告智能体或模拟角色对话，追问细节。' }
]
const launchPoints = [
  { title: '材料先行', desc: '把原始材料上传干净，后续图谱质量会明显更稳。' },
  { title: '目标可验证', desc: '提示词尽量写出对象、变量、时间窗和判定指标。' },
  { title: '保持原入口', desc: '首页完成采集后仍进入现有流程页，不另起一套概念。' }
]

const formData = ref({
  simulationRequirement: ''
})
const launchMode = ref('document')
const files = ref([])
const loading = ref(false)
const isDragOver = ref(false)
const fileInput = ref(null)

const canSubmit = computed(() => {
  return formData.value.simulationRequirement.trim() !== '' && files.value.length > 0
})

const selectedFileSummary = computed(() => {
  if (files.value.length === 0) {
    return '尚未附加材料'
  }

  if (files.value.length === 1) {
    return `已附加 1 份材料`
  }

  return `已附加 ${files.value.length} 份材料`
})

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const scrollToComposer = () => {
  document.getElementById('launch-composer')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const scrollToHistory = () => {
  document.getElementById('history-records')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click()
  }
}

const handleFileSelect = (event) => {
  addFiles(Array.from(event.target.files || []))
}

const handleDragOver = () => {
  if (!loading.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (event) => {
  isDragOver.value = false
  if (!loading.value) {
    addFiles(Array.from(event.dataTransfer.files || []))
  }
}

const addFiles = (newFiles) => {
  const allowedExtensions = ['pdf', 'md', 'txt']
  const existingKeys = new Set(
    files.value.map((file) => `${file.name}-${file.size}-${file.lastModified}`)
  )

  const validFiles = newFiles.filter((file) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    const fileKey = `${file.name}-${file.size}-${file.lastModified}`
    return allowedExtensions.includes(ext) && !existingKeys.has(fileKey)
  })

  files.value.push(...validFiles)
}

const removeFile = (index) => {
  files.value.splice(index, 1)
}

const applyPrompt = (prompt) => {
  formData.value.simulationRequirement = prompt
  scrollToComposer()
}

const openMapWorkspace = () => {
  router.push({
    name: 'MapSeed'
  })
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const startSimulation = () => {
  if (!canSubmit.value || loading.value) return

  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement)
    router.push({
      name: 'Process',
      params: { projectId: 'new' }
    })
  })
}
</script>

<style scoped>
:global(body) {
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(191, 214, 167, 0.48), transparent 34%),
    radial-gradient(circle at right 20%, rgba(217, 176, 120, 0.26), transparent 30%),
    linear-gradient(180deg, #f7f4ea 0%, #efe9da 48%, #f5efe2 100%);
  color: #153126;
}

:global(html) {
  scroll-behavior: smooth;
}

.env-home {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  color: #173126;
  font-family: 'IBM Plex Sans', 'Noto Sans SC', sans-serif;
}

.ambient {
  position: absolute;
  border-radius: 999px;
  filter: blur(20px);
  opacity: 0.8;
  pointer-events: none;
}

.ambient-a {
  top: -8rem;
  left: -4rem;
  width: 20rem;
  height: 20rem;
  background: rgba(153, 193, 118, 0.38);
  animation: driftA 12s ease-in-out infinite;
}

.ambient-b {
  top: 16rem;
  right: -6rem;
  width: 24rem;
  height: 24rem;
  background: rgba(41, 108, 77, 0.16);
  animation: driftB 15s ease-in-out infinite;
}

.ambient-c {
  bottom: 14rem;
  left: 24%;
  width: 18rem;
  height: 18rem;
  background: rgba(230, 193, 113, 0.22);
  animation: driftC 18s ease-in-out infinite;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.35rem 2rem;
  backdrop-filter: blur(18px);
  background: rgba(247, 244, 234, 0.76);
  border-bottom: 1px solid rgba(35, 74, 54, 0.1);
}

.brand-lockup {
  display: inline-flex;
  align-items: center;
  gap: 0.9rem;
  padding: 0;
  background: transparent;
  border: 0;
  color: inherit;
  cursor: pointer;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  border-radius: 1rem;
  background: linear-gradient(135deg, #1f5d45, #7faa5d);
  color: #f6f4eb;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  box-shadow: 0 1rem 2rem rgba(31, 93, 69, 0.16);
}

.brand-copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.brand-copy strong {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 1rem;
  letter-spacing: 0.22em;
}

.brand-copy small {
  font-size: 0.82rem;
  color: rgba(23, 49, 38, 0.68);
}

.topbar-links {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.ghost-link,
.repo-link,
.primary-cta,
.secondary-cta,
.prompt-card,
.remove-file {
  font: inherit;
}

.ghost-link,
.repo-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.7rem;
  padding: 0 1rem;
  border-radius: 999px;
  border: 1px solid rgba(23, 49, 38, 0.12);
  background: rgba(255, 255, 255, 0.55);
  color: inherit;
  text-decoration: none;
  cursor: pointer;
  transition: transform 0.24s ease, border-color 0.24s ease, box-shadow 0.24s ease;
}

.ghost-link:hover,
.repo-link:hover,
.primary-cta:hover,
.secondary-cta:hover,
.prompt-card:hover,
.workflow-card:hover,
.metric-card:hover,
.launch-point:hover,
.stream-card:hover {
  transform: translateY(-2px);
}

.page-shell {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 4rem;
  max-width: 1320px;
  margin: 0 auto;
  padding: 3.5rem 2rem 5rem;
}

.hero-grid,
.launch-section {
  display: grid;
  grid-template-columns: minmax(0, 1.06fr) minmax(0, 0.94fr);
  gap: 2rem;
  align-items: stretch;
}

.eyebrow-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  align-items: center;
  margin-bottom: 1.4rem;
}

.eyebrow-pill,
.section-kicker,
.console-label,
.console-meta,
.prompt-type,
.workflow-id,
.stage-ribbon,
.stage-status {
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eyebrow-pill {
  padding: 0.4rem 0.8rem;
  border-radius: 999px;
  background: #1f5d45;
  color: #f7f4ea;
  font-size: 0.76rem;
}

.eyebrow-note {
  color: rgba(23, 49, 38, 0.65);
  font-size: 0.92rem;
}

.hero-title,
.section-copy h2,
.stage-header h2,
.console-header h3 {
  font-family: 'Fraunces', 'Noto Serif SC', serif;
}

.hero-title {
  max-width: 12ch;
  margin: 0;
  font-size: clamp(3.2rem, 6vw, 5.8rem);
  line-height: 0.96;
  letter-spacing: -0.04em;
  color: #11281f;
}

.hero-lead,
.section-copy p,
.metric-note,
.workflow-card p,
.launch-point p,
.stream-card p,
.signal-item p,
.upload-placeholder p {
  color: rgba(23, 49, 38, 0.74);
  line-height: 1.72;
}

.hero-lead {
  max-width: 40rem;
  margin: 1.5rem 0 0;
  font-size: 1.08rem;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-top: 2rem;
}

.primary-cta,
.secondary-cta {
  min-height: 3.25rem;
  padding: 0 1.4rem;
  border-radius: 999px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: transform 0.24s ease, box-shadow 0.24s ease, background 0.24s ease;
}

.primary-cta {
  background: linear-gradient(135deg, #1f5d45, #82a95f);
  color: #f7f4ea;
  box-shadow: 0 1rem 1.8rem rgba(31, 93, 69, 0.2);
}

.secondary-cta {
  background: rgba(255, 255, 255, 0.52);
  border-color: rgba(23, 49, 38, 0.12);
  color: #173126;
}

.metric-grid,
.prompt-grid,
.workflow-grid,
.launch-points {
  display: grid;
  gap: 1rem;
}

.metric-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 2rem;
}

.metric-card,
.workflow-card,
.launch-point,
.console-card,
.stage-card,
.signal-card,
.prompt-card {
  border: 1px solid rgba(23, 49, 38, 0.1);
  background: rgba(252, 249, 241, 0.8);
  box-shadow: 0 1.2rem 2.8rem rgba(31, 50, 40, 0.08);
}

.metric-card {
  display: grid;
  gap: 0.55rem;
  padding: 1.15rem;
  border-radius: 1.25rem;
}

.metric-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.78rem;
  color: rgba(23, 49, 38, 0.5);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.metric-value {
  font-size: 1.2rem;
}

.hero-stage {
  position: relative;
}

.stage-frame {
  position: relative;
  height: 100%;
  padding: 1.8rem;
  border-radius: 2rem;
  background:
    linear-gradient(145deg, rgba(255, 252, 246, 0.72), rgba(228, 235, 220, 0.44)),
    linear-gradient(180deg, rgba(31, 93, 69, 0.06), rgba(217, 176, 120, 0.05));
  border: 1px solid rgba(31, 93, 69, 0.14);
  overflow: hidden;
}

.stage-frame::before,
.stage-frame::after {
  content: '';
  position: absolute;
  border-radius: 999px;
  pointer-events: none;
}

.stage-frame::before {
  inset: 1rem auto auto 55%;
  width: 12rem;
  height: 12rem;
  background: radial-gradient(circle, rgba(217, 176, 120, 0.32), transparent 65%);
}

.stage-frame::after {
  right: -2rem;
  bottom: -3rem;
  width: 14rem;
  height: 14rem;
  background: radial-gradient(circle, rgba(130, 169, 95, 0.32), transparent 65%);
}

.stage-ribbon {
  display: inline-flex;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  background: rgba(23, 49, 38, 0.08);
  color: rgba(23, 49, 38, 0.68);
  font-size: 0.75rem;
}

.stage-card {
  position: relative;
  margin-top: 1rem;
  padding: 1.4rem;
  border-radius: 1.7rem;
}

.stage-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.stage-label {
  margin: 0 0 0.4rem;
  color: rgba(23, 49, 38, 0.55);
  font-size: 0.9rem;
}

.stage-header h2 {
  margin: 0;
  font-size: 2rem;
  line-height: 1.1;
}

.stage-status {
  display: inline-flex;
  padding: 0.45rem 0.7rem;
  border-radius: 999px;
  background: rgba(128, 167, 94, 0.18);
  color: #1f5d45;
  font-size: 0.74rem;
}

.stage-stream {
  display: grid;
  gap: 0.9rem;
  margin-top: 1.4rem;
}

.stream-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.9rem;
  align-items: flex-start;
  padding: 1rem;
  border-radius: 1.15rem;
  background: rgba(255, 255, 255, 0.54);
  border: 1px solid rgba(23, 49, 38, 0.08);
  transition: transform 0.24s ease, border-color 0.24s ease;
}

.stream-index {
  display: grid;
  place-items: center;
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 999px;
  background: #173126;
  color: #f7f4ea;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.82rem;
}

.stream-card h3,
.signal-item strong,
.prompt-card strong,
.workflow-card h3,
.launch-point strong,
.console-header h3 {
  margin: 0;
}

.stream-card p,
.signal-item p,
.prompt-card p,
.workflow-card p,
.launch-point p {
  margin: 0.35rem 0 0;
  font-size: 0.95rem;
}

.signal-card {
  position: relative;
  margin-top: 1rem;
  padding: 1.2rem;
  border-radius: 1.4rem;
}

.signal-header,
.composer-footer {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
}

.signal-header {
  margin-bottom: 0.95rem;
  font-size: 0.9rem;
  color: rgba(23, 49, 38, 0.65);
}

.signal-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.8rem;
}

.signal-item {
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.56);
  border: 1px solid rgba(23, 49, 38, 0.08);
}

.section-copy {
  display: grid;
  gap: 0.85rem;
  align-content: start;
}

.section-kicker {
  font-size: 0.78rem;
  color: rgba(23, 49, 38, 0.56);
}

.section-copy h2 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 1.03;
}

.prompt-band,
.workflow-section,
.history-section {
  display: grid;
  gap: 1.6rem;
}

.prompt-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.prompt-card {
  display: grid;
  gap: 0.8rem;
  padding: 1.3rem;
  text-align: left;
  border-radius: 1.3rem;
  cursor: pointer;
  transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease;
}

.prompt-card:hover,
.workflow-card:hover,
.metric-card:hover,
.launch-point:hover,
.stream-card:hover {
  border-color: rgba(31, 93, 69, 0.18);
}

.prompt-type {
  color: #1f5d45;
  font-size: 0.74rem;
}

.workflow-grid {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.workflow-card {
  padding: 1.25rem;
  border-radius: 1.3rem;
  transition: transform 0.24s ease, border-color 0.24s ease;
}

.workflow-id {
  display: inline-flex;
  margin-bottom: 0.9rem;
  color: rgba(23, 49, 38, 0.45);
  font-size: 0.76rem;
}

.launch-points {
  margin-top: 1rem;
}

.mode-switch {
  display: inline-flex;
  gap: 0.4rem;
  margin-top: 1rem;
  padding: 0.25rem;
  border-radius: 999px;
  background: rgba(23, 49, 38, 0.06);
}

.mode-switch-btn {
  min-height: 2.5rem;
  padding: 0 1rem;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: rgba(23, 49, 38, 0.7);
  cursor: pointer;
  transition: background 0.24s ease, color 0.24s ease, transform 0.24s ease;
}

.mode-switch-btn.active {
  background: #fff;
  color: #173126;
  box-shadow: 0 0.7rem 1.5rem rgba(23, 49, 38, 0.08);
}

.launch-point {
  padding: 1rem 1.15rem;
  border-radius: 1.2rem;
}

.launch-console {
  display: grid;
  gap: 1rem;
}

.map-console-card {
  min-height: 21rem;
}

.map-intro {
  margin-top: 1rem;
  display: grid;
  gap: 1rem;
}

.map-intro p,
.map-output-note {
  color: rgba(23, 49, 38, 0.74);
  line-height: 1.7;
}

.map-intro-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.map-intro-card {
  padding: 0.95rem;
  border-radius: 1rem;
  background: rgba(23, 49, 38, 0.04);
}

.map-intro-card strong {
  display: block;
  margin-bottom: 0.35rem;
}

.map-output-row {
  margin-top: 1rem;
}

.console-card {
  padding: 1.35rem;
  border-radius: 1.5rem;
}

.console-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.console-label,
.console-meta {
  font-size: 0.74rem;
  color: rgba(23, 49, 38, 0.55);
}

.console-header h3 {
  margin-top: 0.35rem;
  font-size: 1.65rem;
}

.upload-zone {
  margin-top: 1.1rem;
  min-height: 16rem;
  padding: 1rem;
  border: 1px dashed rgba(23, 49, 38, 0.24);
  border-radius: 1.4rem;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.52), rgba(238, 242, 231, 0.54));
  transition: border-color 0.24s ease, background 0.24s ease, transform 0.24s ease;
  cursor: pointer;
}

.upload-zone.drag-over {
  border-color: rgba(31, 93, 69, 0.5);
  background: linear-gradient(180deg, rgba(247, 253, 242, 0.82), rgba(225, 238, 212, 0.72));
}

.upload-zone.has-files {
  min-height: auto;
}

.hidden-input {
  display: none;
}

.upload-placeholder {
  display: grid;
  place-items: center;
  gap: 0.6rem;
  height: 100%;
  padding: 2.5rem 1rem;
  text-align: center;
}

.upload-glyph {
  display: grid;
  place-items: center;
  width: 4rem;
  height: 4rem;
  border-radius: 1.4rem;
  background: rgba(31, 93, 69, 0.12);
  color: #1f5d45;
  font-size: 2rem;
}

.file-stack {
  display: grid;
  gap: 0.75rem;
}

.file-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.95rem 1rem;
  border-radius: 1.1rem;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(23, 49, 38, 0.08);
}

.file-chip-copy {
  display: grid;
  gap: 0.25rem;
  min-width: 0;
}

.file-chip-copy strong,
.file-chip-copy span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-chip-copy span {
  color: rgba(23, 49, 38, 0.56);
  font-size: 0.88rem;
}

.remove-file {
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 999px;
  border: 0;
  background: rgba(23, 49, 38, 0.08);
  color: #173126;
  cursor: pointer;
}

.format-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 1rem;
}

.format-pill {
  padding: 0.4rem 0.7rem;
  border-radius: 999px;
  background: rgba(23, 49, 38, 0.08);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.78rem;
  color: rgba(23, 49, 38, 0.7);
}

.brief-input {
  width: 100%;
  min-height: 15rem;
  margin-top: 1.1rem;
  padding: 1rem 1.1rem;
  border-radius: 1.4rem;
  border: 1px solid rgba(23, 49, 38, 0.14);
  background: rgba(255, 255, 255, 0.64);
  color: #173126;
  font: inherit;
  line-height: 1.7;
  resize: vertical;
}

.brief-input:focus-visible {
  outline: 2px solid rgba(31, 93, 69, 0.26);
  outline-offset: 3px;
}

.composer-footer {
  margin-top: 1rem;
}

.engine-note {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
  color: rgba(23, 49, 38, 0.66);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.82rem;
}

.engine-pulse {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 999px;
  background: #82a95f;
  box-shadow: 0 0 0 0 rgba(130, 169, 95, 0.46);
  animation: pulse 1.8s infinite;
}

.launch-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  transform: none;
  box-shadow: none;
}

.history-copy {
  max-width: 46rem;
}

@keyframes driftA {
  0%, 100% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(2rem, 1rem, 0); }
}

@keyframes driftB {
  0%, 100% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(-2.5rem, 1.8rem, 0); }
}

@keyframes driftC {
  0%, 100% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(1rem, -1.5rem, 0); }
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(130, 169, 95, 0.46);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(130, 169, 95, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(130, 169, 95, 0);
  }
}

@media (max-width: 1120px) {
  .hero-grid,
  .launch-section,
  .workflow-grid,
  .prompt-grid,
  .metric-grid,
  .signal-grid,
  .map-intro-grid {
    grid-template-columns: 1fr;
  }

  .workflow-grid {
    gap: 1rem;
  }

  .page-shell {
    gap: 3rem;
  }

  .hero-title {
    max-width: none;
  }
}

@media (max-width: 720px) {
  .topbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .topbar-links,
  .hero-actions,
  .composer-footer {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .mode-switch {
    width: 100%;
    flex-direction: column;
  }

  .page-shell {
    padding: 2.4rem 1rem 4rem;
  }

  .brand-copy strong {
    letter-spacing: 0.12em;
  }

  .stage-frame,
  .console-card,
  .workflow-card,
  .metric-card,
  .prompt-card,
  .launch-point {
    border-radius: 1.15rem;
  }

  .stage-header,
  .console-header,
  .signal-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
