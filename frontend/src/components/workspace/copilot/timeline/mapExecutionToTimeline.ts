import type { ExecutionStatus, ExecutionStep } from '../../../../features/execution/execution.types'
import type { BrowserLinkItem } from '../../../../features/ui-shell/workspaceTabs.types'
import type { TimelineArtifactFile, TimelineItem } from './timeline.types'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function readString(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null
}

function fileTitle(path: string): string {
  const segments = path.split(/[\\/]/).filter(Boolean)
  return segments.at(-1) ?? path
}

function safeStringify(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function summarizeArguments(args: Record<string, unknown> | null | undefined): string {
  if (!args) {
    return '无参数'
  }
  const keys = Object.keys(args)
  if (keys.length === 0) {
    return '无参数'
  }
  return keys
    .slice(0, 3)
    .map((key) => {
      const value = args[key]
      if (typeof value === 'string') {
        const compactValue = value.trim()
        return `${key}=${compactValue.length > 22 ? `${compactValue.slice(0, 22)}...` : compactValue}`
      }
      if (typeof value === 'number' || typeof value === 'boolean') {
        return `${key}=${String(value)}`
      }
      if (Array.isArray(value)) {
        return `${key}=[${value.length}]`
      }
      if (isRecord(value)) {
        return `${key}={...}`
      }
      return `${key}=null`
    })
    .join(', ')
}

function asBrowserLink(url: string, title?: string | null, snippet?: string | null, source?: string | null): BrowserLinkItem {
  return {
    id: `search:${url}`,
    title: title && title.trim().length > 0 ? title.trim() : url,
    url,
    snippet: snippet ?? null,
    source: source ?? null,
  }
}

function readHttpUrl(value: unknown): string | null {
  const raw = readString(value)
  if (raw === null) {
    return null
  }
  try {
    const url = new URL(raw)
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.toString() : null
  } catch {
    return null
  }
}

function extractSearchResultItem(item: unknown, source: string): BrowserLinkItem | null {
  if (!isRecord(item)) {
    return null
  }

  const url =
    readHttpUrl(item.url) ??
    readHttpUrl(item.link) ??
    readHttpUrl(item.href) ??
    readHttpUrl(item.source_url)
  if (url === null) {
    return null
  }

  const title = readString(item.title) ?? readString(item.name)
  const snippet = readString(item.snippet) ?? readString(item.summary) ?? readString(item.description)
  if (title === null && snippet === null) {
    return null
  }

  return asBrowserLink(url, title, snippet, source)
}

function appendSearchArray(candidateArrays: unknown[][], value: unknown): void {
  if (Array.isArray(value)) {
    candidateArrays.push(value)
  }
}

function extractSearchLinks(content: unknown, source: string): BrowserLinkItem[] {
  if (!isRecord(content)) {
    return []
  }

  const candidateArrays: unknown[][] = []
  appendSearchArray(candidateArrays, content.results)
  appendSearchArray(candidateArrays, content.items)
  appendSearchArray(candidateArrays, content.search_results)
  appendSearchArray(candidateArrays, content.organic_results)
  if (isRecord(content.web)) {
    appendSearchArray(candidateArrays, content.web.results)
  } else {
    appendSearchArray(candidateArrays, content.web)
  }

  if (candidateArrays.length === 0) {
    return []
  }

  return candidateArrays
    .flatMap((items) => items.map((item) => extractSearchResultItem(item, source)))
    .filter((item): item is BrowserLinkItem => item !== null)
    .filter((item, idx, arr) => arr.findIndex((next) => next.url === item.url) === idx)
}

function extractArtifactFiles(rawArtifacts: unknown[]): TimelineArtifactFile[] {
  return rawArtifacts.flatMap((artifact, index) => {
    if (!isRecord(artifact)) {
      return []
    }
    const path =
      readString(artifact.path) ??
      readString(artifact.file_path) ??
      readString(artifact.filename) ??
      readString(artifact.target_path)
    if (path === null) {
      return []
    }
    const additions = typeof artifact.additions === 'number' ? artifact.additions : null
    const deletions = typeof artifact.deletions === 'number' ? artifact.deletions : null
    const summary = readString(artifact.summary) ?? readString(artifact.description)

    return [
      {
        id: `artifact:${index}:${path}`,
        title: fileTitle(path),
        path,
        summary,
        additions,
        deletions,
      },
    ]
  })
}

function summarizeObservationContent(content: unknown, ok: boolean): string {
  if (!ok) {
    return '工具调用失败'
  }
  if (typeof content === 'string') {
    const compact = content.trim()
    if (compact.length === 0) {
      return '空文本结果'
    }
    return compact.length > 120 ? `${compact.slice(0, 120)}...` : compact
  }
  if (Array.isArray(content)) {
    return `返回 ${content.length} 项结果`
  }
  if (isRecord(content)) {
    const keys = Object.keys(content)
    return keys.length === 0 ? '空对象结果' : `JSON 结果（${keys.slice(0, 4).join(', ')}${keys.length > 4 ? '...' : ''}）`
  }
  return '返回结构化结果'
}

function actionStatus(step: ExecutionStep): 'running' | 'success' | 'error' {
  if (!step.observation) {
    return 'running'
  }
  return step.observation.ok ? 'success' : 'error'
}

function mapStepItems(step: ExecutionStep, executionStatus: ExecutionStatus): TimelineItem[] {
  const items: TimelineItem[] = []
  if (step.thought && step.thought.trim().length > 0) {
    items.push({
      id: `thought:${step.step_index}`,
      type: 'thought',
      stepIndex: step.step_index,
      thought: step.thought,
      defaultExpanded: executionStatus === 'RUNNING' || executionStatus === 'PENDING',
    })
  }

  if (step.action) {
    items.push({
      id: `action:${step.step_index}`,
      type: 'action',
      stepIndex: step.step_index,
      toolId: step.action.tool_id,
      argsSummary: summarizeArguments(step.action.arguments),
      status: actionStatus(step),
    })
  }

  if (step.observation) {
    const links = extractSearchLinks(step.observation.content, `step_${step.step_index}`)
    const files =
      isRecord(step.observation.content) && Array.isArray(step.observation.content.files)
        ? extractArtifactFiles(step.observation.content.files)
        : []

    items.push({
      id: `observation:${step.step_index}`,
      type: 'observation',
      stepIndex: step.step_index,
      ok: step.observation.ok,
      summary: summarizeObservationContent(step.observation.content, step.observation.ok),
      rawContent: step.observation.content,
      error: step.observation.error ?? null,
      links,
      files,
    })

    if (!step.observation.ok && step.observation.error) {
      items.push({
        id: `error:${step.step_index}`,
        type: 'error',
        title: `第 ${step.step_index} 步执行失败`,
        message: safeStringify(step.observation.error),
        stepIndex: step.step_index,
      })
    }
  }

  return items
}

export interface BuildTimelineInput {
  currentExecutionId: string | null
  status: ExecutionStatus
  reactSteps: ExecutionStep[]
  finalAnswer: string | null
  errorCode: string | null
  errorSource: string | null
  errorMessage: string | null
  terminationReason: string | null
  artifacts: unknown[]
}

function buildGlobalErrorItem(input: BuildTimelineInput): TimelineItem | null {
  if (input.status !== 'FAILED' && input.status !== 'TERMINATED') {
    return null
  }

  const message = input.errorMessage ?? input.terminationReason ?? '执行异常终止'
  return {
    id: `global-error:${input.currentExecutionId}`,
    type: 'error',
    title: input.status === 'FAILED' ? '执行出错' : '执行中断',
    message,
    source: input.errorSource,
    code: input.errorCode,
    stepIndex: null,
  }
}

export function mapExecutionToTimeline(input: BuildTimelineInput): TimelineItem[] {
  if (input.currentExecutionId === null) {
    return []
  }

  const timeline: TimelineItem[] = [
    {
      id: `status:${input.currentExecutionId}`,
      type: 'status',
      status: input.status,
    },
  ]
  const globalError = buildGlobalErrorItem(input)
  if (globalError !== null) {
    timeline.push(globalError)
  }

  input.reactSteps
    .slice()
    .sort((a, b) => a.step_index - b.step_index)
    .forEach((step) => {
      timeline.push(...mapStepItems(step, input.status))
    })

  const artifactFiles = extractArtifactFiles(input.artifacts)
  if (artifactFiles.length > 0) {
    timeline.push({
      id: `artifact:${input.currentExecutionId}`,
      type: 'artifact',
      files: artifactFiles,
      rawCount: input.artifacts.length,
    })
  }

  if (input.finalAnswer && input.finalAnswer.trim().length > 0) {
    timeline.push({
      id: `final:${input.currentExecutionId}`,
      type: 'final_answer',
      content: input.finalAnswer,
    })
  }

  return timeline
}
