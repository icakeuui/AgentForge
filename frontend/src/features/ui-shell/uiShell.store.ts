import { create } from 'zustand'

type UiShellState = {
  sidebarCollapsed: boolean
  rightPanelCollapsed: boolean
  commandPaletteOpen: boolean
  leftPanelWidth: number
  rightPanelWidth: number
  minLeftPanelWidth: number
  maxLeftPanelWidth: number
  minRightPanelWidth: number
  maxRightPanelWidth: number
  maximizedPanel: 'debug' | 'output' | null
  toggleSidebar: () => void
  toggleRightPanel: () => void
  setCommandPaletteOpen: (open: boolean) => void
  setLeftPanelWidth: (width: number) => void
  setRightPanelWidth: (width: number) => void
  setMaximizedPanel: (panel: 'debug' | 'output' | null) => void
}

export const useUiShellStore = create<UiShellState>((set) => ({
  sidebarCollapsed: false,
  rightPanelCollapsed: false,
  commandPaletteOpen: false,
  leftPanelWidth: 250,
  rightPanelWidth: 340,
  minLeftPanelWidth: 220,
  maxLeftPanelWidth: 320,
  minRightPanelWidth: 300,
  maxRightPanelWidth: 420,
  maximizedPanel: null,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  toggleRightPanel: () => set((state) => ({ rightPanelCollapsed: !state.rightPanelCollapsed })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  setLeftPanelWidth: (width) => set((state) => ({ 
    leftPanelWidth: Math.min(Math.max(width, state.minLeftPanelWidth), state.maxLeftPanelWidth) 
  })),
  setRightPanelWidth: (width) => set((state) => ({ 
    rightPanelWidth: Math.min(Math.max(width, state.minRightPanelWidth), state.maxRightPanelWidth) 
  })),
  setMaximizedPanel: (panel) => set({ maximizedPanel: panel }),
}))
