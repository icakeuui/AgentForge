import type { ReactNode } from 'react'

type Column<T> = { key: keyof T; header: string; render?: (row: T) => ReactNode }
type TableProps<T extends Record<string, unknown>> = { data: T[]; columns: Array<Column<T>> }

export function Table<T extends Record<string, unknown>>({ data, columns }: TableProps<T>) {
  return (
    <div className="overflow-hidden rounded-token-lg border border-border bg-surface shadow-token-sm">
      <table className="min-w-full border-collapse text-left">
        <thead className="bg-bg-soft">
          <tr>
            {columns.map((col) => (
              <th key={String(col.key)} className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-text-sub">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => (
            <tr key={index} className="border-t border-border">
              {columns.map((col) => (
                <td key={String(col.key)} className="px-4 py-3 text-sm text-text-main">
                  {col.render ? col.render(row) : String(row[col.key] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
