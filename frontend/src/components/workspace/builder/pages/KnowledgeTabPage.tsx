import { Database, FileText, Search, Trash2, Upload } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'

import { useAgentStore } from '../../../../features/agent/agent.store'
import { knowledgeAdapter, type KnowledgeDocument, type KnowledgeSearchResult } from '../../../../features/knowledge/knowledge.adapter'
import { notify } from '../../../../features/notifications/notify'
import { cn } from '../../../../lib/cn'
import { Button } from '../../../ui/Button'
import { Input } from '../../../ui/Input'

const uploadAccept = '.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document'
const maxUploadFileSize = 100 * 1024 * 1024

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString()
}

function formatDocumentType(value: string): string {
  const labels: Record<string, string> = {
    school_policy: '校规制度',
    product_policy: '产品规则',
    faq: 'FAQ',
    other: '通用资料',
  }
  return labels[value] ?? value
}

function formatMatchType(value: string): string {
  const labels: Record<string, string> = {
    exact_clause: '条款命中',
    hybrid: '混合命中',
    keyword: '关键词',
    near_miss: '近似候选',
  }
  return labels[value] ?? value
}

function asMetadataNumber(metadata: Record<string, unknown>, key: string): number | null {
  const value = metadata[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function asMetadataString(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key]
  return typeof value === 'string' && value.trim().length > 0 ? value : null
}

function isSupportedUploadFile(file: File): boolean {
  const fileName = file.name.toLowerCase()
  return fileName.endsWith('.pdf') || fileName.endsWith('.docx')
}

export function KnowledgeTabPage() {
  const currentAgentId = useAgentStore((state) => state.current_agent_id)
  const currentAgentDetail = useAgentStore((state) => state.current_agent_detail)
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[]>([])
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [fileTitle, setFileTitle] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isFileDragActive, setIsFileDragActive] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const canSave = currentAgentId !== null && title.trim().length > 0 && content.trim().length > 0 && !isSaving
  const canUpload = currentAgentId !== null && selectedFile !== null && !isUploading
  const canSearch = currentAgentId !== null && query.trim().length > 0 && !isSearching
  const totalChunks = useMemo(() => documents.reduce((sum, item) => sum + item.chunk_count, 0), [documents])
  const totalArticles = useMemo(
    () => documents.reduce((sum, item) => sum + (asMetadataNumber(item.metadata, 'article_count') ?? 0), 0),
    [documents],
  )

  async function loadDocuments(agentId: string) {
    setIsLoading(true)
    try {
      setDocuments(await knowledgeAdapter.listDocuments(agentId))
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '知识库加载失败')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDocuments([])
      setSearchResults([])
      if (currentAgentId !== null) {
        void loadDocuments(currentAgentId)
      }
    }, 0)
    return () => window.clearTimeout(timer)
  }, [currentAgentId])

  async function handleSave() {
    if (!canSave || currentAgentId === null) return
    setIsSaving(true)
    try {
      const created = await knowledgeAdapter.createDocument(currentAgentId, {
        title: title.trim(),
        content: content.trim(),
      })
      setDocuments((prev) => [created, ...prev])
      setTitle('')
      setContent('')
      notify.success('知识已存入')
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '知识存入失败')
    } finally {
      setIsSaving(false)
    }
  }

  async function handleUpload() {
    if (!canUpload || currentAgentId === null || selectedFile === null) return
    setIsUploading(true)
    try {
      const created = await knowledgeAdapter.uploadDocument(currentAgentId, {
        file: selectedFile,
        title: fileTitle.trim().length > 0 ? fileTitle.trim() : undefined,
      })
      setDocuments((prev) => [created, ...prev])
      setSelectedFile(null)
      setFileTitle('')
      notify.success('文件知识已存入')
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '文件上传失败')
    } finally {
      setIsUploading(false)
    }
  }

  function selectUploadFile(file: File | null) {
    if (file === null) return
    if (!isSupportedUploadFile(file)) {
      notify.error('仅支持 PDF 或 Word（.docx）文件')
      return
    }
    if (file.size > maxUploadFileSize) {
      notify.error('文件不能超过 100MB')
      return
    }
    setSelectedFile(file)
  }

  function handleFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    selectUploadFile(event.target.files?.[0] ?? null)
    event.target.value = ''
  }

  function handleFileDragEnter(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    event.stopPropagation()
    if (!isUploading) {
      setIsFileDragActive(true)
    }
  }

  function handleFileDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    event.stopPropagation()
    event.dataTransfer.dropEffect = isUploading ? 'none' : 'copy'
    if (!isUploading) {
      setIsFileDragActive(true)
    }
  }

  function handleFileDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    event.stopPropagation()
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setIsFileDragActive(false)
    }
  }

  function handleFileDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    event.stopPropagation()
    setIsFileDragActive(false)
    if (isUploading) return
    selectUploadFile(event.dataTransfer.files?.[0] ?? null)
  }

  async function handleSearch() {
    if (!canSearch || currentAgentId === null) return
    setIsSearching(true)
    try {
      setSearchResults(await knowledgeAdapter.search(currentAgentId, { query: query.trim(), limit: 5 }))
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '知识检索失败')
    } finally {
      setIsSearching(false)
    }
  }

  async function handleDelete(documentId: string) {
    if (currentAgentId === null) return
    try {
      await knowledgeAdapter.deleteDocument(currentAgentId, documentId)
      setDocuments((prev) => prev.filter((item) => item.id !== documentId))
      setSearchResults((prev) => prev.filter((item) => item.document_id !== documentId))
      notify.success('知识已删除')
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '删除失败')
    }
  }

  if (currentAgentId === null) {
    return (
      <div className="h-full overflow-auto rounded-token-lg border border-border bg-surface p-5">
        <div className="flex h-full min-h-64 items-center justify-center rounded-token-md border border-dashed border-border text-sm text-text-muted">
          请先选择或创建一个智能体，再为它配置知识库。
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto rounded-token-lg border border-border bg-surface">
      <div className="mx-auto max-w-6xl space-y-5 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-4">
          <div className="flex min-w-0 items-center gap-2">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-token-md bg-primary/10 text-primary">
              <Database size={17} />
            </span>
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-text-main">知识库</h2>
              <p className="mt-1 text-sm text-text-sub">
                当前智能体：{currentAgentDetail?.name ?? '未命名'}。知识会在对话执行时按用户问题自动检索。
              </p>
            </div>
          </div>
          <div className="text-right text-xs text-text-muted">
            <p>{documents.length} 篇知识</p>
            <p>{totalChunks} 个分片 · {totalArticles} 个条款</p>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
          <section className="space-y-4 rounded-token-md border border-border bg-bg p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-main">
              <Upload size={15} className="text-text-muted" />
              存入知识
            </div>
            <Input id="knowledge-title" label="标题" placeholder="例如：产品计费规则" value={title} onChange={(e) => setTitle(e.target.value)} />
            <div className="space-y-2">
              <label htmlFor="knowledge-content" className="text-xs font-medium text-text-sub">正文</label>
              <textarea
                id="knowledge-content"
                className="min-h-[320px] w-full resize-y rounded-token-md border border-border bg-surface px-4 py-3 text-sm leading-relaxed text-text-main placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                placeholder="粘贴需要智能体记住和检索的资料。保存后会自动切分为可检索片段。"
                value={content}
                onChange={(event) => setContent(event.target.value)}
              />
              <div className="flex items-center justify-between text-xs text-text-muted">
                <span>保存后立即可被检索。</span>
                <span>{content.trim().length} 字符</span>
              </div>
            </div>
            <Button type="button" variant="primary" leftIcon={<Upload size={14} />} onClick={() => void handleSave()} disabled={!canSave}>
              {isSaving ? '正在存入...' : '存入知识库'}
            </Button>

            <div className="space-y-3 rounded-token-md border border-border bg-surface p-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-text-main">
                <FileText size={15} className="text-text-muted" />
                上传文件
              </div>
              <Input id="knowledge-file-title" label="文件标题" placeholder="留空则使用文件名" value={fileTitle} onChange={(e) => setFileTitle(e.target.value)} />
              <label
                htmlFor="knowledge-file-upload"
                className={cn(
                  'flex min-h-28 cursor-pointer flex-col items-center justify-center gap-2 rounded-token-md border border-dashed px-4 py-5 text-center text-sm transition-colors duration-200',
                  'focus-within:outline-none focus-within:ring-2 focus-within:ring-primary/40',
                  isUploading ? 'cursor-not-allowed opacity-60' : 'hover:border-primary/60 hover:bg-primary/5',
                  isFileDragActive ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-bg-soft/50 text-text-sub',
                )}
                onDragEnter={handleFileDragEnter}
                onDragOver={handleFileDragOver}
                onDragLeave={handleFileDragLeave}
                onDrop={handleFileDrop}
              >
                <input
                  ref={fileInputRef}
                  id="knowledge-file-upload"
                  type="file"
                  accept={uploadAccept}
                  className="hidden"
                  disabled={isUploading}
                  onChange={handleFileInputChange}
                />
                {selectedFile ? (
                  <>
                    <span className="font-medium text-text-main">{selectedFile.name}</span>
                    <span className="text-xs text-text-muted">点击可重新选择，或拖拽新文件替换</span>
                  </>
                ) : (
                  <>
                    <span className="font-medium text-text-main">点击选择文件，或拖拽文件到此处</span>
                    <span className="text-xs text-text-muted">支持 PDF、Word（.docx）</span>
                  </>
                )}
              </label>
              <div className="flex items-center justify-between gap-2 text-xs text-text-muted">
                <span>上传后自动抽取文本并切分入库，最大 100MB。</span>
                {selectedFile ? <button type="button" className="text-primary hover:underline" onClick={() => setSelectedFile(null)}>移除</button> : null}
              </div>
              <Button
                type="button"
                variant="secondary"
                leftIcon={<Upload size={14} />}
                onClick={() => {
                  if (selectedFile === null) {
                    fileInputRef.current?.click()
                    return
                  }
                  void handleUpload()
                }}
                disabled={currentAgentId === null || isUploading}
              >
                {isUploading ? '正在解析...' : '上传并存入'}
              </Button>
            </div>
          </section>

          <aside className="space-y-4">
            <section className="space-y-3 rounded-token-md border border-border bg-bg p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-text-main">
                <Search size={15} className="text-text-muted" />
                读取测试
              </div>
              <Input id="knowledge-query" label="检索问题" placeholder="输入一句用户问题测试检索结果" value={query} onChange={(e) => setQuery(e.target.value)} />
              <Button type="button" variant="secondary" leftIcon={<Search size={14} />} onClick={() => void handleSearch()} disabled={!canSearch}>
                {isSearching ? '正在检索...' : '检索知识'}
              </Button>
              <div className="space-y-2">
                {searchResults.length === 0 ? (
                  <p className="rounded-token-md border border-dashed border-border px-3 py-4 text-center text-xs text-text-muted">暂无检索结果</p>
                ) : (
                  searchResults.map((item) => (
                    <div key={item.chunk_id} className="rounded-token-md border border-border bg-surface p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm font-semibold text-text-main">{item.title}</p>
                        <span className="text-xs text-text-muted">分数 {item.score}</span>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-text-muted">
                        <span className="rounded-token-sm bg-bg-soft px-2 py-0.5">{formatMatchType(item.match_type)}</span>
                        <span className="rounded-token-sm bg-bg-soft px-2 py-0.5">{formatDocumentType(item.document_type)}</span>
                        {item.article_label ? <span className="rounded-token-sm bg-bg-soft px-2 py-0.5">{item.article_label}</span> : null}
                        {item.citation_label ? <span className="min-w-0 truncate rounded-token-sm bg-bg-soft px-2 py-0.5">{item.citation_label}</span> : null}
                        {!item.is_direct_evidence ? <span className="rounded-token-sm bg-warning/10 px-2 py-0.5 text-warning">候选证据</span> : null}
                      </div>
                      {item.section_path.length > 0 ? (
                        <p className="mt-2 truncate text-[11px] text-text-muted">{item.section_path.join(' / ')}</p>
                      ) : null}
                      <p className="mt-2 line-clamp-4 whitespace-pre-wrap text-xs leading-relaxed text-text-sub">{item.content}</p>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="space-y-3 rounded-token-md border border-border bg-bg p-4">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-text-main">已存知识</p>
                <span className="text-xs text-text-muted">{isLoading ? '加载中' : `${documents.length} 篇`}</span>
              </div>
              <div className="max-h-[360px] space-y-2 overflow-y-auto pr-1">
                {documents.length === 0 ? (
                  <p className="rounded-token-md border border-dashed border-border px-3 py-4 text-center text-xs text-text-muted">还没有存入知识</p>
                ) : (
                  documents.map((item) => (
                    <div key={item.id} className="rounded-token-md border border-border bg-surface p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-text-main">{item.title}</p>
                          <p className="mt-1 text-xs text-text-muted">
                            {item.chunk_count} 个分片 · {asMetadataNumber(item.metadata, 'article_count') ?? 0} 个条款 · {formatDate(item.created_at)}
                          </p>
                        </div>
                        <Button variant="ghost" size="icon" aria-label="删除知识" title="删除知识" onClick={() => void handleDelete(item.id)}>
                          <Trash2 size={14} className="text-text-muted" />
                        </Button>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-text-muted">
                        <span className="rounded-token-sm bg-bg-soft px-2 py-0.5">{formatDocumentType(item.document_type)}</span>
                        <span className="rounded-token-sm bg-bg-soft px-2 py-0.5">{item.status}</span>
                        {asMetadataString(item.metadata, 'parser_version') ? (
                          <span className="rounded-token-sm bg-bg-soft px-2 py-0.5">{asMetadataString(item.metadata, 'parser_version')}</span>
                        ) : null}
                        {item.source_filename ? (
                          <span className="min-w-0 truncate rounded-token-sm bg-bg-soft px-2 py-0.5">{item.source_filename}</span>
                        ) : null}
                      </div>
                      <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-xs leading-relaxed text-text-sub">{item.content}</p>
                    </div>
                  ))
                )}
              </div>
            </section>
          </aside>
        </div>
      </div>
    </div>
  )
}
