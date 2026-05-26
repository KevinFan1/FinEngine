<template>
    <div class="page-container">
        <div
            class="upload-shell"
            :class="{ 'upload-shell--embedded': embedded }"
        >
            <section
                class="upload-rule-board"
                aria-label="文件命名规则和平台示例"
            >
                <div class="rule-board-main">
                    <div class="rule-heading">
                        <div>
                            <span class="section-kicker">NAMING RULE</span>
                            <h2>文件命名规则</h2>
                        </div>
                        <p>
                            {{
                                embedded
                                    ? "抽屉里保留核心规则，先命名再上传即可。"
                                    : "先按规则命名，系统会用文件名识别年月、性质和店铺。"
                            }}
                        </p>
                    </div>
                    <div class="rule-code-line" aria-label="标准文件命名格式">
                        <span class="rule-token rule-token--date"
                            >YY年MM月</span
                        >
                        <span class="rule-separator">_</span>
                        <span class="rule-token rule-token--type">性质</span>
                        <span class="rule-separator">_</span>
                        <span class="rule-token rule-token--shop"
                            >店铺名称</span
                        >
                        <span class="rule-extension">.xlsx / .xls / .csv</span>
                    </div>
                    <div class="rule-meta">
                        <p class="rule-example">
                            示例：<code>26年02月_动账_抖音旗舰店.xlsx</code>
                        </p>
                        <div class="rule-hint-list">
                            <span>年月支持 26年 或 2026年</span>
                            <span>月份支持 2月 或 02月</span>
                            <span>GMV / BIC 不区分大小写</span>
                        </div>
                    </div>
                </div>

                <div class="rule-platforms" aria-label="平台示例参考">
                    <div class="reference-heading rule-platforms-heading">
                        <div>
                            <span class="section-kicker">REFERENCE</span>
                            <h3>已接入平台与支持类型</h3>
                        </div>
                        <el-icon><InfoFilled /></el-icon>
                    </div>
                    <div class="platform-card-list">
                        <div
                            v-for="rule in visiblePlatformUploadRules"
                            :key="rule.platformCode"
                            class="platform-card"
                        >
                            <div class="platform-card-line">
                                <PlatformBadge
                                    :platform="rule.platformCode"
                                    show-mark
                                    size="default"
                                />
                                <div class="type-list">
                                    <FileTypeBadge
                                        v-for="type in rule.types"
                                        :key="type"
                                        :type="type"
                                    />
                                </div>
                            </div>
                            <p class="platform-example">
                                {{ rule.examples[0] }}
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            <div class="upload-main-grid">
                <section class="upload-workspace" aria-label="上传操作区">
                    <section class="upload-steps" aria-label="上传流程">
                        <div class="upload-step is-active">
                            <strong>1</strong>
                            <span>选择文件</span>
                        </div>
                        <div
                            class="upload-step"
                            :class="{
                                'is-active':
                                    fileItems.length > 0 || isReadingHeaders,
                            }"
                        >
                            <strong>2</strong>
                            <span>检查表头</span>
                        </div>
                        <div
                            class="upload-step"
                            :class="{ 'is-active': canUpload || isUploading }"
                        >
                            <strong>3</strong>
                            <span>提交任务</span>
                        </div>
                    </section>

                    <el-card
                        v-if="userStore.isSuperAdmin"
                        shadow="never"
                        class="target-org-card"
                    >
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

                    <el-card shadow="never" class="upload-card">
                        <div class="operation-heading">
                            <div>
                                <span class="section-kicker">STEP 01</span>
                                <h3>选择并预检财务文件</h3>
                            </div>
                            <span class="file-counter"
                                >{{ fileItems.length }} 个文件</span
                            >
                        </div>

                        <div
                            class="drop-zone"
                            :class="{
                                'drop-zone--active': isDragging,
                                'drop-zone--scanning': isReadingHeaders,
                            }"
                            @dragover.prevent="isDragging = true"
                            @dragleave.prevent="isDragging = false"
                            @drop.prevent="handleDrop"
                            @click="triggerFileInput"
                        >
                            <input
                                ref="fileInputRef"
                                type="file"
                                multiple
                                accept=".xlsx,.xlsm,.xls,.csv"
                                style="display: none"
                                @change="handleFileInputChange"
                            />
                            <div
                                v-if="isReadingHeaders"
                                class="scan-line"
                                aria-hidden="true"
                            ></div>
                            <div class="drop-zone-content">
                                <div
                                    class="upload-illustration"
                                    aria-hidden="true"
                                >
                                    <span
                                        class="file-layer file-layer--back"
                                    ></span>
                                    <span class="file-layer file-layer--front">
                                        <span></span>
                                        <span></span>
                                        <span></span>
                                    </span>
                                    <el-icon><Upload /></el-icon>
                                </div>
                                <p class="drop-zone-text">
                                    {{
                                        isReadingHeaders
                                            ? "正在扫描文件结构..."
                                            : "拖拽文件到此处"
                                    }}
                                    <em v-if="!isReadingHeaders">点击选择</em>
                                </p>
                                <p class="drop-zone-hint">
                                    支持 .xlsx / .xlsm / .xls / .csv，单文件最大
                                    1024MB，上传前会检查本月上传额度是否充足
                                </p>
                            </div>
                        </div>
                    </el-card>

                    <el-card
                        v-if="fileItems.length > 0 || isReadingHeaders"
                        shadow="never"
                        class="file-list-card"
                    >
                        <template #header>
                            <div class="card-header">
                                <div class="card-header-main">
                                    <div>
                                        <span class="section-kicker"
                                            >STEP 02</span
                                        >
                                        <span class="card-header-title"
                                            >确认识别结果</span
                                        >
                                    </div>
                                    <span
                                        v-if="queuePanelVisible"
                                        class="queue-state"
                                        :class="{
                                            'queue-state--running': isUploading,
                                        }"
                                    >
                                        {{
                                            isUploading ? "上传中" : "等待操作"
                                        }}
                                    </span>
                                </div>
                                <div class="card-header-actions">
                                    <el-button
                                        type="primary"
                                        :loading="isUploading"
                                        :disabled="!canUpload"
                                        @click="startUpload"
                                    >
                                        <el-icon><Upload /></el-icon>
                                        {{
                                            isUploading
                                                ? "上传中..."
                                                : "开始上传"
                                        }}
                                    </el-button>
                                    <el-button
                                        @click="clearAll"
                                        :disabled="
                                            isUploading ||
                                            fileItems.length === 0
                                        "
                                    >
                                        <el-icon><Delete /></el-icon> 清空
                                    </el-button>
                                    <el-button
                                        size="small"
                                        :disabled="
                                            isUploading ||
                                            !hasSelectedFiles
                                        "
                                        @click="clearSelectedFiles"
                                    >
                                        清空选中
                                        {{
                                            hasSelectedFiles
                                                ? `(${selectedFileRows.length})`
                                                : ""
                                        }}
                                    </el-button>
                                    <el-button
                                        v-if="failedReadyItems.length > 0"
                                        :disabled="isUploading"
                                        @click="retryFailedFiles"
                                    >
                                        重试失败
                                    </el-button>
                                    <el-button
                                        size="small"
                                        :disabled="
                                            isUploading ||
                                            uploadStats.success === 0
                                        "
                                        @click="clearSuccessFiles"
                                    >
                                        清空成功
                                    </el-button>
                                    <el-button
                                        size="small"
                                        :disabled="failedItems.length === 0"
                                        @click="exportFailedList"
                                    >
                                        导出失败
                                    </el-button>
                                </div>
                            </div>
                            <div
                                v-if="queuePanelVisible"
                                class="queue-inline-panel"
                            >
                                <div class="queue-stat-grid">
                                    <div class="queue-stat">
                                        <span>总文件</span>
                                        <strong>{{ uploadStats.total }}</strong>
                                    </div>
                                    <div class="queue-stat">
                                        <span>可上传</span>
                                        <strong>{{ uploadStats.ready }}</strong>
                                    </div>
                                    <div class="queue-stat">
                                        <span>上传中</span>
                                        <strong>{{
                                            uploadStats.uploading
                                        }}</strong>
                                    </div>
                                    <div class="queue-stat queue-stat--success">
                                        <span>成功</span>
                                        <strong>{{
                                            uploadStats.success
                                        }}</strong>
                                    </div>
                                    <div class="queue-stat queue-stat--error">
                                        <span>失败</span>
                                        <strong>{{ uploadStats.error }}</strong>
                                    </div>
                                </div>
                                <el-progress
                                    :percentage="uploadOverallPercent"
                                    :stroke-width="10"
                                />
                                <div class="queue-summary">
                                    {{ queueSummaryText }}
                                </div>
                            </div>
                        </template>

                        <div
                            v-if="isReadingHeaders && fileItems.length === 0"
                            class="file-skeleton-list"
                        >
                            <div
                                v-for="row in skeletonRows"
                                :key="row"
                                class="file-skeleton-row"
                            >
                                <span
                                    class="skeleton-block skeleton-name"
                                ></span>
                                <span
                                    class="skeleton-block skeleton-short"
                                ></span>
                                <span
                                    class="skeleton-block skeleton-medium"
                                ></span>
                                <span
                                    class="skeleton-block skeleton-badge"
                                ></span>
                            </div>
                        </div>

                        <el-table
                            ref="uploadTableRef"
                            v-else
                            :data="fileItems"
                            stripe
                            style="width: 100%"
                            class="summary-table file-table"
                            @selection-change="handleUploadSelectionChange"
                        >
                            <el-table-column
                                type="selection"
                                width="48"
                                align="center"
                            />
                            <el-table-column
                                type="index"
                                label="#"
                                width="50"
                                align="center"
                            />
                            <el-table-column
                                prop="name"
                                label="文件名"
                                min-width="220"
                                show-overflow-tooltip
                            />
                            <el-table-column label="年月" width="100">
                                <template #default="{ row }">
                                    <el-tag
                                        v-if="row.meta"
                                        type="info"
                                        size="small"
                                        class="soft-badge"
                                    >
                                        {{ row.meta.year }}-{{
                                            String(row.meta.month).padStart(
                                                2,
                                                "0",
                                            )
                                        }}
                                    </el-tag>
                                    <span v-else class="text-error"
                                        >解析失败</span
                                    >
                                </template>
                            </el-table-column>
                            <el-table-column
                                label="识别店铺名称"
                                min-width="170"
                                show-overflow-tooltip
                            >
                                <template #default="{ row }">
                                    <span
                                        v-if="row.meta?.shop"
                                        class="shop-cell"
                                    >
                                        <el-icon><Shop /></el-icon>
                                        <strong>{{ row.meta.shop }}</strong>
                                    </span>
                                    <span v-else class="text-error"
                                        >解析失败</span
                                    >
                                </template>
                            </el-table-column>
                            <el-table-column label="性质" width="90">
                                <template #default="{ row }">
                                    <template v-if="row.meta">
                                        <FileTypeBadge :type="row.meta.type" />
                                    </template>
                                    <span v-else class="text-error">-</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="平台识别" width="150">
                                <template #default="{ row }">
                                    <el-tooltip
                                        v-if="row.headerMatch"
                                        :content="row.headerMatch.message"
                                        placement="top"
                                    >
                                        <PlatformBadge
                                            v-if="
                                                row.headerMatch.status ===
                                                    'matched' && row.matchedRule
                                            "
                                            :platform="
                                                row.matchedRule.platform_code ||
                                                row.matchedRule.platform_name
                                            "
                                        />
                                        <el-tag
                                            v-else
                                            :type="
                                                headerMatchTagType(
                                                    row.headerMatch.status,
                                                )
                                            "
                                            size="small"
                                            class="soft-badge"
                                        >
                                            {{ platformMatchLabel(row) }}
                                        </el-tag>
                                    </el-tooltip>
                                    <span v-else class="text-tertiary">-</span>
                                </template>
                            </el-table-column>
                            <el-table-column
                                label="检查结果"
                                min-width="260"
                                show-overflow-tooltip
                            >
                                <template #default="{ row }">
                                    <span
                                        v-if="
                                            row.headerMatch.status === 'matched'
                                        "
                                        class="check-pill check-pill--success"
                                    >
                                        <span class="check-dot"></span>
                                        {{ validationMessage(row) }}
                                    </span>
                                    <span
                                        v-else
                                        class="check-pill check-pill--error"
                                    >
                                        <span class="check-dot"></span>
                                        {{ validationMessage(row) }}
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column
                                label="状态"
                                width="120"
                                align="center"
                            >
                                <template #default="{ row }">
                                    <template v-if="row.status === 'pending'">
                                        <span class="status-pill"
                                            >等待上传</span
                                        >
                                    </template>
                                    <template
                                        v-else-if="row.status === 'uploading'"
                                    >
                                        <span
                                            class="status-pill status-pill--warning"
                                            >上传中</span
                                        >
                                    </template>
                                    <template
                                        v-else-if="row.status === 'success'"
                                    >
                                        <span
                                            class="status-pill status-pill--success"
                                            >已完成</span
                                        >
                                    </template>
                                    <template
                                        v-else-if="row.status === 'error'"
                                    >
                                        <el-tooltip
                                            :content="row.error || '上传失败'"
                                            placement="top"
                                        >
                                            <span
                                                class="status-pill status-pill--error"
                                                >失败</span
                                            >
                                        </el-tooltip>
                                    </template>
                                </template>
                            </el-table-column>
                            <el-table-column label="进度" width="160">
                                <template #default="{ row }">
                                    <el-progress
                                        v-if="
                                            row.status === 'uploading' ||
                                            row.status === 'success'
                                        "
                                        :percentage="row.progress"
                                        :status="
                                            row.status === 'success'
                                                ? 'success'
                                                : ''
                                        "
                                        :stroke-width="8"
                                    />
                                    <el-tooltip
                                        v-else-if="row.status === 'error'"
                                        :content="row.error || '上传失败'"
                                        placement="top"
                                    >
                                        <span class="text-error">查看原因</span>
                                    </el-tooltip>
                                    <span v-else class="text-tertiary">-</span>
                                </template>
                            </el-table-column>
                            <el-table-column
                                label="操作"
                                width="120"
                                align="center"
                            >
                                <template #default="{ row, $index }">
                                    <el-button
                                        v-if="row.status === 'error'"
                                        type="primary"
                                        link
                                        :disabled="
                                            isUploading ||
                                            !isFileReadyForUpload(row)
                                        "
                                        @click="retryFile(row)"
                                    >
                                        重试
                                    </el-button>
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
                                <div class="file-empty-state">
                                    <div
                                        class="empty-illustration"
                                        aria-hidden="true"
                                    >
                                        <span></span>
                                    </div>
                                    <p>等待选择文件</p>
                                </div>
                            </template>
                        </el-table>
                    </el-card>
                </section>

                <aside class="reference-panel" aria-label="文件名辅助生成">
                    <div class="reference-heading">
                        <div>
                            <span class="section-kicker">HELPER</span>
                            <h3>辅助生成</h3>
                        </div>
                        <el-icon><InfoFilled /></el-icon>
                    </div>

                    <section
                        class="naming-rule-panel"
                        aria-label="文件名生成器"
                    >
                        <div class="naming-assistant">
                            <div class="naming-fields">
                                <label class="naming-field">
                                    <span>年月</span>
                                    <el-date-picker
                                        v-model="namingMonth"
                                        type="month"
                                        value-format="YYYY-MM"
                                        format="YYYY年MM月"
                                        placeholder="选择年月"
                                        :clearable="false"
                                    />
                                </label>
                                <label class="naming-field">
                                    <span>性质</span>
                                    <el-select
                                        v-model="namingType"
                                        placeholder="选择性质"
                                    >
                                        <el-option
                                            v-for="type in namingTypeOptions"
                                            :key="type"
                                            :label="fileTypeLabel(type)"
                                            :value="type"
                                        >
                                            <FileTypeBadge :type="type" />
                                        </el-option>
                                    </el-select>
                                </label>
                                <label class="naming-field">
                                    <span>店铺名称</span>
                                    <el-select
                                        v-model="namingShopName"
                                        placeholder="选择或输入店铺名称"
                                        clearable
                                        filterable
                                        allow-create
                                        default-first-option
                                        reserve-keyword
                                        :loading="shopLoading"
                                        @visible-change="
                                            handleShopSelectVisibleChange
                                        "
                                        @clear="clearNamingShopName"
                                        @change="normalizeNamingShopName"
                                    >
                                        <el-option
                                            v-for="shop in shopOptions"
                                            :key="shop.id"
                                            :label="shop.shop_name"
                                            :value="shop.shop_name"
                                        >
                                            <div class="shop-option">
                                                <ShopBadge
                                                    :label="shop.shop_name"
                                                    :color="shop.shop_color"
                                                    size="compact"
                                                />
                                                <small>{{
                                                    shop.platform_name
                                                }}</small>
                                            </div>
                                        </el-option>
                                    </el-select>
                                </label>
                            </div>

                            <button
                                type="button"
                                class="generated-name-button"
                                :class="{
                                    'generated-name-button--ready':
                                        canCopyGeneratedName,
                                }"
                                :disabled="!canCopyGeneratedName"
                                @click="copyGeneratedFileName"
                            >
                                <strong>{{
                                    generatedFileName ||
                                    "生成的文件名会显示在这里"
                                }}</strong>
                                <el-icon><CopyDocument /></el-icon>
                            </button>
                        </div>
                    </section>

                    <div v-if="!embedded" class="check-note">
                        <span class="check-note-dot"></span>
                        <span
                            >系统只读取文件开头前 20
                            行匹配接口表头；表头顺序不同或多余列不影响识别，部分规格支持缺字段阈值匹配。</span
                        >
                    </div>
                </aside>
            </div>
        </div>

        <el-dialog
            v-model="uploadConfirmVisible"
            title="确认开始上传"
            width="760px"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
        >
            <div class="upload-complete-dialog">
                <div>
                    <p class="upload-complete-title">
                        本次将上传 {{ readyUploadItems.length }} 个文件
                    </p>
                    <p class="upload-complete-desc">
                        系统会先创建统一上传记录，再根据文件类型派生任务。所有可识别文件都会进入核算任务；抖音动账文件会额外创建资金任务；抖音
                        BIC 文件会额外创建 BIC 任务。
                    </p>
                </div>
            </div>
            <div class="upload-confirm-summary">
                <div class="upload-confirm-stat">
                    <span>总大小</span>
                    <strong>{{ uploadConfirmSummary.totalSizeLabel }}</strong>
                </div>
                <div class="upload-confirm-stat">
                    <span>核算任务</span>
                    <strong>{{ uploadConfirmSummary.orderCount }}</strong>
                </div>
                <div class="upload-confirm-stat">
                    <span>动账资金任务</span>
                    <strong>{{ uploadConfirmSummary.transactionCount }}</strong>
                </div>
                <div class="upload-confirm-stat">
                    <span>BIC任务</span>
                    <strong>{{ uploadConfirmSummary.bicCount }}</strong>
                </div>
            </div>
            <div class="upload-confirm-note">
                提交前请重点核对文件名、年月、店铺、性质和预计进入模块。若识别结果不对，先返回修改命名再上传。
            </div>
            <el-table
                :data="uploadConfirmRows"
                stripe
                border
                class="summary-table upload-confirm-table"
                max-height="420"
            >
                <el-table-column
                    type="index"
                    label="#"
                    width="52"
                    align="center"
                />
                <el-table-column
                    prop="name"
                    label="文件名"
                    min-width="220"
                    show-overflow-tooltip
                />
                <el-table-column
                    prop="monthLabel"
                    label="年月"
                    width="110"
                    align="center"
                />
                <el-table-column
                    prop="typeLabel"
                    label="性质"
                    width="110"
                    align="center"
                />
                <el-table-column
                    prop="shopLabel"
                    label="店铺"
                    min-width="170"
                    show-overflow-tooltip
                />
                <el-table-column
                    prop="platformLabel"
                    label="平台"
                    width="120"
                    align="center"
                />
                <el-table-column
                    prop="sizeLabel"
                    label="大小"
                    width="110"
                    align="right"
                />
                <el-table-column
                    prop="targetLabel"
                    label="预计进入模块"
                    min-width="190"
                    show-overflow-tooltip
                />
                <el-table-column
                    label="检查结果"
                    min-width="210"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        <el-tag
                            :type="row.reviewStatusType"
                            size="small"
                            effect="plain"
                        >
                            {{ row.reviewStatusLabel }}
                        </el-tag>
                    </template>
                </el-table-column>
            </el-table>
            <template #footer>
                <el-button @click="uploadConfirmVisible = false"
                    >取消</el-button
                >
                <el-button type="primary" @click="confirmStartUpload"
                    >确认上传</el-button
                >
            </template>
        </el-dialog>

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
                <el-icon class="upload-complete-icon"
                    ><CircleCheckFilled
                /></el-icon>
                <div>
                    <p class="upload-complete-title">
                        成功上传 {{ uploadCompleteCount }} 个文件
                    </p>
                    <p class="upload-complete-desc">
                        系统已创建统一上传记录，并按文件类型派生对应任务，可以继续上传或前往任务列表查看进度。
                    </p>
                </div>
            </div>
            <template #footer>
                <el-button @click="handleContinueUpload">继续上传</el-button>
                <el-button type="primary" @click="goTaskList"
                    >查看任务列表</el-button
                >
            </template>
        </el-dialog>

        <div
            v-if="isUploading"
            class="upload-blocking-mask"
            role="alert"
            aria-live="assertive"
            aria-busy="true"
        >
            <div class="upload-blocking-card">
                <div class="upload-blocking-badge">上传进行中</div>
                <h3>请勿关闭页面或刷新浏览器</h3>
                <p>
                    文件正在上传并创建处理任务，中途中断可能导致本次批量上传不完整。
                </p>
                <el-progress
                    :percentage="uploadOverallPercent"
                    :stroke-width="10"
                    status="success"
                />
                <div class="upload-blocking-meta">
                    <span>当前文件</span>
                    <strong>{{
                        uploadingFileName || "正在准备上传..."
                    }}</strong>
                </div>
                <div class="upload-blocking-meta">
                    <span>完成进度</span>
                    <strong
                        >{{ uploadDialogDone }} /
                        {{
                            uploadDialogTotal || readyUploadItems.length
                        }}</strong
                    >
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "UploadCenter" });

import { ref, computed, h, nextTick } from "vue";
import { useRouter } from "vue-router";
import {
    CircleCheckFilled,
    CopyDocument,
    InfoFilled,
    Shop,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { TableInstance } from "element-plus";
import { parseFileName, type ParsedFileName } from "@/utils/format";
import { getFileSpecs, type FileSpec } from "@/api/file_spec";
import {
    createBatch,
    getOssSts,
    uploadCallback,
    type OssStsCredential,
} from "@/api/upload";
import { getOrganizationList, type Organization } from "@/api/organization";
import { getShopList, type Shop as ShopRecord } from "@/api/shop";
import { checkUploadQuota } from "@/api/quota";
import { useUserStore } from "@/stores/user";
import { usePageRefresh } from "@/composables/pageRefresh";
import PlatformBadge from "@/components/PlatformBadge.vue";
import FileTypeBadge from "@/components/FileTypeBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";

const props = withDefaults(
    defineProps<{
        embedded?: boolean;
    }>(),
    {
        embedded: false,
    },
);

const emit = defineEmits<{
    uploaded: [count: number];
    viewTasks: [];
    continueUpload: [];
}>();

interface FileItem {
    file: File;
    name: string;
    meta: ParsedFileName | null;
    matchedRule: FileSpec | null;
    headers: string[];
    headerRowIndex: number | null;
    headerMatch: HeaderMatchInfo;
    status: "pending" | "uploading" | "success" | "error";
    progress: number;
    error?: string;
}

interface UploadConfirmRow {
    name: string;
    monthLabel: string;
    typeLabel: string;
    shopLabel: string;
    platformLabel: string;
    sizeLabel: string;
    targetLabel: string;
    reviewStatusLabel: string;
    reviewStatusType: "success" | "warning" | "danger";
}

interface UploadBatchContext {
    batchId: number;
    sts: OssStsCredential;
    ossClient: any;
}

type HeaderMatchStatus =
    | "matched"
    | "mismatch"
    | "no_spec"
    | "read_failed"
    | "filename_failed";

interface HeaderMatchInfo {
    status: HeaderMatchStatus;
    message: string;
    matchedCount: number;
    expectedCount: number;
    headerRowIndex: number | null;
}

interface HeaderMatchResult {
    spec: FileSpec | null;
    headers: string[];
    info: HeaderMatchInfo;
}

interface HeaderRowCandidate {
    headers: string[];
    rowIndex: number;
}

interface RejectedFileInfo {
    name: string;
    message: string;
}

const FILENAME_PARSE_FAILED_MESSAGE =
    "文件名解析失败，格式示例：2026年02月_BIC_店铺名.xls、26年02月_其他服务款_店铺名.csv";
const MAX_REJECTED_FILES_IN_DIALOG = 10;

const platformUploadRules = [
    {
        platform: "抖音",
        platformCode: "douyin",
        types: ["订单", "动账", "bic", "运费险"],
        examples: [
            "26年02月_订单_抖音旗舰店.xlsx",
            "26年02月_动账_抖音旗舰店.xlsx",
            "26年2月_BIC_抖音旗舰店.xlsx",
            "26年02月_运费险_抖音旗舰店.xlsx",
        ],
    },
    {
        platform: "快手",
        platformCode: "kuaishou",
        types: ["gmv", "动账", "运费险", "订单"],
        examples: [
            "26年02月_动账_快手专营店.xlsx",
            "2026年2月_gmv_快手专营店.csv",
            "26年02月_订单_快手专营店.xlsx",
            "26年02月_运费险_快手专营店.csv",
        ],
    },
    {
        platform: "小红书",
        platformCode: "xiaohongshu",
        types: ["订单", "gmv", "其他服务款", "动账"],
        examples: [
            "26年02月_订单_小红书店铺.xlsx",
            "26年02月_动账_小红书店铺.xlsx",
            "2026年02月_GMV_小红书店铺.xlsx",
            "26年02月_其他服务款_小红书店铺.xlsx",
        ],
    },
    {
        platform: "微信小店",
        platformCode: "weixin_video",
        types: ["订单", "动账", "bic", "运费险"],
        examples: [
            "26年02月_动账_微信小店.xlsx",
            "26年02月_BIC_微信小店.xlsx",
            "26年02月_订单_微信小店.xlsx",
            "26年02月_运费险_微信小店.xlsx",
        ],
    },
    {
        platform: "支付宝",
        platformCode: "alipay",
        types: ["动账"],
        examples: ["26年02月_动账_支付宝店铺.xlsx"],
    },
    {
        platform: "千牛",
        platformCode: "qianniu",
        types: ["订单", "动账"],
        examples: [
            "26年02月_订单_千牛店铺.xlsx",
            "26年02月_动账_千牛店铺.xlsx",
        ],
    },
];

function fileTypeLabel(type: string): string {
    if (type.toLowerCase() === "gmv") return "GMV";
    return type.toLowerCase() === "bic" ? "BIC" : type;
}

const namingTypeOptions = Array.from(
    new Set(platformUploadRules.flatMap((rule) => rule.types)),
);
const visiblePlatformUploadRules = computed(() => {
    if (!props.embedded) return platformUploadRules;
    return platformUploadRules.map((rule) => ({
        ...rule,
        examples: rule.examples.slice(0, 1),
    }));
});
const namingMonth = ref("");
const namingType = ref("");
const namingShopName = ref("");
const shopLoading = ref(false);
const shopOptions = ref<ShopRecord[]>([]);
const SHOP_PAGE_SIZE = 100;

const generatedFileName = computed(() => {
    const monthText = formatNamingMonth(namingMonth.value);
    const typeText = namingType.value ? fileTypeLabel(namingType.value) : "";
    const shopText = sanitizeFileNamePart(namingShopName.value);
    if (!monthText || !typeText || !shopText) return "";
    return `${monthText}_${typeText}_${shopText}.xlsx`;
});

const canCopyGeneratedName = computed(() => Boolean(generatedFileName.value));

function formatNamingMonth(month: string): string {
    const match = month.match(/^(\d{4})-(\d{2})$/);
    if (!match) return "";
    return `${match[1].slice(-2)}年${match[2]}月`;
}

function sanitizeFileNamePart(value: string): string {
    return value
        .trim()
        .replace(/[\\/:*?"<>|]/g, "-")
        .replace(/\s+/g, "");
}

function normalizeNamingShopName() {
    namingShopName.value = namingShopName.value.trim();
}

function clearNamingShopName() {
    namingShopName.value = "";
}

async function fetchShopOptions() {
    if (shopLoading.value || shopOptions.value.length > 0) return;
    shopLoading.value = true;
    try {
        const allShops: ShopRecord[] = [];
        let page = 1;
        let total = 0;

        do {
            const res = await getShopList({ page, page_size: SHOP_PAGE_SIZE });
            const items = res.items || [];
            total = res.total || 0;
            allShops.push(...items);

            if (items.length < SHOP_PAGE_SIZE) {
                break;
            }
            page += 1;
        } while (allShops.length < total);

        shopOptions.value = allShops;
    } catch {
        // Error handled by interceptor; custom shop names still work.
    } finally {
        shopLoading.value = false;
    }
}

async function handleShopSelectVisibleChange(visible: boolean) {
    if (visible) {
        await fetchShopOptions();
    }
}

function fallbackCopyText(text: string): boolean {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "true");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    const copied = document.execCommand("copy");
    document.body.removeChild(textarea);
    return copied;
}

async function copyGeneratedFileName() {
    if (!generatedFileName.value) {
        ElMessage.warning("请先填写年月、性质和店铺名称");
        return;
    }

    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(generatedFileName.value);
        } else if (!fallbackCopyText(generatedFileName.value)) {
            throw new Error("fallback copy failed");
        }
        ElMessage.success("文件名已复制");
    } catch {
        if (fallbackCopyText(generatedFileName.value)) {
            ElMessage.success("文件名已复制");
            return;
        }
        ElMessage.error("复制失败，请手动复制");
    }
}

function validationMessage(row: FileItem): string {
    if (!row.meta) {
        return FILENAME_PARSE_FAILED_MESSAGE;
    }
    if (!row.meta.shop) {
        return "文件名缺少店铺名称";
    }
    if (row.headerMatch.status === "matched") {
        return `检查通过：${row.headerMatch.message}`;
    }
    return row.headerMatch.message;
}

// State
const fileInputRef = ref<HTMLInputElement>();
const uploadTableRef = ref<TableInstance>();
const isDragging = ref(false);
const isUploading = ref(false);
const fileItems = ref<FileItem[]>([]);
const selectedFileRows = ref<FileItem[]>([]);
const fileSpecs = ref<FileSpec[]>([]);
const skeletonRows = [1, 2, 3];
const userStore = useUserStore();
const router = useRouter();
const orgLoading = ref(false);
const orgOptions = ref<Organization[]>([]);
const targetOrgId = ref<number | undefined>(undefined);
const isReadingHeaders = ref(false);
const uploadConfirmVisible = ref(false);
const uploadCompleteDialogVisible = ref(false);
const uploadCompleteCount = ref(0);
const uploadingFileName = ref("");
const uploadDialogTotal = ref(0);
const uploadDialogDone = ref(0);
let xlsxModulePromise: Promise<typeof import("xlsx")> | null = null;
let ossModulePromise: Promise<typeof import("ali-oss")> | null = null;

const uploadableItems = computed(() =>
    fileItems.value.filter((item) => item.status !== "success"),
);
const readyUploadItems = computed(() =>
    uploadableItems.value.filter(isFileReadyForUpload),
);
const failedItems = computed(() =>
    fileItems.value.filter((item) => item.status === "error"),
);
const failedReadyItems = computed(() =>
    failedItems.value.filter(isFileReadyForUpload),
);
const queuePanelVisible = computed(
    () => fileItems.value.length > 0 || uploadDialogTotal.value > 0,
);
const hasSelectedFiles = computed(() => selectedFileRows.value.length > 0);

const uploadOverallPercent = computed(() => {
    const total = uploadDialogTotal.value || readyUploadItems.value.length;
    if (total === 0) return 0;
    const currentProgress = fileItems.value
        .filter((item) => item.status === "uploading")
        .reduce(
            (sum, item) =>
                sum + Math.max(0, Math.min(item.progress, 100)) / 100,
            0,
        );
    return Math.min(
        100,
        Math.round(((uploadDialogDone.value + currentProgress) / total) * 100),
    );
});

const uploadStats = computed(() => ({
    total: fileItems.value.length,
    ready: readyUploadItems.value.length,
    uploading: fileItems.value.filter((item) => item.status === "uploading")
        .length,
    success: fileItems.value.filter((item) => item.status === "success").length,
    error: failedItems.value.length,
}));

const queueSummaryText = computed(() => {
    if (isUploading.value) {
        return `正在上传 ${uploadStats.value.uploading} 个文件，订单优先、GMV 其次，并发 3 个，失败不会阻塞后续文件。`;
    }
    if (uploadStats.value.error > 0) {
        return `已完成本轮上传，${uploadStats.value.error} 个文件失败，可只重试失败文件。`;
    }
    if (uploadStats.value.success > 0) {
        return `已成功上传 ${uploadStats.value.success} 个文件。`;
    }
    return "通过预检后，订单类型会排在上传队列前面，GMV 类型紧随其后。";
});

const canUpload = computed(() => {
    return (
        readyUploadItems.value.length > 0 &&
        (!userStore.isSuperAdmin || Boolean(targetOrgId.value)) &&
        !isUploading.value
    );
});

const uploadConfirmRows = computed<UploadConfirmRow[]>(() =>
    orderUploadItems(uploadableItems.value).map((item) => ({
        name: item.name,
        monthLabel: formatMetaMonth(item),
        typeLabel: formatConfirmType(item),
        shopLabel: item.meta?.shop || "-",
        platformLabel:
            item.matchedRule?.platform_name ||
            item.matchedRule?.platform_code ||
            "-",
        sizeLabel: formatFileSize(item.file.size),
        targetLabel: uploadTargetLabel(item),
        reviewStatusLabel: uploadReviewStatusLabel(item),
        reviewStatusType: uploadReviewStatusType(item),
    })),
);

const uploadConfirmSummary = computed(() => {
    let orderCount = 0;
    let transactionCount = 0;
    let bicCount = 0;
    const totalBytes = totalFileBytes(readyUploadItems.value);

    for (const item of readyUploadItems.value) {
        const targets = uploadTargets(item);
        if (targets.includes("核算任务")) orderCount += 1;
        if (targets.includes("资金任务")) transactionCount += 1;
        if (targets.includes("BIC任务")) bicCount += 1;
    }

    return {
        totalSizeLabel: formatFileSize(totalBytes),
        orderCount,
        transactionCount,
        bicCount,
    };
});

function totalFileBytes(items: FileItem[]): number {
    return items.reduce((sum, item) => sum + item.file.size, 0);
}

function formatMetaMonth(item: FileItem): string {
    if (!item.meta) return "-";
    return `${item.meta.year}-${String(item.meta.month).padStart(2, "0")}`;
}

function formatConfirmType(item: FileItem): string {
    if (!item.meta?.type) return "-";
    return fileTypeLabel(item.meta.type);
}

function formatFileSize(bytes: number): string {
    if (bytes >= 1024 * 1024 * 1024) {
        return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }
    if (bytes >= 1024 * 1024) {
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }
    return `${(bytes / 1024).toFixed(1)} KB`;
}

function uploadTargets(item: FileItem): string[] {
    const type = item.meta?.type?.toLowerCase() || "";
    const platform = item.matchedRule?.platform_code || "";
    const targets = new Set<string>();

    targets.add("核算任务");

    if (type === "动账" && platform === "douyin") {
        targets.add("资金任务");
    }

    if (type === "bic" && platform === "douyin") {
        targets.add("BIC任务");
    }

    return Array.from(targets);
}

function uploadTargetLabel(item: FileItem): string {
    const targets = uploadTargets(item);
    return targets.length > 0 ? targets.join(" / ") : "-";
}

function uploadReviewStatusLabel(item: FileItem): string {
    if (isFileReadyForUpload(item)) return "可上传";
    if (item.status === "success") return "已上传";
    return validationMessage(item);
}

function uploadReviewStatusType(
    item: FileItem,
): "success" | "warning" | "danger" {
    if (isFileReadyForUpload(item)) return "success";
    if (!item.meta) return "danger";
    if (item.headerMatch.status === "matched") return "warning";
    return "danger";
}

// Load file specs on mount for platform auto-detection
async function loadFileSpecs() {
    try {
        fileSpecs.value = await getFileSpecs();
    } catch {
        // Silently fail - will show "待识别" for all
    }
}

async function loadOrgOptions() {
    if (!userStore.isSuperAdmin) return;
    orgLoading.value = true;
    try {
        const res = await getOrganizationList({ page: 1, page_size: 100 });
        orgOptions.value = (res.items || []).filter(
            (org) => org.status === "1" || org.status === 1,
        );
        if (!targetOrgId.value && orgOptions.value.length === 1) {
            targetOrgId.value = orgOptions.value[0].id;
        }
    } catch {
        // Error handled by interceptor
    } finally {
        orgLoading.value = false;
    }
}

async function refreshPage() {
    await loadFileSpecs();
    await loadOrgOptions();
}

void refreshPage();

async function ensureFileSpecsLoaded() {
    if (fileSpecs.value.length > 0) return;
    await loadFileSpecs();
}

usePageRefresh(refreshPage);

async function showRejectedFilesDialog(rejectedFiles: RejectedFileInfo[]) {
    const visibleFiles = rejectedFiles.slice(0, MAX_REJECTED_FILES_IN_DIALOG);
    const hiddenCount = rejectedFiles.length - visibleFiles.length;
    const children = [
        h(
            "p",
            { class: "upload-validation-dialog__intro" },
            `以下 ${rejectedFiles.length} 个文件未通过文件名或表头校验，已从上传列表中跳过。`,
        ),
        h(
            "div",
            { class: "upload-validation-dialog__list" },
            visibleFiles.map((item, index) =>
                h(
                    "div",
                    {
                        class: "upload-validation-dialog__item",
                        key: `${item.name}-${index}`,
                    },
                    [
                        h(
                            "strong",
                            {
                                class: "upload-validation-dialog__name",
                                title: item.name,
                            },
                            item.name,
                        ),
                        h(
                            "span",
                            { class: "upload-validation-dialog__message" },
                            item.message,
                        ),
                    ],
                ),
            ),
        ),
    ];

    if (hiddenCount > 0) {
        children.push(
            h(
                "p",
                { class: "upload-validation-dialog__more" },
                `还有 ${hiddenCount} 个文件未展示，请修正后重新选择。`,
            ),
        );
    }

    try {
        await ElMessageBox.alert(
            h("div", { class: "upload-validation-dialog" }, children),
            "文件预检未通过",
            {
                appendTo: "body",
                confirmButtonText: "我知道了",
                customClass: "upload-validation-message-box",
                customStyle: {
                    width: "min(1120px, calc(100vw - 96px))",
                    maxWidth: "calc(100vw - 32px)",
                },
                closeOnClickModal: false,
                closeOnPressEscape: false,
                showClose: false,
                type: "warning",
            },
        );
    } catch {
        // The dialog is confirmation-only; keep this guard for programmatic closes.
    }
}

// File input trigger
function triggerFileInput() {
    fileInputRef.value?.click();
}

// Handle file input change
function handleFileInputChange(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files) {
        processFiles(Array.from(input.files));
        input.value = "";
    }
}

// Handle drag and drop
function handleDrop(e: DragEvent) {
    isDragging.value = false;
    if (e.dataTransfer?.files) {
        processFiles(Array.from(e.dataTransfer.files));
    }
}

// Process selected files
async function processFiles(files: File[]) {
    if (isUploading.value) {
        ElMessage.warning("文件正在上传中，请等待完成后再选择新文件");
        return;
    }
    if (files.length === 0) return;

    uploadCompleteDialogVisible.value = false;
    await ensureFileSpecsLoaded();
    isReadingHeaders.value = true;
    const rejectedFiles: RejectedFileInfo[] = [];

    try {
        for (const file of files) {
            // Validate file type
            if (!file.name.match(/\.(xlsx|xlsm|xls|csv)$/i)) {
                ElMessage.warning(
                    `文件 ${file.name} 不是 Excel/CSV 文件，已跳过`,
                );
                continue;
            }

            // Check duplicate
            if (fileItems.value.some((f) => f.name === file.name)) {
                ElMessage.warning(`文件 ${file.name} 已存在，已跳过`);
                continue;
            }

            // Parse filename
            const meta = parseFileName(file.name);
            if (!meta) {
                rejectedFiles.push({
                    name: file.name,
                    message: FILENAME_PARSE_FAILED_MESSAGE,
                });
                continue;
            }

            let headers: string[] = [];
            let matchedRule: FileSpec | null = null;
            let headerMatch: HeaderMatchInfo = {
                status: "filename_failed",
                message: FILENAME_PARSE_FAILED_MESSAGE,
                matchedCount: 0,
                expectedCount: 0,
                headerRowIndex: null,
            };

            if (fileSpecs.value.length > 0) {
                try {
                    const headerRows = await readTabularHeaderRows(file);
                    const matchResult = matchPlatformByHeaderRows(
                        headerRows,
                        meta.type,
                    );
                    matchedRule = matchResult.spec;
                    headers = matchResult.headers;
                    headerMatch = matchResult.info;
                } catch (err: any) {
                    headerMatch = {
                        status: "read_failed",
                        message: err?.message || "读取文件表头失败",
                        matchedCount: 0,
                        expectedCount: 0,
                        headerRowIndex: null,
                    };
                }
            } else {
                headerMatch = {
                    status: "no_spec",
                    message: "未获取到接口表头规格，无法识别平台",
                    matchedCount: 0,
                    expectedCount: 0,
                    headerRowIndex: null,
                };
            }

            if (headerMatch.status !== "matched" || !matchedRule) {
                rejectedFiles.push({
                    name: file.name,
                    message: headerMatch.message,
                });
                continue;
            }

            fileItems.value.push({
                file,
                name: file.name,
                meta,
                matchedRule,
                headers,
                headerRowIndex: headerMatch.headerRowIndex,
                headerMatch,
                status: "pending",
                progress: 0,
            });
        }
    } finally {
        isReadingHeaders.value = false;
    }

    if (rejectedFiles.length > 0) {
        await showRejectedFilesDialog(rejectedFiles);
    }
}

// Read the first non-empty rows using SheetJS. Some platform exports place notes
// above the real header, so matching chooses the best header row below.
async function readTabularHeaderRows(
    file: File,
): Promise<HeaderRowCandidate[]> {
    const isCsv = file.name.toLowerCase().endsWith(".csv");
    if (isCsv) {
        return readCsvHeaderRows(file);
    }

    const XLSX = await loadXlsx();
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = e.target?.result;
                if (!data) {
                    resolve([]);
                    return;
                }
                const wb = XLSX.read(data, {
                    type: "array",
                    sheetRows: HEADER_SCAN_ROW_LIMIT,
                    cellFormula: false,
                    cellHTML: false,
                    cellNF: false,
                    cellStyles: false,
                    cellText: false,
                });
                const ws = wb.Sheets[wb.SheetNames[0]];
                const rows = XLSX.utils.sheet_to_json<string[]>(ws, {
                    header: 1,
                    blankrows: true,
                    defval: "",
                    raw: false,
                });
                resolve(toHeaderRowCandidates(rows));
            } catch (err) {
                reject(err);
            }
        };
        reader.onerror = reject;
        reader.readAsArrayBuffer(file);
    });
}

const HEADER_SCAN_ROW_LIMIT = 20;
const CSV_HEADER_SCAN_BYTES = 256 * 1024;

async function readCsvHeaderRows(file: File): Promise<HeaderRowCandidate[]> {
    const buffer = await file
        .slice(0, Math.min(file.size, CSV_HEADER_SCAN_BYTES))
        .arrayBuffer();
    const text = decodeCsvBuffer(buffer);
    const rows = parseCsvPreviewRows(text, HEADER_SCAN_ROW_LIMIT);
    return toHeaderRowCandidates(rows);
}

function toHeaderRowCandidates(rows: unknown[][]): HeaderRowCandidate[] {
    return rows
        .slice(0, HEADER_SCAN_ROW_LIMIT)
        .map((row, index) => ({
            headers: row.map((cell) => String(cell || "").trim()),
            rowIndex: index + 1,
        }))
        .filter((row) => row.headers.some(Boolean));
}

function parseCsvPreviewRows(text: string, maxRows: number): string[][] {
    const rows: string[][] = [];
    let row: string[] = [];
    let cell = "";
    let inQuotes = false;

    for (
        let index = 0;
        index < text.length && rows.length < maxRows;
        index += 1
    ) {
        const char = text[index];
        const nextChar = text[index + 1];

        if (char === '"') {
            if (inQuotes && nextChar === '"') {
                cell += '"';
                index += 1;
            } else {
                inQuotes = !inQuotes;
            }
            continue;
        }

        if (char === "," && !inQuotes) {
            row.push(cell);
            cell = "";
            continue;
        }

        if ((char === "\n" || char === "\r") && !inQuotes) {
            if (char === "\r" && nextChar === "\n") index += 1;
            row.push(cell);
            rows.push(row);
            row = [];
            cell = "";
            continue;
        }

        cell += char;
    }

    if (rows.length < maxRows && (cell || row.length > 0)) {
        row.push(cell);
        rows.push(row);
    }

    return rows;
}

function decodeCsvBuffer(buffer: ArrayBuffer): string {
    const encodings = ["utf-8", "gb18030"];
    for (const encoding of encodings) {
        try {
            return new TextDecoder(encoding, { fatal: true }).decode(buffer);
        } catch {
            // Try the next common CSV export encoding.
        }
    }
    return new TextDecoder("utf-8").decode(buffer);
}

function loadXlsx() {
    if (!xlsxModulePromise) {
        xlsxModulePromise = import("xlsx");
    }
    return xlsxModulePromise;
}

function matchPlatformByHeaderRows(
    headerRows: HeaderRowCandidate[],
    type: string,
): HeaderMatchResult {
    const typedCandidates = fileSpecs.value.filter(
        (r) => r.type_code.toLowerCase() === type.toLowerCase(),
    );

    if (typedCandidates.length === 0) {
        return {
            spec: null,
            info: {
                status: "no_spec",
                message: `接口未配置「${type}」类型的表头规格`,
                matchedCount: 0,
                expectedCount: 0,
                headerRowIndex: null,
            },
            headers: [],
        };
    }

    let bestMatched: {
        spec: FileSpec;
        headers: string[];
        matchedCount: number;
        expectedCount: number;
        headerRowIndex: number;
    } | null = null;

    for (const row of headerRows) {
        const actualHeaders = normalizeHeaders(row.headers);
        for (const spec of typedCandidates) {
            if (!isHeaderRowAllowedForSpec(row, spec)) continue;
            const expectedHeaders = normalizeHeaders(spec.headers || []);
            if (expectedHeaders.length === 0) continue;
            const matchedCount = countMatchedHeaders(
                actualHeaders,
                expectedHeaders,
            );
            const requiredCount = requiredMatchCount(
                spec,
                expectedHeaders.length,
            );
            if (matchedCount >= requiredCount) {
                if (
                    !bestMatched ||
                    matchedCount > bestMatched.matchedCount ||
                    (matchedCount === bestMatched.matchedCount &&
                        expectedHeaders.length < bestMatched.expectedCount)
                ) {
                    bestMatched = {
                        spec,
                        headers: row.headers,
                        matchedCount,
                        expectedCount: expectedHeaders.length,
                        headerRowIndex: row.rowIndex,
                    };
                }
            }
        }
    }

    if (bestMatched) {
        return {
            spec: bestMatched.spec,
            headers: bestMatched.headers,
            info: {
                status: "matched",
                message: `表头匹配 ${bestMatched.matchedCount}/${bestMatched.expectedCount} 个字段，识别平台：${bestMatched.spec.platform_name || bestMatched.spec.platform_code}（已忽略多余列和列顺序）`,
                matchedCount: bestMatched.matchedCount,
                expectedCount: bestMatched.expectedCount,
                headerRowIndex: bestMatched.headerRowIndex,
            },
        };
    }

    const closest = scoreClosest(typedCandidates, headerRows);
    return {
        spec: null,
        headers: closest?.headers || headerRows[0]?.headers || [],
        info: {
            status: "mismatch",
            message: closest
                ? `表头不一致，最接近「${closest.spec.name}」：匹配 ${closest.matchedCount}/${closest.expectedCount} 个字段`
                : "表头不一致，未匹配到平台规格",
            matchedCount: closest?.matchedCount || 0,
            expectedCount: closest?.expectedCount || 0,
            headerRowIndex: closest ? closest.headerRowIndex : null,
        },
    };
}

function fixedHeaderRowForSpec(spec: FileSpec): number | null {
    if (spec.platform_code === "alipay" && spec.type_code === "动账") {
        return 3;
    }
    return null;
}

function isHeaderRowAllowedForSpec(
    row: HeaderRowCandidate,
    spec: FileSpec,
): boolean {
    const fixedRow = fixedHeaderRowForSpec(spec);
    return fixedRow === null || row.rowIndex === fixedRow;
}

function normalizeHeaders(headers: string[]): string[] {
    const normalized = headers.map(canonicalHeader).filter(Boolean);

    return Array.from(new Set(normalized));
}

function canonicalHeader(header: string): string {
    return String(header || "")
        .trim()
        .replace(/[\s　\uFEFF\u200B-\u200D]+/g, "")
        .replace(/帐/g, "账")
        .replace(/（/g, "(")
        .replace(/）/g, ")")
        .toLowerCase();
}

function countMatchedHeaders(actual: string[], expected: string[]): number {
    const actualSet = new Set(actual);
    return expected.filter((h) => actualSet.has(h)).length;
}

function requiredMatchCount(spec: FileSpec, expectedCount: number): number {
    if (!usesThresholdMatch(spec)) {
        return expectedCount;
    }
    const threshold = Number(spec.match_threshold);
    if (!Number.isFinite(threshold) || threshold <= 0) {
        return expectedCount;
    }
    return Math.min(expectedCount, Math.ceil(threshold));
}

function usesThresholdMatch(spec: FileSpec): boolean {
    return spec.platform_code === "douyin" && spec.type_code === "运费险";
}

function scoreClosest(
    candidates: FileSpec[],
    headerRows: HeaderRowCandidate[],
) {
    let best: {
        spec: FileSpec;
        headers: string[];
        matchedCount: number;
        expectedCount: number;
        headerRowIndex: number;
    } | null = null;

    for (const row of headerRows) {
        const actualHeaders = normalizeHeaders(row.headers);

        for (const spec of candidates) {
            if (!isHeaderRowAllowedForSpec(row, spec)) continue;
            const expectedHeaders = normalizeHeaders(spec.headers || []);
            if (expectedHeaders.length === 0) continue;
            const matchedCount = countMatchedHeaders(
                actualHeaders,
                expectedHeaders,
            );
            if (!best || matchedCount > best.matchedCount) {
                best = {
                    spec,
                    headers: row.headers,
                    matchedCount,
                    expectedCount: expectedHeaders.length,
                    headerRowIndex: row.rowIndex,
                };
            }
        }
    }

    return best;
}

function headerMatchTagType(status: HeaderMatchStatus): string {
    const map: Record<HeaderMatchStatus, string> = {
        matched: "success",
        mismatch: "danger",
        no_spec: "warning",
        read_failed: "danger",
        filename_failed: "danger",
    };
    return map[status];
}

function platformMatchLabel(row: FileItem): string {
    if (row.headerMatch.status === "matched" && row.matchedRule) {
        return row.matchedRule.platform_name || row.matchedRule.platform_code;
    }
    const map: Record<HeaderMatchStatus, string> = {
        matched: "已识别",
        mismatch: "表头不一致",
        no_spec: "无规格",
        read_failed: "读取失败",
        filename_failed: "解析失败",
    };
    return map[row.headerMatch.status];
}

const STS_REFRESH_INTERVAL_MS = 5 * 60 * 1000;
const STS_REFRESH_SAFETY_MS = 60 * 1000;
const OSS_REQUEST_TIMEOUT = 2 * 60 * 1000;
const OSS_MULTIPART_PART_SIZE = 1024 * 1024;
const OSS_MULTIPART_PARALLEL = 2;
const UPLOAD_CONCURRENCY = 3;
const UPLOAD_TYPE_PRIORITY: Record<string, number> = {
    订单: 1,
    gmv: 2,
    GMV: 2,
};

function buildOssKey(sts: OssStsCredential, fileName: string): string {
    const safeName = fileName.replace(/[\\/]/g, "_");
    return `${sts.oss_key_prefix}${Date.now()}_${safeName}`;
}

function toOssCredential(sts: OssStsCredential) {
    return {
        accessKeyId: sts.access_key_id,
        accessKeySecret: sts.access_key_secret,
        stsToken: sts.security_token,
    };
}

function stsRefreshInterval(sts: OssStsCredential): number {
    const expiresAt = Date.parse(sts.expiration);
    if (Number.isNaN(expiresAt)) return STS_REFRESH_INTERVAL_MS;
    const msUntilExpiration = expiresAt - Date.now() - STS_REFRESH_SAFETY_MS;
    return Math.max(
        30 * 1000,
        Math.min(STS_REFRESH_INTERVAL_MS, msUntilExpiration),
    );
}

async function createOssClient(sts: OssStsCredential, batchId: number) {
    const OSS = await loadOss();
    return new OSS.default({
        region: sts.region,
        bucket: sts.bucket,
        endpoint: sts.endpoint,
        ...toOssCredential(sts),
        secure: sts.endpoint.startsWith("https://"),
        timeout: OSS_REQUEST_TIMEOUT,
        retryMax: 0,
        refreshSTSToken: async () => {
            const refreshed = await getOssSts(batchId);
            return toOssCredential(refreshed);
        },
        refreshSTSTokenInterval: stsRefreshInterval(sts),
    });
}

async function uploadFileToOss(ossClient: any, ossKey: string, item: FileItem) {
    await ossClient.multipartUpload(ossKey, item.file, {
        timeout: OSS_REQUEST_TIMEOUT,
        partSize: OSS_MULTIPART_PART_SIZE,
        parallel: OSS_MULTIPART_PARALLEL,
        progress: async (percent: number) => {
            item.progress = Math.round(percent * 100);
        },
    });
}

function ossErrorMessage(err: any): string {
    if (
        err?.code === "ConnectionTimeoutError" ||
        err?.code === "ResponseTimeoutError"
    ) {
        return "文件上传超时，请重试";
    }
    return err?.message || err?.name || err?.code || "上传失败";
}

function isFileReadyForUpload(item: FileItem): boolean {
    return (
        item.status !== "success" &&
        item.status !== "uploading" &&
        item.meta !== null &&
        item.matchedRule !== null &&
        item.headerMatch.status === "matched"
    );
}

function uploadTypePriority(item: FileItem): number {
    const type = item.meta?.type || "";
    return UPLOAD_TYPE_PRIORITY[type] || Number.MAX_SAFE_INTEGER;
}

function orderUploadItems(items: FileItem[]): FileItem[] {
    return items
        .map((item, index) => ({ item, index }))
        .sort((a, b) => {
            const priorityDiff =
                uploadTypePriority(a.item) - uploadTypePriority(b.item);
            return priorityDiff || a.index - b.index;
        })
        .map(({ item }) => item);
}

function loadOss() {
    if (!ossModulePromise) {
        ossModulePromise = import("ali-oss");
    }
    return ossModulePromise;
}

// Remove a file from list
function removeFile(index: number) {
    fileItems.value.splice(index, 1);
    syncSelectedFileRows();
}

// Clear all files
function clearAll() {
    fileItems.value = [];
    selectedFileRows.value = [];
    uploadDialogTotal.value = 0;
    uploadDialogDone.value = 0;
    void clearUploadSelection();
}

function handleUploadSelectionChange(rows: FileItem[]) {
    selectedFileRows.value = rows;
}

async function clearUploadSelection() {
    await nextTick();
    uploadTableRef.value?.clearSelection();
}

function syncSelectedFileRows() {
    selectedFileRows.value = selectedFileRows.value.filter((item) =>
        fileItems.value.includes(item),
    );
    if (selectedFileRows.value.length === 0) {
        void clearUploadSelection();
    }
}

function clearSelectedFiles() {
    if (selectedFileRows.value.length === 0) return;
    const selectedSet = new Set(selectedFileRows.value);
    fileItems.value = fileItems.value.filter((item) => !selectedSet.has(item));
    selectedFileRows.value = [];
    if (fileItems.value.length === 0) {
        uploadDialogTotal.value = 0;
        uploadDialogDone.value = 0;
    }
    void clearUploadSelection();
}

function showUploadCompleteDialog(successCount: number) {
    uploadCompleteCount.value = successCount;
    uploadCompleteDialogVisible.value = true;
    emit("uploaded", successCount);
}

function handleContinueUpload() {
    uploadCompleteDialogVisible.value = false;
    emit("continueUpload");
}

function goTaskList() {
    uploadCompleteDialogVisible.value = false;
    if (props.embedded) {
        emit("viewTasks");
        return;
    }
    router.push("/tasks");
}

async function createUploadContext(
    itemsToUpload: FileItem[],
): Promise<UploadBatchContext> {
    const batch = await createBatch({
        file_count: itemsToUpload.length,
        total_bytes: totalFileBytes(itemsToUpload),
        org_id: userStore.isSuperAdmin ? targetOrgId.value : undefined,
    });
    const sts = await getOssSts(batch.id);
    const ossClient = await createOssClient(sts, batch.id);
    return { batchId: batch.id, sts, ossClient };
}

async function uploadSingleFile(
    item: FileItem,
    context: UploadBatchContext,
): Promise<boolean> {
    if (!item.meta) return false;
    uploadingFileName.value = item.name;
    item.status = "uploading";
    item.progress = 0;
    item.error = undefined;

    try {
        const ossKey = buildOssKey(context.sts, item.file.name);
        await uploadFileToOss(context.ossClient, ossKey, item);
        await uploadCallback({
            batch_id: context.batchId,
            original_name: item.name,
            oss_key: ossKey,
            file_size: item.file.size,
            parsed_year: item.meta.year,
            parsed_month: item.meta.month,
            parsed_type: item.meta.type,
            parsed_shop: item.meta.shop,
            detected_platform: item.matchedRule?.platform_code || "",
        });

        item.status = "success";
        item.progress = 100;
        return true;
    } catch (err: any) {
        item.status = "error";
        item.error = ossErrorMessage(err);
        return false;
    } finally {
        uploadDialogDone.value += 1;
    }
}

async function runUploadQueue(itemsToUpload: FileItem[]) {
    if (itemsToUpload.length === 0) {
        ElMessage.warning("没有可上传的文件");
        return;
    }
    let successCount = 0;
    let failedCount = 0;
    uploadDialogTotal.value = itemsToUpload.length;
    uploadDialogDone.value = 0;
    uploadingFileName.value = "";
    isUploading.value = true;

    try {
        const context = await createUploadContext(itemsToUpload);
        let cursor = 0;
        const workerCount = Math.min(UPLOAD_CONCURRENCY, itemsToUpload.length);
        const workers = Array.from({ length: workerCount }, async () => {
            while (cursor < itemsToUpload.length) {
                const item = itemsToUpload[cursor];
                cursor += 1;
                const ok = await uploadSingleFile(item, context);
                if (ok) {
                    successCount += 1;
                } else {
                    failedCount += 1;
                }
            }
        });
        await Promise.all(workers);

        if (successCount > 0) {
            showUploadCompleteDialog(successCount);
        }
        if (failedCount > 0) {
            ElMessage.warning(
                `本轮上传完成，${failedCount} 个文件失败，可只重试失败文件`,
            );
        }
    } catch (err: any) {
        ElMessage.error("创建上传批次失败：" + (err.message || "未知错误"));
    } finally {
        isUploading.value = false;
        uploadingFileName.value = "";
    }
}

async function startUpload() {
    if (!canUpload.value) return;
    uploadConfirmVisible.value = true;
}

async function confirmStartUpload() {
    uploadConfirmVisible.value = false;

    // 计算总文件大小
    const totalBytes = totalFileBytes(readyUploadItems.value);
    const totalMB = (totalBytes / (1024 * 1024)).toFixed(2);

    // 检查本月上传额度。超级管理员代上传时，后端会按目标组织在创建批次前再次校验。
    if (!userStore.isSuperAdmin) {
        try {
            const result = await checkUploadQuota(totalBytes);
            if (!result.can_upload) {
                await ElMessageBox.alert(
                    `${result.message}\n\n本次上传文件总大小：${totalMB} MB`,
                    "本月上传额度不足",
                    {
                        appendTo: "body",
                        confirmButtonText: "我知道了",
                        customClass: "upload-quota-limit-message-box",
                        modalClass: "upload-quota-limit-message-box__mask",
                        type: "warning",
                    },
                );
                return;
            }
        } catch (error: any) {
            ElMessage.error(
                "检查本月上传额度失败：" + (error.message || "未知错误"),
            );
            return;
        }
    }

    await runUploadQueue(orderUploadItems(readyUploadItems.value));
}

async function retryFailedFiles() {
    if (isUploading.value) return;
    await runUploadQueue(orderUploadItems(failedReadyItems.value));
}

async function retryFile(item: FileItem) {
    if (isUploading.value || !isFileReadyForUpload(item)) return;
    await runUploadQueue([item]);
}

function clearSuccessFiles() {
    fileItems.value = fileItems.value.filter(
        (item) => item.status !== "success",
    );
    syncSelectedFileRows();
}

function exportFailedList() {
    if (failedItems.value.length === 0) return;
    const rows = [
        ["文件名", "店铺", "性质", "失败原因"],
        ...failedItems.value.map((item) => [
            item.name,
            item.meta?.shop || "",
            item.meta?.type || "",
            item.error || "",
        ]),
    ];
    const csv = rows
        .map((row) =>
            row
                .map((cell) => `"${String(cell).replace(/"/g, '""')}"`)
                .join(","),
        )
        .join("\n");
    const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `上传失败清单_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
}
</script>

<style scoped lang="scss">
.page-container {
    width: 100%;
}

.upload-shell {
    display: grid;
    gap: 14px;
    align-items: start;
}

.upload-shell--embedded {
    gap: 12px;
}

.upload-main-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 308px;
    gap: 14px;
    align-items: start;
    min-width: 0;
}

.naming-rule-panel {
    display: grid;
    min-width: 0;
    padding: 0;
}

.upload-rule-board {
    position: relative;
    display: grid;
    grid-template-columns: minmax(340px, 0.82fr) minmax(430px, 1.18fr);
    align-items: stretch;
    gap: 14px;
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
    box-shadow: var(--shadow-card);

    &::after {
        content: none;
    }

    h2 {
        position: relative;
        z-index: 1;
        margin: 0;
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 800;
        line-height: 1.2;
    }
}

.rule-board-main {
    display: grid;
    align-content: start;
    gap: 12px;
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--border-color-light);
    border-radius: calc(var(--radius-card) - 2px);
    background: var(--bg-elevated);
}

.rule-heading {
    display: grid;
    gap: 6px;
    min-width: 0;

    p {
        margin: 0;
        color: var(--text-secondary);
        font-size: 12px;
        line-height: 1.55;
    }
}

.rule-code-line {
    position: relative;
    z-index: 1;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-start;
    gap: 5px;
    max-width: 100%;
    min-height: 46px;
    padding: 8px 10px;
    border: 1px solid var(--border-color-light);
    border-radius: 10px;
    background: var(--bg-card);
}

.rule-token,
.rule-extension,
.rule-separator {
    font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
    font-size: 12px;
    font-weight: 800;
    line-height: 1.25;
}

.rule-token {
    display: inline-flex;
    align-items: center;
    min-height: 26px;
    padding: 4px 8px;
    border-radius: 8px;
    border: 1px solid transparent;
}

.rule-token--date {
    border-color: var(--border-color-light);
    background: var(--bg-card);
    color: var(--text-secondary);
}

.rule-token--type {
    border-color: var(--border-color-light);
    background: var(--bg-card);
    color: var(--text-secondary);
}

.rule-token--shop {
    border-color: var(--border-color-light);
    background: var(--bg-card);
    color: var(--text-secondary);
}

.rule-extension,
.rule-separator {
    color: var(--text-tertiary);
}

.rule-meta {
    display: grid;
    gap: 7px;
    min-width: 0;
}

.rule-example {
    position: relative;
    z-index: 1;
    margin: 0;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.6;

    code {
        color: var(--code-text);
        font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
        font-size: 12px;
        font-weight: 700;
        overflow-wrap: anywhere;
    }
}

.rule-hint-list {
    position: relative;
    z-index: 1;
    display: flex;
    flex-wrap: wrap;
    gap: 5px;

    span {
        display: inline-flex;
        align-items: center;
        min-height: 22px;
        padding: 2px 7px;
        border: 1px solid var(--surface-border);
        border-radius: 999px;
        background: var(--bg-card);
        color: var(--text-secondary);
        font-size: 11px;
        font-weight: 600;
    }
}

.rule-platforms {
    display: grid;
    gap: 10px;
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--border-color-light);
    border-radius: calc(var(--radius-card) - 2px);
    background: var(--bg-card);
}

.rule-platforms-heading {
    margin-bottom: 0;
}

.upload-workspace {
    display: grid;
    gap: 10px;
    min-width: 0;
}

.upload-steps {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    overflow: hidden;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
}

.upload-step {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    min-height: 40px;
    padding: 0 12px;
    border-right: 1px solid var(--border-color-light);
    color: var(--text-tertiary);
    font-size: 13px;
    font-weight: 600;

    &:last-child {
        border-right: 0;
    }

    strong {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border: 1px solid var(--border-light);
        border-radius: var(--radius-sm);
        color: var(--text-secondary);
        font-size: 12px;
        font-weight: 700;
    }

    span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    &.is-active {
        color: var(--text-primary);
        background: var(--primary-light-9);

        strong {
            border-color: var(--primary);
            background: var(--primary);
            color: var(--primary-contrast);
        }
    }
}

.section-kicker {
    display: block;
    margin-bottom: 4px;
    color: var(--text-tertiary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0;
}

.operation-heading,
.reference-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;

    h3 {
        margin: 0;
        color: var(--text-primary);
        font-size: 17px;
        font-weight: 700;
        line-height: 1.25;
    }
}

.file-counter {
    flex-shrink: 0;
    padding: 5px 10px;
    border-radius: 999px;
    background: var(--bg-elevated);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 700;
}

.upload-card {
    :deep(.el-card__body) {
        padding: 14px;
    }
}

.drop-zone {
    position: relative;
    overflow: hidden;
    min-height: 190px;
    border: 1px dashed var(--border-color);
    border-radius: var(--radius-card);
    padding: 28px 18px;
    text-align: center;
    cursor: pointer;
    transition:
        border-color 0.18s,
        background-color 0.18s,
        box-shadow 0.18s,
        transform 0.18s;
    background: var(--bg-card);

    &:hover {
        border-color: var(--input-hover-border);
        box-shadow: none;
    }

    &--active {
        border-color: var(--input-hover-border);
        border-style: solid;
        background: var(--bg-hover);
        box-shadow: none;
        animation: none;
    }

    &--scanning {
        border-color: var(--input-hover-border);
        border-style: solid;
    }

    .scan-line {
        position: absolute;
        left: 5%;
        right: 5%;
        top: -18px;
        height: 18px;
        border-radius: var(--radius-sm);
        background: var(--primary-light-5);
        filter: none;
        opacity: 0.72;
        animation: scan-line 0.5s ease-in-out infinite;
        pointer-events: none;
    }

    .drop-zone-text {
        margin: 12px 0 5px;
        color: var(--text-primary);
        font-size: 15px;
        font-weight: 700;

        em {
            color: var(--text-secondary);
            font-style: normal;
            font-weight: 800;
            margin-left: 6px;
        }
    }

    .drop-zone-hint {
        font-size: 12px;
        color: var(--text-tertiary);
    }
}

.drop-zone-content {
    position: relative;
    z-index: 1;
}

.upload-illustration {
    position: relative;
    width: 82px;
    height: 76px;
    margin: 0 auto;

    .file-layer {
        position: absolute;
        display: block;
        border-radius: 12px;
        border: 1px solid var(--border-color-light);
        box-shadow: none;
    }

    .file-layer--back {
        left: 12px;
        top: 8px;
        width: 56px;
        height: 60px;
        background: var(--bg-elevated);
        transform: rotate(-9deg);
    }

    .file-layer--front {
        left: 22px;
        top: 0;
        width: 54px;
        height: 68px;
        padding: 16px 10px;
        background: var(--bg-card);

        span {
            display: block;
            height: 4px;
            margin-bottom: 8px;
            border-radius: 999px;
            background: var(--border-color);

            &:nth-child(2) {
                width: 72%;
                background: var(--border-color);
            }

            &:nth-child(3) {
                width: 52%;
            }
        }
    }

    .el-icon {
        position: absolute;
        right: 2px;
        bottom: 0;
        width: 31px;
        height: 31px;
        border-radius: 50%;
        background: var(--bg-elevated);
        color: var(--primary);
        font-size: 18px;
        border: 1px solid var(--border-color-light);
        box-shadow: none;
    }
}

.file-list-card {
    :deep(.el-card__body) {
        padding: 0;
    }

    :deep(.el-card__header) {
        display: grid;
        gap: 12px;
    }

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;

        &-title {
            display: block;
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            line-height: 1.2;
        }

        &-actions {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 8px;
        }
    }
}

.card-header-main {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
}

.file-table {
    border-radius: 0;
}

.upload-confirm-summary {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin: 14px 0 12px;
}

.upload-confirm-stat {
    display: grid;
    gap: 4px;
    padding: 10px 12px;
    border: 1px solid var(--border-color-light);
    border-radius: 10px;
    background: var(--bg-elevated);

    span {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 600;
    }

    strong {
        color: var(--text-primary);
        font-size: 16px;
        font-weight: 700;
        line-height: 1.2;
    }
}

.upload-confirm-note {
    margin-bottom: 12px;
    padding: 10px 12px;
    border: 1px solid var(--warning-light-7);
    border-radius: 10px;
    background: var(--warning-light-9);
    color: var(--warning-dark-2);
    font-size: 12px;
    line-height: 1.6;
}

.upload-confirm-table {
    :deep(.el-table__cell) {
        vertical-align: top;
    }
}

.shop-cell {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-width: 0;

    .el-icon {
        flex-shrink: 0;
        color: var(--primary);
        font-size: 15px;
    }

    strong {
        overflow: hidden;
        color: var(--text-primary);
        font-weight: 700;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
}

.soft-badge,
.status-pill,
.check-pill {
    border-radius: 999px !important;
}

.check-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    max-width: 100%;
    padding: 4px 10px;
    border: 1px solid transparent;
    font-size: 12px;
    font-weight: 700;
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.check-pill--success {
    border-color: var(--border-color-light);
    background: var(--bg-elevated);
    color: var(--success);
    box-shadow: none;
}

.check-pill--error {
    border-color: var(--border-color-light);
    background: var(--bg-elevated);
    color: var(--error);
}

.check-dot {
    width: 6px;
    height: 6px;
    flex-shrink: 0;
    border-radius: 50%;
    background: currentColor;
}

.status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 64px;
    padding: 4px 10px;
    background: var(--bg-hover);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 700;
}

.status-pill--warning {
    background: var(--warning-light);
    color: var(--warning);
}

.status-pill--success {
    background: var(--bg-elevated);
    color: var(--success);
    box-shadow: none;
}

.status-pill--error {
    background: var(--error-light);
    color: var(--error);
}

.file-skeleton-list {
    display: grid;
    gap: 0;
    padding: 8px 0;
}

.file-skeleton-row {
    display: grid;
    grid-template-columns: minmax(180px, 1.7fr) 0.6fr 1fr 0.7fr;
    gap: 18px;
    align-items: center;
    min-height: 58px;
    padding: 0 18px;
    border-bottom: 1px solid var(--border-color-light);
}

.skeleton-block {
    display: block;
    height: 13px;
    border-radius: 999px;
    background: var(--bg-hover);
    animation: pulse 1.2s ease-in-out infinite;
}

.skeleton-name {
    width: 82%;
}

.skeleton-short {
    width: 52%;
}

.skeleton-medium {
    width: 70%;
}

.skeleton-badge {
    width: 62px;
    height: 24px;
}

.file-empty-state {
    display: grid;
    place-items: center;
    gap: 10px;
    min-height: 160px;
    color: var(--text-tertiary);

    p {
        margin: 0;
        font-size: 13px;
    }
}

.empty-illustration {
    position: relative;
    width: 54px;
    height: 62px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-lg);
    background: var(--bg-elevated);

    span {
        position: absolute;
        left: 12px;
        right: 12px;
        top: 22px;
        height: 4px;
        border-radius: 999px;
        background: var(--primary-light-5);

        &::before,
        &::after {
            content: "";
            position: absolute;
            left: 0;
            height: 4px;
            border-radius: inherit;
            background: inherit;
        }

        &::before {
            top: 10px;
            width: 80%;
        }

        &::after {
            top: 20px;
            width: 58%;
        }
    }
}

.queue-state {
    flex-shrink: 0;
    padding: 5px 10px;
    border-radius: 999px;
    background: var(--bg-elevated);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 700;
}

.queue-state--running {
    background: var(--primary-light-9);
    color: var(--primary);
}

.queue-stat-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 8px;
}

.queue-inline-panel {
    display: grid;
    gap: 9px;
    padding: 10px;
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-card);
    background: var(--bg-elevated);
}

.queue-stat {
    display: grid;
    gap: 4px;
    min-width: 0;
    padding: 8px 10px;
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-sm);
    background: var(--bg-card);

    span {
        color: var(--text-tertiary);
        font-size: 11px;
        font-weight: 700;
    }

    strong {
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 800;
        line-height: 1;
    }
}

.queue-stat--success strong {
    color: var(--success);
}

.queue-stat--error strong {
    color: var(--error);
}

.queue-summary {
    min-width: 0;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.6;
}

.reference-panel {
    position: sticky;
    top: 0;
    display: grid;
    gap: 10px;
    padding: 12px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
    box-shadow: var(--shadow-card);
    backdrop-filter: none;
    min-width: 0;

    .reference-heading {
        margin-bottom: 0;

        .el-icon {
            color: var(--text-tertiary);
            font-size: 18px;
        }
    }
}

:global(html.dark) .reference-panel {
    border-color: var(--border-light);
    background: var(--bg-card);
}

.upload-shell--embedded {
    .upload-rule-board,
    .upload-main-grid {
        grid-template-columns: minmax(0, 1fr);
    }

    .upload-rule-board,
    .rule-board-main,
    .rule-platforms,
    .reference-panel {
        padding: 12px;
    }

    .rule-heading p,
    .rule-example,
    .platform-card p {
        font-size: 11px;
    }

    .platform-card-list {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .reference-panel {
        position: static;
    }

    .drop-zone {
        min-height: 168px;
        padding: 22px 14px;
    }

    .file-list-card .card-header,
    .reference-heading {
        align-items: flex-start;
        flex-direction: column;
    }
}

.naming-assistant,
.platform-card,
.check-note {
    border-radius: var(--radius-card);
}

.naming-assistant {
    display: grid;
    gap: 9px;
    min-width: 0;
    padding: 0;
}

.naming-fields {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
    align-items: end;

    .naming-field:last-child {
        grid-column: auto;
    }
}

.naming-field {
    display: grid;
    gap: 6px;
    min-width: 0;

    > span {
        color: var(--text-secondary);
        font-size: 11px;
        font-weight: 700;
    }

    :deep(.el-date-editor.el-input),
    :deep(.el-select),
    :deep(.el-autocomplete),
    :deep(.el-input) {
        width: 100%;
    }
}

.generated-name-button {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    width: 100%;
    min-width: 0;
    min-height: 38px;
    padding: 8px 10px;
    border: 1px dashed var(--surface-border);
    border-radius: calc(var(--radius-card) - 2px);
    background: var(--bg-card);
    color: var(--text-tertiary);
    text-align: left;
    cursor: not-allowed;
    transition:
        border-color 0.18s,
        box-shadow 0.18s,
        color 0.18s,
        transform 0.18s;

    strong {
        min-width: 0;
        color: currentColor;
        font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
        font-size: 12px;
        font-weight: 700;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }

    .el-icon {
        flex: 0 0 auto;
        color: currentColor;
        font-size: 17px;
    }

    &--ready {
        border-style: solid;
        border-color: var(--input-hover-border);
        color: var(--text-primary);
        cursor: pointer;
        box-shadow: none;

        &:hover {
            transform: translateY(-1px);
            border-color: var(--primary);
            box-shadow: none;
        }
    }
}

.shop-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-width: 0;

    span {
        overflow: hidden;
        color: var(--text-primary);
        font-weight: 600;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    small {
        flex: 0 0 auto;
        color: var(--text-tertiary);
        font-size: 11px;
    }
}

.platform-card-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
}

.platform-card {
    display: grid;
    gap: 7px;
    min-width: 0;
    padding: 9px 10px;
    border: 1px solid var(--border-color-light);
    background: var(--bg-elevated);

    h4 {
        margin: 0 0 7px;
        color: var(--text-primary);
        font-size: 14px;
        font-weight: 700;
    }

    p {
        margin: 0;
        color: var(--text-tertiary);
        font-size: 11px;
        line-height: 1.35;
        word-break: break-all;
    }
}

.platform-card-line {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    overflow: hidden;
}

.type-list {
    display: flex;
    flex-wrap: nowrap;
    gap: 4px;
    min-width: 0;
    overflow: hidden;
}

.platform-example {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.check-note {
    display: flex;
    gap: 8px;
    padding: 11px;
    color: var(--text-secondary);
    font-size: 11px;
    line-height: 1.6;
}

.check-note-dot {
    width: 7px;
    height: 7px;
    flex: 0 0 auto;
    margin-top: 7px;
    border-radius: 50%;
    background: var(--success);
    box-shadow: none;
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

:global(.el-message-box.upload-validation-message-box) {
    width: min(1120px, calc(100vw - 96px));
    width: min(1120px, calc(100vw - 96px)) !important;
    max-width: calc(100vw - 32px);
    max-width: calc(100vw - 32px) !important;

    .el-message-box__status {
        background: var(--warning-light);
    }
}

:global(.upload-validation-dialog) {
    display: grid;
    gap: 12px;
    min-width: 0;
}

:global(.upload-validation-dialog__intro),
:global(.upload-validation-dialog__more) {
    margin: 0;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.6;
}

:global(.upload-validation-dialog__list) {
    display: grid;
    gap: 8px;
    max-height: 320px;
    overflow: auto;
}

:global(.upload-validation-dialog__item) {
    display: grid;
    grid-template-columns: minmax(0, 1fr) max-content;
    align-items: center;
    gap: 24px;
    min-width: 0;
    padding: 10px 12px;
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-sm);
    background: var(--bg-elevated);
}

:global(.upload-validation-dialog__name) {
    min-width: 0;
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 700;
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

:global(.upload-validation-dialog__message) {
    color: var(--error);
    font-size: 12px;
    line-height: 1.55;
    white-space: nowrap;
}

.upload-blocking-mask {
    position: fixed;
    inset: 0;
    z-index: 3000;
    display: grid;
    place-items: center;
    padding: 20px;
    background: rgba(15, 23, 42, 0.56);
    backdrop-filter: blur(2px);
}

.upload-blocking-card {
    display: grid;
    gap: 14px;
    width: min(460px, 100%);
    padding: 22px 22px 20px;
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
    box-shadow: var(--shadow-card);

    h3 {
        margin: 0;
        color: var(--text-primary);
        font-size: 20px;
        font-weight: 700;
        line-height: 1.3;
    }

    p {
        margin: -6px 0 0;
        color: var(--text-secondary);
        font-size: 13px;
        line-height: 1.7;
    }
}

.upload-blocking-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: fit-content;
    min-height: 28px;
    padding: 0 10px;
    border-radius: 999px;
    background: var(--primary-light-9);
    color: var(--primary);
    font-size: 12px;
    font-weight: 700;
}

.upload-blocking-meta {
    display: grid;
    gap: 4px;

    span {
        color: var(--text-tertiary);
        font-size: 11px;
        font-weight: 700;
    }

    strong {
        color: var(--text-primary);
        font-size: 13px;
        font-weight: 700;
        line-height: 1.5;
        overflow-wrap: anywhere;
    }
}

@keyframes scan-line {
    0% {
        transform: translateY(0);
        opacity: 0;
    }

    15%,
    85% {
        opacity: 0.9;
    }

    100% {
        transform: translateY(250px);
        opacity: 0;
    }
}

@media (max-width: 1180px) {
    .upload-main-grid,
    .upload-rule-board {
        grid-template-columns: minmax(0, 1fr);
    }

    .rule-code-line {
        justify-content: flex-start;
    }

    .naming-fields {
        grid-template-columns: 1fr;
    }

    .reference-panel {
        position: static;
    }

    .platform-card-list {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .queue-stat-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

@media (max-width: 768px) {
    :global(.upload-validation-dialog__item) {
        grid-template-columns: 1fr;
        align-items: start;
        gap: 5px;
    }

    :global(.upload-validation-dialog__name),
    :global(.upload-validation-dialog__message) {
        overflow-wrap: anywhere;
        white-space: normal;
    }

    .operation-heading,
    .reference-heading,
    .file-list-card .card-header,
    .card-header-main {
        align-items: flex-start;
        flex-direction: column;
    }

    .naming-fields {
        grid-template-columns: 1fr;
    }

    .platform-card-line {
        align-items: center;
        flex-direction: row;
    }

    .upload-rule-board,
    .rule-board-main,
    .rule-platforms {
        padding: 14px;
    }

    .rule-code-line {
        justify-content: flex-start;
    }

    .upload-steps {
        grid-template-columns: 1fr;
    }

    .upload-step {
        border-right: 0;
        border-bottom: 1px solid var(--border-color-light);

        &:last-child {
            border-bottom: 0;
        }
    }

    .drop-zone {
        min-height: 188px;
        padding: 28px 14px;
    }

    .platform-card-list {
        grid-template-columns: 1fr;
    }

    .queue-stat-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .file-skeleton-row {
        grid-template-columns: 1fr;
        gap: 9px;
        padding: 14px 16px;
    }
}

@media (prefers-reduced-motion: reduce) {
    .drop-zone--active,
    .scan-line,
    .skeleton-block {
        animation: none;
    }
}
</style>
