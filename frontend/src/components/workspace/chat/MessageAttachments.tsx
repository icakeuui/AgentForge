import { Paperclip } from 'lucide-react'

export interface MessageAttachment {
  id: string
  name: string
  mime_type?: string | null
  size?: number | null
  conversation_id?: string | null
}

function safeAttachmentName(name: string): string {
  return name.split(/[\\/]/).pop()?.trim() || '未命名文件'
}

function attachmentType(attachment: MessageAttachment): string {
  const extension = safeAttachmentName(attachment.name).split('.').pop()?.toUpperCase()
  if (extension && extension !== safeAttachmentName(attachment.name).toUpperCase()) return extension
  return attachment.mime_type?.split('/').pop()?.toUpperCase() || '文件'
}

function attachmentSize(size: number | null | undefined): string | null {
  if (typeof size !== 'number' || !Number.isFinite(size) || size < 0) return null
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

export function MessageAttachments({ attachments }: { attachments?: MessageAttachment[] }) {
  if (!attachments?.length) return null

  return (
    <div className="mt-2 flex min-w-0 flex-col gap-1.5" aria-label="消息附件">
      {attachments.map((attachment) => {
        const name = safeAttachmentName(attachment.name)
        const size = attachmentSize(attachment.size)
        return (
          <div key={attachment.id} className="flex min-w-0 max-w-full items-center gap-2 rounded-token-md border border-primary/15 bg-surface/85 px-2.5 py-1.5 text-xs text-text-main">
            <Paperclip size={13} className="shrink-0 text-primary" aria-hidden="true" />
            <span className="min-w-0 truncate" title={name}>{name}</span>
            <span className="shrink-0 text-text-muted">{attachmentType(attachment)}{size ? ` · ${size}` : ''}</span>
          </div>
        )
      })}
    </div>
  )
}
