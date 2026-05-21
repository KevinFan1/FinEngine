<template>
  <div v-if="tags.length" class="active-filters">
    <span class="active-filters-label">当前筛选</span>
    <el-tag
      v-for="tag in tags"
      :key="tagKey(tag)"
      closable
      class="filter-tag"
      @close="$emit('remove', tag)"
    >
      {{ tag.label }}：{{ tag.value }}
    </el-tag>
    <el-button link class="clear-filters-btn" @click="$emit('clear')">清空全部</el-button>
  </div>
</template>

<script setup lang="ts">
import type { ActiveFilterTag } from "./activeFilterTags";

defineProps<{
  tags: ActiveFilterTag[]
}>()

defineEmits<{
  remove: [tag: ActiveFilterTag]
  clear: []
}>()

function tagKey(tag: ActiveFilterTag) {
  return `${tag.key}-${tag.value}`
}
</script>
