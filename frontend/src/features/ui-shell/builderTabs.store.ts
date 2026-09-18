import { create } from 'zustand'

import { BUILDER_TAB_REGISTRY, getCapabilityMeta } from './builderTabs.registry'
import type { BuilderTab, BuilderTabState, BuilderTabType } from './builderTabs.types'

function makeTabId(type: BuilderTabType): string {
  return `${type}:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`
}

function createTab(
  type: BuilderTabType,
  input?: {
    title?: string
    icon?: string
    closable?: boolean
    status?: BuilderTabState['status']
    message?: string | null
    resourceId?: string | null
    params?: Record<string, unknown> | null
  },
): BuilderTab {
  const meta = getCapabilityMeta(type)
  return {
    id: makeTabId(type),
    type,
    title: input?.title ?? meta.title,
    icon: input?.icon ?? meta.icon,
    closable: input?.closable ?? meta.defaultClosable,
    state: {
      status: input?.status ?? 'idle',
      message: input?.message ?? null,
    },
    createdAt: Date.now(),
    resourceId: input?.resourceId ?? null,
    params: input?.params ?? null,
  }
}

interface OpenTabInput {
  type: BuilderTabType
  title?: string
  icon?: string
  status?: BuilderTabState['status']
  message?: string | null
  resourceId?: string | null
  params?: Record<string, unknown> | null
  forceNew?: boolean
}

interface BuilderTabsState {
  tabs: BuilderTab[]
  activeTabId: string
  openTab: (input: OpenTabInput) => string
  openCapabilityTab: (type: BuilderTabType) => string | null
  selectCapabilityInActiveTab: (type: BuilderTabType) => string | null
  openOrFocusNewTab: () => string
  openRunLogsTab: (input?: { stepIndex?: number | null; executionId?: string | null }) => string
  setActiveTab: (tabId: string) => void
  renameTab: (tabId: string, title: string) => void
  setTabState: (tabId: string, state: BuilderTabState) => void
  setTabStateByType: (type: BuilderTabType, state: BuilderTabState) => void
  closeTab: (tabId: string) => void
}

const initialAgentConfigTab = createTab('agent_config', {
  status: 'idle',
  message: '以智能体人设与配置为中心',
  closable: false,
})

export const useBuilderTabsStore = create<BuilderTabsState>((set, get) => ({
  tabs: [initialAgentConfigTab],
  activeTabId: initialAgentConfigTab.id,

  openTab: (input) => {
    const meta = BUILDER_TAB_REGISTRY[input.type]
    const state = get()
    if (!input.forceNew && meta.singleton) {
      const existing = state.tabs.find((tab) => tab.type === input.type)
      if (existing) {
        const mergedParams = input.params ? { ...(existing.params ?? {}), ...input.params } : existing.params
        set((prev) => ({
          tabs: prev.tabs.map((tab) =>
            tab.id === existing.id
              ? {
                  ...tab,
                  title: input.title ?? tab.title,
                  icon: input.icon ?? tab.icon,
                  resourceId: input.resourceId ?? tab.resourceId ?? null,
                  params: mergedParams ?? null,
                }
              : tab,
          ),
          activeTabId: existing.id,
        }))
        return existing.id
      }
    }

    const newTab = createTab(input.type, {
      title: input.title,
      icon: input.icon,
      status: input.status,
      message: input.message,
      resourceId: input.resourceId,
      params: input.params,
    })
    set((prev) => ({
      tabs: [...prev.tabs, newTab],
      activeTabId: newTab.id,
    }))
    return newTab.id
  },

  openCapabilityTab: (type) => {
    const meta = BUILDER_TAB_REGISTRY[type]
    if (!meta.enabled) {
      return null
    }
    return get().openTab({ type })
  },

  selectCapabilityInActiveTab: (type) => {
    const meta = BUILDER_TAB_REGISTRY[type]
    if (!meta.enabled) {
      return null
    }

    const state = get()
    const activeTab = state.tabs.find((tab) => tab.id === state.activeTabId)
    if (!activeTab || activeTab.type !== 'new_tab') {
      return state.openTab({ type })
    }

    const singletonTab = meta.singleton ? state.tabs.find((tab) => tab.type === type && tab.id !== activeTab.id) : null
    if (singletonTab) {
      const filtered = state.tabs.filter((tab) => tab.id !== activeTab.id)
      set(() => ({
        tabs: filtered,
        activeTabId: singletonTab.id,
      }))
      return singletonTab.id
    }

    set((prev) => ({
      tabs: prev.tabs.map((tab) =>
        tab.id === activeTab.id
          ? {
              ...tab,
              type,
              title: meta.title,
              icon: meta.icon,
              closable: meta.defaultClosable,
              state: { status: 'ready', message: '已打开' },
              resourceId: null,
              params: null,
            }
          : tab,
      ),
      activeTabId: activeTab.id,
    }))
    return activeTab.id
  },

  openOrFocusNewTab: () => {
    return get().openTab({ type: 'new_tab', forceNew: true })
  },

  openRunLogsTab: (input) => {
    return get().openTab({
      type: 'run_logs',
      resourceId: input?.executionId ?? null,
      params: { stepIndex: input?.stepIndex ?? null },
    })
  },

  setActiveTab: (tabId) => {
    const exists = get().tabs.some((tab) => tab.id === tabId)
    if (!exists) {
      return
    }
    set(() => ({ activeTabId: tabId }))
  },

  renameTab: (tabId, title) => {
    const trimmed = title.trim()
    if (trimmed.length === 0) {
      return
    }
    set((state) => ({
      tabs: state.tabs.map((tab) => (tab.id === tabId ? { ...tab, title: trimmed } : tab)),
    }))
  },

  setTabState: (tabId, state) => {
    set((prev) => ({
      tabs: prev.tabs.map((tab) => (tab.id === tabId ? { ...tab, state } : tab)),
    }))
  },

  setTabStateByType: (type, state) => {
    set((prev) => ({
      tabs: prev.tabs.map((tab) => (tab.type === type ? { ...tab, state } : tab)),
    }))
  },

  closeTab: (tabId) => {
    const state = get()
    const closingTab = state.tabs.find((tab) => tab.id === tabId)
    if (!closingTab || !closingTab.closable) {
      return
    }

    const closedIndex = state.tabs.findIndex((tab) => tab.id === tabId)
    const nextTabs = state.tabs.filter((tab) => tab.id !== tabId)
    if (nextTabs.length === 0) {
      const fallback = createTab('new_tab')
      set(() => ({
        tabs: [fallback],
        activeTabId: fallback.id,
      }))
      return
    }

    const nextActiveId =
      state.activeTabId === tabId
        ? nextTabs[closedIndex]?.id ?? nextTabs[closedIndex - 1]?.id ?? nextTabs[0].id
        : state.activeTabId
    set(() => ({
      tabs: nextTabs,
      activeTabId: nextActiveId,
    }))
  },
}))
