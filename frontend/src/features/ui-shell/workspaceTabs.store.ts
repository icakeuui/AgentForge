import { create } from 'zustand'

import type {
  BrowserLinkItem,
  CanvasPinItem,
  CodeChangeItem,
  MainTabId,
  OpenFileTab,
  TerminalCommandItem,
  WorkspaceJumpTarget,
} from './workspaceTabs.types'
import type { ExecutionStatus } from '../execution/execution.types'

type TabSource = 'user' | 'system'

interface WorkspaceTabsState {
  activeMainTab: MainTabId
  userPinnedMainTab: boolean
  lastExecutionFocusKey: string | null
  documents: {
    openFiles: OpenFileTab[]
    activeFileId: string | null
  }
  browser: {
    links: BrowserLinkItem[]
    activeUrl: string | null
  }
  terminal: {
    commandHistory: TerminalCommandItem[]
  }
  codeChanges: {
    items: CodeChangeItem[]
    activeItemId: string | null
  }
  canvas: {
    pins: CanvasPinItem[]
  }
  reactFlow: {
    focusedStepIndex: number | null
  }
  setActiveMainTab: (tab: MainTabId, source?: TabSource) => void
  syncExecutionFocus: (status: ExecutionStatus, executionId: string | null) => void
  openFile: (file: Omit<OpenFileTab, 'id' | 'title'> & Partial<Pick<OpenFileTab, 'id' | 'title'>>) => void
  closeFile: (fileId: string) => void
  selectBrowserLink: (link: Omit<BrowserLinkItem, 'id' | 'title'> & Partial<Pick<BrowserLinkItem, 'id' | 'title'>>) => void
  addTerminalCommand: (command: Omit<TerminalCommandItem, 'id'> & Partial<Pick<TerminalCommandItem, 'id'>>) => void
  addCodeChange: (item: Omit<CodeChangeItem, 'id' | 'title'> & Partial<Pick<CodeChangeItem, 'id' | 'title'>>) => void
  addCanvasPin: (pin: Omit<CanvasPinItem, 'id' | 'title'> & Partial<Pick<CanvasPinItem, 'id' | 'title'>>) => void
  focusReactStep: (stepIndex: number | null) => void
  jumpTo: (target: WorkspaceJumpTarget) => void
}

function stableId(prefix: string, value: string): string {
  return `${prefix}:${value}`
}

function fileTitle(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean)
  return parts.at(-1) ?? path
}

function linkTitle(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

function upsertById<T extends { id: string }>(items: T[], nextItem: T): T[] {
  const existingIndex = items.findIndex((item) => item.id === nextItem.id)
  if (existingIndex < 0) {
    return [...items, nextItem]
  }
  const nextItems = [...items]
  nextItems[existingIndex] = {
    ...nextItems[existingIndex],
    ...nextItem,
  }
  return nextItems
}

export const useWorkspaceTabsStore = create<WorkspaceTabsState>((set, get) => ({
  activeMainTab: 'agent',
  userPinnedMainTab: false,
  lastExecutionFocusKey: null,
  documents: {
    openFiles: [],
    activeFileId: null,
  },
  browser: {
    links: [],
    activeUrl: null,
  },
  terminal: {
    commandHistory: [],
  },
  codeChanges: {
    items: [],
    activeItemId: null,
  },
  canvas: {
    pins: [],
  },
  reactFlow: {
    focusedStepIndex: null,
  },

  setActiveMainTab: (tab, source = 'user') => {
    set(() => ({
      activeMainTab: tab,
      userPinnedMainTab: source === 'user',
    }))
  },

  syncExecutionFocus: (status, executionId) => {
    const state = get()
    const focusKey = executionId ?? `transient:${status}`
    const isNewExecution = state.lastExecutionFocusKey !== focusKey && status !== 'IDLE'

    if (isNewExecution) {
      set(() => ({
        activeMainTab: status === 'PENDING' || status === 'RUNNING' || status === 'FAILED' ? 'react-flow' : 'agent',
        userPinnedMainTab: false,
        lastExecutionFocusKey: focusKey,
        reactFlow: {
          focusedStepIndex: status === 'FAILED' ? state.reactFlow.focusedStepIndex : null,
        },
      }))
      return
    }

    if (state.userPinnedMainTab) {
      return
    }

    if (status === 'PENDING' || status === 'RUNNING' || status === 'FAILED') {
      set(() => ({
        activeMainTab: 'react-flow',
      }))
    }
  },

  openFile: (file) => {
    const id = file.id ?? stableId('file', file.path)
    const nextFile: OpenFileTab = {
      id,
      title: file.title ?? fileTitle(file.path),
      path: file.path,
      kind: file.kind,
      previewText: file.previewText ?? null,
      source: file.source ?? null,
    }

    set((state) => ({
      activeMainTab: 'documents',
      userPinnedMainTab: true,
      documents: {
        openFiles: upsertById(state.documents.openFiles, nextFile),
        activeFileId: id,
      },
    }))
  },

  closeFile: (fileId) => {
    set((state) => {
      const currentIndex = state.documents.openFiles.findIndex((file) => file.id === fileId)
      const openFiles = state.documents.openFiles.filter((file) => file.id !== fileId)
      const activeFileId =
        state.documents.activeFileId !== fileId
          ? state.documents.activeFileId
          : openFiles[currentIndex]?.id ?? openFiles[currentIndex - 1]?.id ?? openFiles[0]?.id ?? null

      return {
        documents: {
          openFiles,
          activeFileId,
        },
      }
    })
  },

  selectBrowserLink: (link) => {
    const id = link.id ?? stableId('url', link.url)
    const nextLink: BrowserLinkItem = {
      id,
      title: link.title ?? linkTitle(link.url),
      url: link.url,
      snippet: link.snippet ?? null,
      source: link.source ?? null,
    }

    set((state) => ({
      activeMainTab: 'browser',
      userPinnedMainTab: true,
      browser: {
        links: upsertById(state.browser.links, nextLink),
        activeUrl: nextLink.url,
      },
    }))
  },

  addTerminalCommand: (command) => {
    const id = command.id ?? stableId('command', command.command)
    const nextCommand: TerminalCommandItem = {
      id,
      command: command.command,
      title: command.title ?? null,
      source: command.source ?? null,
    }

    set((state) => ({
      activeMainTab: 'terminal',
      userPinnedMainTab: true,
      terminal: {
        commandHistory: upsertById(state.terminal.commandHistory, nextCommand),
      },
    }))
  },

  addCodeChange: (item) => {
    const id = item.id ?? stableId('change', item.path ?? item.summary ?? 'untracked')
    const nextItem: CodeChangeItem = {
      id,
      title: item.title ?? (item.path ? fileTitle(item.path) : '变更摘要'),
      path: item.path ?? null,
      summary: item.summary ?? null,
      additions: item.additions ?? null,
      deletions: item.deletions ?? null,
      source: item.source ?? null,
    }

    set((state) => ({
      activeMainTab: 'code-changes',
      userPinnedMainTab: true,
      codeChanges: {
        items: upsertById(state.codeChanges.items, nextItem),
        activeItemId: id,
      },
    }))
  },

  addCanvasPin: (pin) => {
    const id = pin.id ?? stableId('pin', `${pin.type}:${pin.title ?? pin.summary ?? Date.now()}`)
    const nextPin: CanvasPinItem = {
      id,
      type: pin.type,
      title: pin.title ?? '固定内容',
      summary: pin.summary ?? null,
      target: pin.target ?? null,
    }

    set((state) => ({
      activeMainTab: 'canvas',
      userPinnedMainTab: true,
      canvas: {
        pins: upsertById(state.canvas.pins, nextPin),
      },
    }))
  },

  focusReactStep: (stepIndex) => {
    set(() => ({
      activeMainTab: 'react-flow',
      userPinnedMainTab: true,
      reactFlow: {
        focusedStepIndex: stepIndex,
      },
    }))
  },

  jumpTo: (target) => {
    if (target.type === 'tab') {
      get().setActiveMainTab(target.tab)
      return
    }
    if (target.type === 'file') {
      get().openFile(target.file)
      return
    }
    if (target.type === 'browser') {
      get().selectBrowserLink(target.link)
      return
    }
    if (target.type === 'terminal') {
      get().addTerminalCommand(target.command)
      return
    }
    if (target.type === 'code-change') {
      if (target.item) {
        get().addCodeChange(target.item)
      } else {
        get().setActiveMainTab('code-changes')
      }
      return
    }
    if (target.type === 'canvas') {
      if (target.pin) {
        get().addCanvasPin(target.pin)
      } else {
        get().setActiveMainTab('canvas')
      }
      return
    }
    if (target.type === 'react-flow') {
      get().focusReactStep(target.stepIndex ?? null)
      return
    }
    if (target.type === 'agent') {
      get().setActiveMainTab('agent')
      return
    }
    get().setActiveMainTab('mcp')
  },
}))
