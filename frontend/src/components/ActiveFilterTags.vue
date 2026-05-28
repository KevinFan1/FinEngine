<template>
  <span v-if="false" />
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
</script>
