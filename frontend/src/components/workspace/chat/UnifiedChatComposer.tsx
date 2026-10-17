import { useCallback, useEffect, useRef, useState } from 'react'
import { Mic, Paperclip, Send, Square, X } from 'lucide-react'

import { notify } from '../../../features/notifications/notify'
import { Button } from '../../ui/Button'

export const MAX_CHAT_ATTACHMENT_BYTES = 100 * 1024 * 1024
export const MAX_CHAT_ATTACHMENTS = 3

export type ComposerAttachment = { id: string; name: string }

type SpeechResultEvent = {
  resultIndex: number
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>
}

type BrowserSpeechRecognition = {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((event: SpeechResultEvent) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}

type SpeechRecognitionWindow = Window & {
  SpeechRecognition?: new () => BrowserSpeechRecognition
  webkitSpeechRecognition?: new () => BrowserSpeechRecognition
}

type Props = {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled: boolean
  placeholder: string
  attachments?: ComposerAttachment[]
  onSelectFiles?: (files: File[]) => void
  onRemoveAttachment?: (id: string) => void
  isUploading?: boolean
  onStop?: () => void
  isRunning?: boolean
  maxAttachments?: number
}

function speechErrorMessage(error: string): string {
  if (error === 'not-allowed' || error === 'service-not-allowed') {
    return '未获得麦克风权限，请在浏览器设置中允许麦克风访问。'
  }
  if (error === 'audio-capture') return '无法使用麦克风，请检查设备连接和浏览器麦克风设置。'
  if (error === 'no-speech') return '没有识别到语音，请重试。'
  if (error === 'network') return '语音识别网络连接失败，请检查网络后重试。'
  return '语音识别失败，请重试。'
}

export function UnifiedChatComposer({
  value,
  onChange,
  onSend,
  disabled,
  placeholder,
  attachments = [],
  onSelectFiles,
  onRemoveAttachment,
  isUploading = false,
  onStop,
  isRunning = false,
  maxAttachments = MAX_CHAT_ATTACHMENTS,
}: Props) {
  const [isListening, setIsListening] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null)
  const isStoppingRef = useRef(false)
  const onChangeRef = useRef(onChange)
  const valueRef = useRef(value)

  useEffect(() => {
    onChangeRef.current = onChange
    valueRef.current = value
  }, [onChange, value])

  const toggleSpeech = useCallback(() => {
    const active = recognitionRef.current
    if (active) {
      if (!isStoppingRef.current) {
        isStoppingRef.current = true
        try { active.stop() } catch { active.abort() }
      }
      return
    }
    if (disabled) return
    const speechWindow = window as SpeechRecognitionWindow
    const Recognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition
    if (!Recognition) {
      notify.warning('当前浏览器暂不支持语音输入，请使用支持 Web Speech API 的浏览器。')
      return
    }
    const recognition = new Recognition()
    const processed = new Set<number>()
    let hasVoiceText = false
    recognition.lang = 'zh-CN'
    recognition.continuous = true
    recognition.interimResults = false
    recognition.onresult = (event) => {
      let addition = ''
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index]
        if (!result.isFinal || processed.has(index)) continue
        processed.add(index)
        addition += result[0].transcript
      }
      if (addition) {
        const separator = !hasVoiceText && valueRef.current && !/\s$/.test(valueRef.current) ? ' ' : ''
        hasVoiceText = true
        valueRef.current += separator + addition
        onChangeRef.current(valueRef.current)
      }
    }
    recognition.onerror = (event) => {
      if (event.error !== 'aborted' || !isStoppingRef.current) notify.error(speechErrorMessage(event.error))
    }
    recognition.onend = () => {
      if (recognitionRef.current === recognition) {
        recognitionRef.current = null
        isStoppingRef.current = false
        setIsListening(false)
      }
    }
    recognitionRef.current = recognition
    try {
      recognition.start()
      setIsListening(true)
    } catch {
      recognitionRef.current = null
      setIsListening(false)
      notify.error('语音识别启动失败，请检查麦克风权限后重试。')
    }
  }, [disabled])

  useEffect(() => {
    if (disabled && recognitionRef.current) {
      isStoppingRef.current = true
      recognitionRef.current.abort()
    }
  }, [disabled])

  useEffect(() => () => {
    const recognition = recognitionRef.current
    if (recognition) {
      recognition.onresult = null
      recognition.onerror = null
      recognition.onend = null
      recognition.abort()
      recognitionRef.current = null
    }
  }, [])

  const handleFiles = (files: FileList | null) => {
    if (!files || !onSelectFiles) return
    const selected = Array.from(files)
    if (attachments.length + selected.length > maxAttachments) {
      notify.error(`每条消息最多添加 ${maxAttachments} 个附件`)
      return
    }
    for (const file of selected) {
      if (!/\.(pdf|docx|txt)$/i.test(file.name)) {
        notify.error('仅支持 PDF、Word（.docx）或 TXT 文件')
        return
      }
      if (file.size > MAX_CHAT_ATTACHMENT_BYTES) {
        notify.error('文件不能超过 100MB')
        return
      }
    }
    onSelectFiles(selected)
  }

  return (
    <div className={`flex flex-col gap-2 rounded-token-md border border-border bg-bg px-3 py-2 shadow-token-sm transition-colors focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/50 ${isRunning ? 'opacity-75' : ''}`} aria-busy={isRunning || isUploading}>
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-1.5" aria-label="已选择附件">
          {attachments.map((file) => (
            <span key={file.id} className="inline-flex max-w-full items-center gap-1 rounded-token-md border border-border bg-surface px-2 py-1 text-xs text-text-sub">
              <span className="max-w-48 truncate" title={file.name}>{file.name}</span>
              {onRemoveAttachment && <button type="button" aria-label={`移除 ${file.name}`} disabled={disabled || isUploading} onClick={() => onRemoveAttachment(file.id)}><X size={12} /></button>}
            </span>
          ))}
        </div>
      )}
      <textarea
        ref={textareaRef}
        className="w-full resize-none bg-transparent py-1 text-sm text-text-main placeholder:text-text-muted focus:outline-none"
        rows={2}
        placeholder={placeholder}
        disabled={disabled}
        value={value}
        onChange={(event) => { valueRef.current = event.target.value; onChange(event.target.value) }}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            if (isRunning && onStop) onStop()
            else if (!disabled) onSend()
          }
        }}
      />
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-1">
          {onSelectFiles && <>
            <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain" multiple={maxAttachments > 1} className="sr-only" disabled={disabled || isUploading} onChange={(event) => { handleFiles(event.target.files); event.target.value = '' }} />
            <Button type="button" variant="ghost" size="icon" aria-label="添加附件" title={isUploading ? '正在上传附件' : '添加附件'} disabled={disabled || isUploading} onClick={() => fileInputRef.current?.click()}><Paperclip size={14} className="text-text-muted" /></Button>
          </>}
          <Button type="button" variant="ghost" size="icon" aria-label={isListening ? '停止语音输入' : '语音输入'} aria-pressed={isListening} title={isListening ? '停止语音输入' : '语音输入'} className={isListening ? 'bg-primary/10 text-primary' : undefined} disabled={disabled && !isListening} onClick={toggleSpeech}><Mic size={14} className={isListening ? 'text-primary' : 'text-text-muted'} /></Button>
          {isListening && <span className="text-xs text-primary" role="status">正在聆听…</span>}
          {isUploading && <span className="text-xs text-text-muted" role="status">正在上传…</span>}
        </div>
        <Button type="button" variant="primary" size="icon" aria-label={isRunning && onStop ? '停止模型回复' : '发送消息'} title={isRunning && onStop ? '停止当前模型行为' : '发送消息'} className="h-6 w-6 rounded-token-md" disabled={disabled && !(isRunning && onStop)} onClick={() => { if (isRunning && onStop) onStop(); else onSend() }}>
          {isRunning && onStop ? <Square size={11} className="fill-white text-white" /> : <Send size={12} className="text-white" />}
        </Button>
      </div>
    </div>
  )
}
