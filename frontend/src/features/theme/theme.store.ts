import { create } from 'zustand'

const THEME_STORAGE_KEY = 'AGENTFORGE_THEME'

export type ThemeMode = 'light' | 'dark' | 'summer'

interface ThemeStoreState {
  theme: ThemeMode
  setTheme: (theme: ThemeMode) => void
}

function isThemeMode(value: string | null): value is ThemeMode {
  return value === 'light' || value === 'dark' || value === 'summer'
}

function readStoredTheme(): ThemeMode {
  if (typeof window === 'undefined') {
    return 'light'
  }
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
  return isThemeMode(stored) ? stored : 'light'
}

function writeStoredTheme(theme: ThemeMode): void {
  if (typeof window === 'undefined') {
    return
  }
  window.localStorage.setItem(THEME_STORAGE_KEY, theme)
}

export function applyTheme(theme: ThemeMode): void {
  if (typeof document === 'undefined') {
    return
  }
  document.documentElement.dataset.theme = theme
  document.documentElement.style.colorScheme = theme === 'dark' ? 'dark' : 'light'
}

export const useThemeStore = create<ThemeStoreState>((set) => ({
  theme: readStoredTheme(),
  setTheme: (theme) => {
    writeStoredTheme(theme)
    set(() => ({ theme }))
  },
}))

applyTheme(readStoredTheme())
