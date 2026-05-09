<template>
  <div class="page-container">
    <!-- Page header -->
    <div v-if="!embedded" class="page-header">
      <div class="page-header-info">
        <h2 class="page-title">上传中心</h2>
        <p class="page-desc">上传财务数据文件，系统将自动解析并创建处理任务</p>
      </div>
    </div>

    <!-- Naming rules info -->
    <el-card shadow="never" class="info-card">
      <div class="rules-content">
        <div class="rules-header">
          <el-icon :size="18" color="var(--primary)"><InfoFilled /></el-icon>
          <span class="rules-title">文件命名规则</span>
        </div>
        <div class="rules-body">
          <div class="rule-row">
            <span class="rule-label">命名格式：</span>
            <code class="rule-code">{YY年MM月或YYYY年MM月}_{性质}_{店铺名称}.xlsx/.xlsm/.csv</code>
          </div>
          <div class="rule-row">
            <span class="rule-label">性质类型：</span>
            <div class="rule-tags">
              <el-tag
                v-for="type in supportedFileTypes"
                :key="type"
                size="small"
                :type="typeTagMap[type] || ''"
              >
                {{ fileTypeLabel(type) }}
              </el-tag>
            </div>
          </div>
          <div class="rule-row rule-row--full">
            <span class="rule-label">平台规则：</span>
            <div class="platform-rule-list">
              <div
                v-for="rule in platformUploadRules"
                :key="rule.platformCode"
                class="platform-rule-item"
              >
                <div class="platform-rule-main">
                  <el-tag size="small" :class="getPlatformTagClass(rule.platformCode)">
                    {{ rule.platform }}
                  </el-tag>
                  <div class="type-list">
                    <el-tag
                      v-for="type in rule.types"
                      :key="type"
                      size="small"
                      :type="typeTagMap[type] || ''"
                    >
                      {{ fileTypeLabel(type) }}
                    </el-tag>
                  </div>
                </div>
                <div class="example-list">
                  <code v-for="example in rule.examples" :key="example">{{ example }}</code>
                </div>
              </div>
            </div>
          </div>
          <div class="rule-row">
            <span class="rule-label">兼容规则：</span>
            <span>年份支持 26年 或 2026年；月份支持 2月 或 02月；GMV/BIC 不区分大小写，如 gmv、GMV、bic、BIC。</span>
          </div>
          <div class="rule-row">
            <span class="rule-label">检查规则：</span>
            <span>先按文件名识别年月、性质和店铺，再读取文件前 20 行非空内容匹配接口表头；表头顺序不同也可以通过，字段缺失或多余会阻止上传。</span>
          </div>
        </div>
      </div>
    </el-card>

    <el-card v-if="userStore.isSuperAdmin" shadow="never" class="target-org-card">
      <el-form inline>
        <el-form-item label="上传到组织">
          <el-select
            v-model="targetOrgId"
            placeholder="请选择组织"
            filterable
            style="width: 260px"
            :loading="orgLoading"
          >
            <el-option
              v-for="org in orgOptions"
              :key="org.id"
              :label="org.name"
              :value="org.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Upload drop zone -->
    <el-card shadow="never" class="upload-card">
      <div
        class="drop-zone"
        :class="{ 'drop-zone--active': isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInputRef"
          type="file"
          multiple
          accept=".xlsx,.xlsm,.csv"
          style="display: none"
          @change="handleFileInputChange"
        />
        <div class="drop-zone-content">
          <el-icon :size="48" class="drop-zone-icon"><Upload /></el-icon>
          <p class="drop-zone-text">
            {{ isReadingHeaders ? '正在读取文件表头...' : '拖拽文件到此处，或' }}
            <em v-if="!isReadingHeaders">点击选择文件</em>
          </p>
          <p class="drop-zone-hint">支持 .xlsx / .xlsm / .csv 格式，单文件最大 1024MB</p>
        </div>
      </div>
    </el-card>

    <!-- File list -->
    <el-card v-if="fileItems.length > 0" shadow="never" class="file-list-card">
      <template #header>
        <div class="card-header">
          <span class="card-header-title">
            已选择文件 ({{ fileItems.length }})
          </span>
          <div class="card-header-actions">
            <el-button
              type="primary"
              :loading="isUploading"
              :disabled="!canUpload"
              @click="startUpload"
            >
              <el-icon><Upload /></el-icon>
              {{ isUploading ? '上传中...' : '开始上传' }}
            </el-button>
            <el-button @click="clearAll" :disabled="isUploading">
              <el-icon><Delete /></el-icon> 清空
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="fileItems" stripe border style="width: 100%">
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column prop="name" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column label="年月" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.meta" type="info" size="small">
              {{ row.meta.year }}-{{ String(row.meta.month).padStart(2, '0') }}
            </el-tag>
            <span v-else class="text-error">解析失败</span>
          </template>
        </el-table-column>
        <el-table-column label="识别店铺名称" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.meta?.shop">{{ row.meta.shop }}</span>
            <span v-else class="text-error">解析失败</span>
          </template>
        </el-table-column>
        <el-table-column label="性质" width="90" align="center">
          <template #default="{ row }">
            <template v-if="row.meta">
              <el-tag
                size="small"
                :type="typeTagMap[row.meta.type] || ''"
              >
                {{ fileTypeLabel(row.meta.type) }}
              </el-tag>
            </template>
            <span v-else class="text-error">-</span>
          </template>
        </el-table-column>
        <el-table-column label="平台识别" width="150" align="center">
          <template #default="{ row }">
            <el-tooltip
              v-if="row.headerMatch"
              :content="row.headerMatch.message"
              placement="top"
            >
              <el-tag
                :type="row.headerMatch.status === 'matched' ? '' : headerMatchTagType(row.headerMatch.status)"
                :class="platformMatchTagClass(row)"
                size="small"
              >
                {{ platformMatchLabel(row) }}
              </el-tag>
            </el-tooltip>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="检查结果" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <span :class="row.headerMatch.status === 'matched' ? 'text-success' : 'text-error'">
              {{ validationMessage(row) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-tag size="small">等待上传</el-tag>
            </template>
            <template v-else-if="row.status === 'uploading'">
              <el-tag type="warning" size="small">上传中</el-tag>
            </template>
            <template v-else-if="row.status === 'success'">
              <el-tag type="success" size="small">已完成</el-tag>
            </template>
            <template v-else-if="row.status === 'error'">
              <el-tag type="danger" size="small">失败</el-tag>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="160">
          <template #default="{ row }">
            <el-progress
              v-if="row.status === 'uploading' || row.status === 'success'"
              :percentage="row.progress"
              :status="row.status === 'success' ? 'success' : ''"
              :stroke-width="8"
            />
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ $index }">
            <el-button
              type="danger"
              link
              :disabled="isUploading"
              @click="removeFile($index)"
            >
              移除
            </el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无文件" :image-size="60" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="uploadCompleteDialogVisible"
      title="上传完成"
      width="420px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
      :close-on-press-escape="false"
    >
      <div class="upload-complete-dialog">
        <el-icon class="upload-complete-icon"><CircleCheckFilled /></el-icon>
        <div>
          <p class="upload-complete-title">成功上传 {{ uploadCompleteCount }} 个文件</p>
          <p class="upload-complete-desc">系统已创建处理任务，可以继续上传或前往任务列表查看进度。</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="handleContinueUpload">继续上传</el-button>
        <el-button type="primary" @click="goTaskList">查看任务列表</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { CircleCheckFilled, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus/es/components/message/index.mjs'
import { getPlatformTagClass, parseFileName, type ParsedFileName } from '@/utils/format'
import { getFileSpecs, type FileSpec } from '@/api/file_spec'
import { createBatch, getOssSts, uploadCallback, type OssStsCredential } from '@/api/upload'
import { getOrganizationList, type Organization } from '@/api/organization'
import { useUserStore } from '@/stores/user'

const props = withDefaults(defineProps<{
  embedded?: boolean
}>(), {
  embedded: false,
})

const emit = defineEmits<{
  uploaded: [count: number]
  viewTasks: []
  continueUpload: []
}>()

interface FileItem {
  file: File
  name: string
  meta: ParsedFileName | null
  matchedRule: FileSpec | null
  headers: string[]
  headerRowIndex: number | null
  headerMatch: HeaderMatchInfo
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number
  error?: string
}

type HeaderMatchStatus = 'matched' | 'mismatch' | 'no_spec' | 'read_failed' | 'filename_failed'

interface HeaderMatchInfo {
  status: HeaderMatchStatus
  message: string
  matchedCount: number
  expectedCount: number
  headerRowIndex: number | null
}

interface HeaderMatchResult {
  spec: FileSpec | null
  headers: string[]
  info: HeaderMatchInfo
}

const typeTagMap: Record<string, string> = {
  '动账': '',
  'gmv': 'primary',
  'GMV': 'primary',
  'bic': 'success',
  'BIC': 'success',
  '运费险': 'warning',
  '订单': 'info',
  '其他服务款': 'warning',
}

const supportedFileTypes = ['动账', 'gmv', 'bic', '运费险', '订单', '其他服务款']

const platformUploadRules = [
  {
    platform: '抖音',
    platformCode: 'douyin',
    types: ['动账', 'bic', '运费险'],
    examples: [
      '26年02月_动账_抖音旗舰店.xlsx',
      '26年2月_BIC_抖音旗舰店.xlsx',
      '26年02月_运费险_抖音旗舰店.xlsx',
    ],
  },
  {
    platform: '快手',
    platformCode: 'kuaishou',
    types: ['gmv', '动账', '运费险', '订单'],
    examples: [
      '26年02月_动账_快手专营店.xlsx',
      '2026年2月_gmv_快手专营店.csv',
      '26年02月_订单_快手专营店.xlsx',
      '26年02月_运费险_快手专营店.csv',
    ],
  },
  {
    platform: '小红书',
    platformCode: 'xiaohongshu',
    types: ['gmv', '其他服务款', '动账'],
    examples: [
      '26年02月_动账_小红书店铺.xlsx',
      '2026年02月_GMV_小红书店铺.xlsx',
      '26年02月_其他服务款_小红书店铺.xlsx',
    ],
  },
  {
    platform: '微信小店',
    platformCode: 'weixin_video',
    types: ['订单', '动账', 'bic', '运费险'],
    examples: [
      '26年02月_动账_微信小店.xlsx',
      '26年02月_BIC_微信小店.xlsx',
      '26年02月_订单_微信小店.xlsx',
      '26年02月_运费险_微信小店.xlsx',
    ],
  },
]

function fileTypeLabel(type: string): string {
  if (type.toLowerCase() === 'gmv') return 'GMV'
  return type.toLowerCase() === 'bic' ? 'BIC' : type
}

function validationMessage(row: FileItem): string {
  if (!row.meta) {
    return '文件名不符合规则：请使用 26年02月 或 2026年02月_性质_店铺名称'
  }
  if (!row.meta.shop) {
    return '文件名缺少店铺名称'
  }
  if (row.headerMatch.status === 'matched') {
    return `检查通过：${row.headerMatch.message}`
  }
  return row.headerMatch.message
}

// State
const fileInputRef = ref<HTMLInputElement>()
const isDragging = ref(false)
const isUploading = ref(false)
const fileItems = ref<FileItem[]>([])
const fileSpecs = ref<FileSpec[]>([])
const userStore = useUserStore()
const router = useRouter()
const orgLoading = ref(false)
const orgOptions = ref<Organization[]>([])
const targetOrgId = ref<number | undefined>(undefined)
const isReadingHeaders = ref(false)
const uploadCompleteDialogVisible = ref(false)
const uploadCompleteCount = ref(0)
let xlsxModulePromise: Promise<typeof import('xlsx')> | null = null
let ossModulePromise: Promise<typeof import('ali-oss')> | null = null

const canUpload = computed(() => {
  return fileItems.value.length > 0 &&
    fileItems.value.every(f => f.meta !== null && f.matchedRule !== null && f.headerMatch.status === 'matched') &&
    (!userStore.isSuperAdmin || Boolean(targetOrgId.value)) &&
    !isUploading.value
})

// Load file specs on mount for platform auto-detection
async function loadFileSpecs() {
  try {
    fileSpecs.value = await getFileSpecs()
  } catch {
    // Silently fail - will show "待识别" for all
  }
}
loadFileSpecs()

async function loadOrgOptions() {
  if (!userStore.isSuperAdmin) return
  orgLoading.value = true
  try {
    const res = await getOrganizationList({ page: 1, page_size: 100 })
    orgOptions.value = (res.items || []).filter((org) => org.status === '1' || org.status === 1)
    if (!targetOrgId.value && orgOptions.value.length === 1) {
      targetOrgId.value = orgOptions.value[0].id
    }
  } catch {
    // Error handled by interceptor
  } finally {
    orgLoading.value = false
  }
}
loadOrgOptions()

async function ensureFileSpecsLoaded() {
  if (fileSpecs.value.length > 0) return
  await loadFileSpecs()
}

// File input trigger
function triggerFileInput() {
  fileInputRef.value?.click()
}

// Handle file input change
function handleFileInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    processFiles(Array.from(input.files))
    input.value = ''
  }
}

// Handle drag and drop
function handleDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files) {
    processFiles(Array.from(e.dataTransfer.files))
  }
}

// Process selected files
async function processFiles(files: File[]) {
  await ensureFileSpecsLoaded()
  isReadingHeaders.value = true

  try {
    for (const file of files) {
      // Validate file type
      if (!file.name.match(/\.(xlsx|xlsm|csv)$/i)) {
        ElMessage.warning(`文件 ${file.name} 不是 Excel/CSV 文件，已跳过`)
        continue
      }

      // Check duplicate
      if (fileItems.value.some(f => f.name === file.name)) {
        ElMessage.warning(`文件 ${file.name} 已存在，已跳过`)
        continue
      }

      // Parse filename
      const meta = parseFileName(file.name)
      if (!meta) {
        ElMessage.warning(`文件 ${file.name} 命名不符合规则：支持 26年/2026年，GMV/BIC 不区分大小写`)
      }

      let headers: string[] = []
      let matchedRule: FileSpec | null = null
      let headerMatch: HeaderMatchInfo = {
        status: 'filename_failed',
        message: '文件名解析失败，格式示例：2026年02月_BIC_店铺名.xlsx、26年02月_其他服务款_店铺名.csv',
        matchedCount: 0,
        expectedCount: 0,
        headerRowIndex: null,
      }

      if (meta && fileSpecs.value.length > 0) {
        try {
          const headerRows = await readTabularHeaderRows(file)
          const matchResult = matchPlatformByHeaderRows(headerRows, meta.type)
          matchedRule = matchResult.spec
          headers = matchResult.headers
          headerMatch = matchResult.info
        } catch (err: any) {
          headerMatch = {
            status: 'read_failed',
            message: err?.message || '读取文件表头失败',
            matchedCount: 0,
            expectedCount: 0,
            headerRowIndex: null,
          }
        }
      } else if (meta) {
        headerMatch = {
          status: 'no_spec',
          message: '未获取到接口表头规格，无法识别平台',
          matchedCount: 0,
          expectedCount: 0,
          headerRowIndex: null,
        }
      }

      fileItems.value.push({
        file,
        name: file.name,
        meta,
        matchedRule,
        headers,
        headerRowIndex: headerMatch.headerRowIndex,
        headerMatch,
        status: 'pending',
        progress: 0,
      })
    }
  } finally {
    isReadingHeaders.value = false
  }
}

// Read the first non-empty rows using SheetJS. Some platform exports place notes
// above the real header, so matching chooses the best header row below.
async function readTabularHeaderRows(file: File): Promise<string[][]> {
  const XLSX = await loadXlsx()
  const isCsv = file.name.toLowerCase().endsWith('.csv')
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = e.target?.result
        if (!data) {
          resolve([])
          return
        }
        const wb = isCsv
          ? XLSX.read(decodeCsvBuffer(data as ArrayBuffer), { type: 'string', raw: true })
          : XLSX.read(data, { type: 'array' })
        const ws = wb.Sheets[wb.SheetNames[0]]
        const rows = XLSX.utils.sheet_to_json<string[]>(ws, { header: 1, blankrows: false })
        const headerRows = rows
          .slice(0, 20)
          .map((row) => row.map((cell) => String(cell || '').trim()))
          .filter((row) => row.some(Boolean))
        resolve(headerRows)
      } catch (err) {
        reject(err)
      }
    }
    reader.onerror = reject
    reader.readAsArrayBuffer(file)
  })
}

function decodeCsvBuffer(buffer: ArrayBuffer): string {
  const encodings = ['utf-8', 'gb18030']
  for (const encoding of encodings) {
    try {
      return new TextDecoder(encoding, { fatal: true }).decode(buffer)
    } catch {
      // Try the next common CSV export encoding.
    }
  }
  return new TextDecoder('utf-8').decode(buffer)
}

function loadXlsx() {
  if (!xlsxModulePromise) {
    xlsxModulePromise = import('xlsx')
  }
  return xlsxModulePromise
}

function matchPlatformByHeaderRows(headerRows: string[][], type: string): HeaderMatchResult {
  const typedCandidates = fileSpecs.value.filter(
    (r) => r.type_code.toLowerCase() === type.toLowerCase(),
  )

  if (typedCandidates.length === 0) {
    return {
      spec: null,
      info: {
        status: 'no_spec',
        message: `接口未配置「${type}」类型的表头规格`,
        matchedCount: 0,
        expectedCount: 0,
        headerRowIndex: null,
      },
      headers: [],
    }
  }

  for (const [rowIndex, headers] of headerRows.entries()) {
    const actualHeaders = normalizeHeaders(headers)
    for (const spec of typedCandidates) {
      const expectedHeaders = normalizeHeaders(spec.headers || [])
      if (isSameHeaderSet(actualHeaders, expectedHeaders)) {
        return {
          spec,
          headers,
          info: {
            status: 'matched',
            message: `表头一致，识别平台：${spec.platform_name || spec.platform_code}（已忽略列顺序）`,
            matchedCount: expectedHeaders.length,
            expectedCount: expectedHeaders.length,
            headerRowIndex: rowIndex + 1,
          },
        }
      }
    }
  }

  const closest = scoreClosest(typedCandidates, headerRows)
  return {
    spec: null,
    headers: closest?.headers || headerRows[0] || [],
    info: {
      status: 'mismatch',
      message: closest
        ? `表头不一致，最接近「${closest.spec.name}」：匹配 ${closest.matchedCount}/${closest.expectedCount} 个字段`
        : '表头不一致，未匹配到平台规格',
      matchedCount: closest?.matchedCount || 0,
      expectedCount: closest?.expectedCount || 0,
      headerRowIndex: closest ? closest.headerRowIndex + 1 : null,
    },
  }
}

function normalizeHeaders(headers: string[]): string[] {
  const normalized = headers
    .map(canonicalHeader)
    .filter(Boolean)

  return Array.from(new Set(normalized))
}

function canonicalHeader(header: string): string {
  return String(header || '')
    .trim()
    .replace(/[\s　\uFEFF\u200B-\u200D]+/g, '')
    .replace(/帐/g, '账')
    .replace(/（/g, '(')
    .replace(/）/g, ')')
    .toLowerCase()
}

function isSameHeaderSet(actual: string[], expected: string[]): boolean {
  if (actual.length !== expected.length) return false
  const actualSet = new Set(actual)
  return expected.every((h) => actualSet.has(h))
}

function scoreClosest(candidates: FileSpec[], headerRows: string[][]) {
  let best: {
    spec: FileSpec
    headers: string[]
    matchedCount: number
    expectedCount: number
    headerRowIndex: number
  } | null = null

  for (const [rowIndex, headers] of headerRows.entries()) {
    const actualHeaders = normalizeHeaders(headers)
    const actualSet = new Set(actualHeaders)

    for (const spec of candidates) {
      const expectedHeaders = normalizeHeaders(spec.headers || [])
      const matchedCount = expectedHeaders.filter((h) => actualSet.has(h)).length
      if (!best || matchedCount > best.matchedCount) {
        best = {
          spec,
          headers,
          matchedCount,
          expectedCount: expectedHeaders.length,
          headerRowIndex: rowIndex,
        }
      }
    }
  }

  return best
}

function headerMatchTagType(status: HeaderMatchStatus): string {
  const map: Record<HeaderMatchStatus, string> = {
    matched: 'success',
    mismatch: 'danger',
    no_spec: 'warning',
    read_failed: 'danger',
    filename_failed: 'danger',
  }
  return map[status]
}

function platformMatchLabel(row: FileItem): string {
  if (row.headerMatch.status === 'matched' && row.matchedRule) {
    return row.matchedRule.platform_name || row.matchedRule.platform_code
  }
  const map: Record<HeaderMatchStatus, string> = {
    matched: '已识别',
    mismatch: '表头不一致',
    no_spec: '无规格',
    read_failed: '读取失败',
    filename_failed: '解析失败',
  }
  return map[row.headerMatch.status]
}

function platformMatchTagClass(row: FileItem): string {
  if (row.headerMatch.status !== 'matched' || !row.matchedRule) return ''
  return getPlatformTagClass(row.matchedRule.platform_code || row.matchedRule.platform_name)
}

function buildOssKey(sts: OssStsCredential, fileName: string): string {
  const safeName = fileName.replace(/[\\/]/g, '_')
  return `${sts.oss_key_prefix}${Date.now()}_${safeName}`
}

async function createOssClient(sts: OssStsCredential) {
  const OSS = await loadOss()
  return new OSS.default({
    region: sts.region,
    bucket: sts.bucket,
    endpoint: sts.endpoint,
    accessKeyId: sts.access_key_id,
    accessKeySecret: sts.access_key_secret,
    stsToken: sts.security_token,
    secure: sts.endpoint.startsWith('https://'),
  })
}

function loadOss() {
  if (!ossModulePromise) {
    ossModulePromise = import('ali-oss')
  }
  return ossModulePromise
}

// Remove a file from list
function removeFile(index: number) {
  fileItems.value.splice(index, 1)
}

// Clear all files
function clearAll() {
  fileItems.value = []
}

function showUploadCompleteDialog(successCount: number) {
  uploadCompleteCount.value = successCount
  uploadCompleteDialogVisible.value = true
  emit('uploaded', successCount)
}

function handleContinueUpload() {
  uploadCompleteDialogVisible.value = false
  clearAll()
  emit('continueUpload')
}

function goTaskList() {
  uploadCompleteDialogVisible.value = false
  if (props.embedded) {
    emit('viewTasks')
    return
  }
  router.push('/tasks')
}

// Start upload process
async function startUpload() {
  if (!canUpload.value) return

  isUploading.value = true

  try {
    // a. Create batch
    const batch = await createBatch({
      file_count: fileItems.value.length,
      org_id: userStore.isSuperAdmin ? targetOrgId.value : undefined,
    })
    const sts = await getOssSts(batch.id)
    const ossClient = await createOssClient(sts)

    // b. Upload each file
    for (const item of fileItems.value) {
      if (!item.meta) continue

      item.status = 'uploading'
      item.progress = 0

      try {
        const ossKey = buildOssKey(sts, item.file.name)

        await ossClient.put(ossKey, item.file, {
          progress: (percent: number) => {
            item.progress = Math.round(percent * 100)
          },
        })

        // Notify backend
        await uploadCallback({
          batch_id: batch.id,
          original_name: item.name,
          oss_key: ossKey,
          file_size: item.file.size,
          parsed_year: item.meta.year,
          parsed_month: item.meta.month,
          parsed_type: item.meta.type,
          parsed_shop: item.meta.shop,
          detected_platform: item.matchedRule?.platform_code || '',
        })

        item.status = 'success'
        item.progress = 100
      } catch (err: any) {
        item.status = 'error'
        item.error = err.message || '上传失败'
        ElMessage.error(`文件 ${item.name} 上传失败`)
      }
    }

    const successCount = fileItems.value.filter(f => f.status === 'success').length
    if (successCount > 0) {
      showUploadCompleteDialog(successCount)
    }
  } catch (err: any) {
    ElMessage.error('创建上传批次失败：' + (err.message || '未知错误'))
  } finally {
    isUploading.value = false
  }
}
</script>

<style scoped lang="scss">
.page-container {
  width: 100%;
}

.page-header {
  margin-bottom: 16px;

  .page-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  .page-desc {
    font-size: 13px;
    color: var(--text-tertiary);
  }
}

// Info card
.info-card {
  margin-bottom: 16px;

  :deep(.el-card__body) {
    padding: 16px;
  }

  .rules-content {
    .rules-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;

      .rules-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-primary);
      }
    }

    .rules-body {
      .rule-row {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        margin-bottom: 8px;
        font-size: 13px;
        color: var(--text-secondary);
        line-height: 1.8;

        &:last-child {
          margin-bottom: 0;
        }

        .rule-label {
          color: var(--text-tertiary);
          flex-shrink: 0;
          width: 80px;
          line-height: 26px;
        }

        .rule-code {
          background: var(--code-bg);
          padding: 2px 8px;
          border-radius: 4px;
          color: var(--code-text);
          font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
          font-size: 13px;
        }

        .rule-tags {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          min-width: 0;
        }

        .platform-rule-list {
          display: grid;
          grid-template-columns: 1fr;
          gap: 8px;
          min-width: 0;
          width: 100%;
        }

        .platform-rule-item {
          display: grid;
          grid-template-columns: 240px 1fr;
          gap: 10px;
          align-items: center;
          min-width: 0;
          padding: 8px 10px;
          border: 1px solid var(--border-light);
          border-radius: 6px;
          background: var(--bg-elevated);
        }

        .platform-rule-main {
          display: flex;
          align-items: center;
          gap: 8px;
          min-width: 0;
        }

        .type-list {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          min-width: 0;
        }

        .example-list {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          min-width: 0;

          code {
            background: var(--code-bg);
            border: 1px solid var(--border-light);
            border-radius: 4px;
            color: var(--code-text);
            font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
            font-size: 12px;
            line-height: 1.5;
            padding: 3px 8px;
            word-break: break-all;
          }
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .info-card {
    .rules-content {
      .rules-body {
        .rule-row {
          flex-direction: column;
          gap: 4px;

          .rule-label {
            width: auto;
          }

          .platform-rule-item {
            grid-template-columns: 1fr;
          }

          .platform-rule-main {
            align-items: flex-start;
            flex-direction: column;
          }
        }
      }
    }
  }
}

// Upload drop zone
.upload-card {
  margin-bottom: 16px;

  :deep(.el-card__body) {
    padding: 16px;
  }
}

.drop-zone {
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 30px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.12s, background-color 0.12s;
  background: var(--bg-card);

  &:hover {
    border-color: var(--primary);
    background: var(--primary-light);
  }

  &--active {
    border-color: var(--primary);
    background: var(--primary-light);
    border-style: solid;
  }

  .drop-zone-icon {
    color: var(--text-disabled);
    margin-bottom: 8px;
  }

  .drop-zone-text {
    font-size: 15px;
    color: var(--text-secondary);
    margin-bottom: 6px;

    em {
      color: var(--primary);
      font-style: normal;
      font-weight: 500;
    }
  }

  .drop-zone-hint {
    font-size: 12px;
    color: var(--text-tertiary);
  }
}

// File list card
.file-list-card {
  margin-bottom: 16px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    &-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
    }

    &-actions {
      display: flex;
      gap: 8px;
    }
  }
}

.upload-complete-dialog {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 4px 0;

  .upload-complete-icon {
    flex-shrink: 0;
    margin-top: 2px;
    color: var(--success);
    font-size: 34px;
  }

  .upload-complete-title {
    margin: 0 0 6px;
    color: var(--text-primary);
    font-size: 16px;
    font-weight: 600;
  }

  .upload-complete-desc {
    margin: 0;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.7;
  }
}

</style>
