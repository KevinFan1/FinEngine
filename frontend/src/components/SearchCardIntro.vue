<template>
    <div class="search-card-head">
        <div>
            <p v-if="showKicker" class="search-card-kicker">{{ kicker }}</p>
            <h2 class="search-card-title">{{ heading }}</h2>
        </div>
        <div v-if="tip" class="search-card-tip">
            <span>{{ tip }}</span>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

defineOptions({ name: "SearchCardIntro" });

const props = defineProps<{
    kicker?: string;
    title?: string;
    tip?: string;
}>();

const heading = computed(() => props.title || props.kicker || "");
const showKicker = computed(() => Boolean(props.kicker && props.title));
</script>

<style scoped lang="scss">
.search-card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 20px;
    min-width: 0;
}

.search-card-kicker {
    margin: 0 0 4px;
    color: var(--el-color-primary);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.08em;
}

.search-card-title {
    margin: 0;
    color: var(--text-primary);
    font-size: 18px;
    font-weight: 700;
    line-height: 1.3;
}

.search-card-tip {
    display: flex;
    align-items: center;
    max-width: 320px;
    min-width: 0;
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 500;
    line-height: 1.5;
}

.search-card-tip span {
    min-width: 0;
}

@media (max-width: 768px) {
    .search-card-head {
        flex-direction: column;
        gap: 10px;
    }
}
</style>
