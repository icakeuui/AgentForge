import { apiClient } from '../../lib/api/client'
import { ApiError } from '../../lib/api/error'

export interface MarketplaceConfigField {
  key: string
  label: string
  type: string
  required: boolean
  placeholder: string | null
  help_text: string | null
}

export interface MarketplaceExtension {
  id: string
  name: string
  description: string | null
  icon_url: string | null
  tool_type: string
  categories: string[]
  author: string | null
  homepage: string | null
  popularity: number
  is_official: boolean
  config_fields: MarketplaceConfigField[]
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function asString(value: unknown, field: string): string {
  if (typeof value !== 'string') {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: `工具市场字段无效：${field}`,
      raw: value,
    })
  }
  return value
}

function asNullableString(value: unknown, field: string): string | null {
  if (value === null || value === undefined) {
    return null
  }
  return asString(value, field)
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }
  return value.filter((item): item is string => typeof item === 'string')
}

function mapConfigField(raw: unknown): MarketplaceConfigField {
  const field = isRecord(raw) ? raw : {}
  return {
    key: asString(field.key ?? '', 'config_fields.key'),
    label: asString(field.label ?? field.key ?? '', 'config_fields.label'),
    type: typeof field.type === 'string' ? field.type : 'text',
    required: Boolean(field.required),
    placeholder: asNullableString(field.placeholder, 'config_fields.placeholder'),
    help_text: asNullableString(field.help_text, 'config_fields.help_text'),
  }
}

function mapExtension(raw: unknown): MarketplaceExtension {
  if (!isRecord(raw)) {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: '工具市场扩展响应无效',
      raw,
    })
  }

  return {
    id: asString(raw.id, 'id'),
    name: asString(raw.name, 'name'),
    description: asNullableString(raw.description, 'description'),
    icon_url: asNullableString(raw.icon_url, 'icon_url'),
    tool_type: asString(raw.tool_type ?? 'tool', 'tool_type'),
    categories: asStringArray(raw.categories),
    author: asNullableString(raw.author, 'author'),
    homepage: asNullableString(raw.homepage, 'homepage'),
    popularity: typeof raw.popularity === 'number' ? raw.popularity : 0,
    is_official: Boolean(raw.is_official),
    config_fields: Array.isArray(raw.config_fields) ? raw.config_fields.map(mapConfigField) : [],
  }
}

function mapExtensions(raw: unknown): MarketplaceExtension[] {
  if (!Array.isArray(raw)) {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: '工具市场扩展列表响应无效',
      raw,
    })
  }
  return raw.map(mapExtension)
}

export const marketplaceAdapter = {
  async fetchExtensions(): Promise<MarketplaceExtension[]> {
    try {
      const result = await apiClient.request<unknown>('/marketplace/extensions', {
        method: 'GET',
        authMode: 'required',
        responseMode: 'raw',
      })
      return mapExtensions(result.data)
    } catch (error) {
      if (!(error instanceof ApiError) || error.code !== 'HTTP_ERROR') {
        throw error
      }
      const result = await apiClient.request<unknown>('/api/v1/marketplace/extensions', {
        method: 'GET',
        authMode: 'required',
        responseMode: 'raw',
      })
      return mapExtensions(result.data)
    }
  },
}
