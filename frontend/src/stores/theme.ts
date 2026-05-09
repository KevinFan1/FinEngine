import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark'

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>((localStorage.getItem('theme') as ThemeMode) || 'light')

  function toggleTheme() {
    mode.value = mode.value === 'light' ? 'dark' : 'light'
  }

  function setTheme(newMode: ThemeMode) {
    mode.value = newMode
  }

  /** Apply theme to document */
  function applyTheme() {
    const html = document.documentElement

    if (mode.value === 'dark') {
      html.classList.add('dark')
    } else {
      html.classList.remove('dark')
    }

    // Persist
    localStorage.setItem('theme', mode.value)
  }

  // Watch and auto-apply
  watch(mode, () => {
    applyTheme()
  }, { immediate: true })

  return { mode, toggleTheme, setTheme, applyTheme }
})
