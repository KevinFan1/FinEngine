<template>
  <span class="brand-logo" :style="logoStyle" aria-hidden="true"></span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  size?: number
}>(), {
  size: 32,
})

const logoStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
}))
</script>

<style scoped lang="scss">
.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
  border-radius: inherit;
  background-image: url('/brand/finengine-logo.svg');
  background-position: center;
  background-repeat: no-repeat;
  background-size: contain;
}
</style>
