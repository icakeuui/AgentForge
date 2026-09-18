import {
  BookOpen,
  Bot,
  BugPlay,
  ChartNoAxesColumn,
  Database,
  FileCode2,
  FolderArchive,
  FolderCog,
  GitBranch,
  KeyRound,
  MonitorSmartphone,
  Network,
  Plus,
  ScrollText,
  TerminalSquare,
  Wrench,
  Workflow,
  type LucideIcon,
} from 'lucide-react'

const ICON_MAP: Record<string, LucideIcon> = {
  monitor: MonitorSmartphone,
  plus: Plus,
  bot: Bot,
  wrench: Wrench,
  book: BookOpen,
  scroll: ScrollText,
  plug: Network,
  key: KeyRound,
  database: Database,
  folder: FolderArchive,
  history: FolderCog,
  chart: ChartNoAxesColumn,
  workflow: Workflow,
  terminal: TerminalSquare,
  file: FileCode2,
  git: GitBranch,
  bug: BugPlay,
}

export function getBuilderIcon(name: string): LucideIcon {
  return ICON_MAP[name] ?? MonitorSmartphone
}
