<template>
    <div class="search-card-head">
        <div>
            <p class="search-card-kicker">{{ kicker }}</p>
            <h2 class="search-card-title">{{ title }}</h2>
        </div>
        <div v-if="tip" class="search-card-tip">
            <span>{{ tip }}</span>
        </div>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "SearchCardIntro" });

defineProps<{
    kicker: string;
    title: string;
    tip?: string;
}>();
</script>
