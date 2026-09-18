import { Check, ChevronLeft, ChevronRight, LogOut, Moon, Palette, Sparkles, Sun, User } from 'lucide-react'
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuthStore } from '../../../features/auth/auth.store'
import { type ThemeMode, useThemeStore } from '../../../features/theme/theme.store'
import { cn } from '../../../lib/cn'

type MenuView = 'root' | 'theme'

const THEME_OPTIONS: Array<{ value: ThemeMode; label: string; description: string; icon: typeof Sun }> = [
  { value: 'light', label: '浅色', description: '明亮简洁的默认界面', icon: Sun },
  { value: 'dark', label: '深色', description: '低眩光的深色工作区', icon: Moon },
  { value: 'summer', label: '夏日青春', description: '清爽通透的青绿色夏日配色', icon: Sparkles },
]

function getAvatarInitials(displayName: string): string {
  const tokens = displayName
    .trim()
    .split(/\s+/)
    .filter((token) => token.length > 0)
    .slice(0, 2)

  if (tokens.length === 0) {
    return 'AF'
  }

  return tokens.map((token) => token[0]?.toUpperCase() ?? '').join('')
}

export function UserSummary() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const theme = useThemeStore((state) => state.theme)
  const setTheme = useThemeStore((state) => state.setTheme)

  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [menuView, setMenuView] = useState<MenuView>('root')
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!isMenuOpen) {
      setMenuView('root')
      return
    }

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target
      if (!(target instanceof Node)) {
        return
      }
      if (!containerRef.current?.contains(target)) {
        setIsMenuOpen(false)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    return () => window.removeEventListener('mousedown', handlePointerDown)
  }, [isMenuOpen])

  if (!user) {
    return null
  }

  const activeTheme = THEME_OPTIONS.find((option) => option.value === theme) ?? THEME_OPTIONS[0]
  const avatarInitials = getAvatarInitials(user.display_name)

  const toggleMenu = () => setIsMenuOpen((open) => !open)
  const handleSummaryKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      toggleMenu()
    }
  }

  return (
    <div className="border-t border-border p-3">
      <div
        ref={containerRef}
        role="button"
        tabIndex={0}
        aria-label="打开账户菜单"
        aria-haspopup="menu"
        aria-expanded={isMenuOpen}
        aria-controls="user-summary-menu"
        className={cn(
          'relative flex items-center gap-4 rounded-token-lg px-3 py-3.5 text-left outline-none transition-all duration-200',
          'cursor-pointer select-none hover:bg-bg-soft/60 focus-visible:ring-2 focus-visible:ring-primary/20',
          isMenuOpen && 'bg-bg-soft/70 shadow-token-sm',
        )}
        onClick={toggleMenu}
        onKeyDown={handleSummaryKeyDown}
      >
        <span
          className={cn(
            'group relative flex h-14 w-14 shrink-0 items-center justify-center rounded-full p-[2px] transition-all duration-200',
            'bg-[linear-gradient(145deg,rgba(255,255,255,0.96),rgba(233,248,245,0.78))] shadow-token-sm',
            isMenuOpen ? 'ring-2 ring-primary/20 shadow-token-xl' : 'group-hover:-translate-y-0.5 group-hover:shadow-token-xl',
          )}
          aria-hidden="true"
        >
          <span className="absolute inset-0 rounded-full border border-white/70" aria-hidden="true" />
          <span className="absolute inset-[6px] rounded-full bg-white/60 blur-[10px]" aria-hidden="true" />
          {user.avatar_url ? (
            <span className="relative h-full w-full overflow-hidden rounded-full border border-white/80 bg-bg-soft">
              <img src={user.avatar_url} alt="" aria-hidden="true" className="h-full w-full object-cover" />
            </span>
          ) : (
            <span className="relative flex h-full w-full items-center justify-center overflow-hidden rounded-full border border-white/80 bg-[linear-gradient(160deg,rgba(15,118,110,0.18),rgba(2,132,199,0.12),rgba(251,191,36,0.18))] text-sm font-semibold tracking-[0.08em] text-text-main">
              {avatarInitials}
            </span>
          )}
        </span>

        <div className="min-w-0 flex-1">
          <div className="truncate text-[15px] font-semibold leading-6 text-text-main">{user.display_name}</div>
          <div className="text-[12px] leading-5 text-text-muted">ID {user.search_id}</div>
        </div>

        <ChevronRight
          size={16}
          className={cn('shrink-0 text-text-muted transition-transform duration-200', isMenuOpen && 'rotate-90 text-text-main')}
        />

        {isMenuOpen ? (
          <div
            id="user-summary-menu"
            className="absolute bottom-full left-3 z-30 mb-2 w-[280px] rounded-token-lg border border-border bg-surface p-2 shadow-token-xl backdrop-blur"
            onClick={(event) => event.stopPropagation()}
          >
            {menuView === 'root' ? (
              <div className="space-y-1" role="menu" aria-label="账户菜单">
                <button
                  type="button"
                  className="flex w-full items-center gap-3 rounded-token-md px-3 py-2.5 text-left text-sm text-text-sub transition-all duration-200 hover:bg-bg-soft hover:text-text-main"
                  onClick={() => {
                    setIsMenuOpen(false)
                    navigate('/develop/profile')
                  }}
                >
                  <User size={16} />
                  <span className="flex-1">账户信息</span>
                </button>

                <button
                  type="button"
                  className="flex w-full items-center gap-3 rounded-token-md px-3 py-2.5 text-left text-sm text-text-sub transition-all duration-200 hover:bg-bg-soft hover:text-text-main"
                  onClick={() => setMenuView('theme')}
                >
                  <Palette size={16} />
                  <span className="flex-1">主题与颜色</span>
                  <span className="truncate text-xs text-text-muted">{activeTheme.label}</span>
                  <ChevronRight size={16} />
                </button>

                <div className="my-1 border-t border-border" />

                <button
                  type="button"
                  className="flex w-full items-center gap-3 rounded-token-md px-3 py-2.5 text-left text-sm text-text-sub transition-all duration-200 hover:bg-bg-soft hover:text-text-main"
                  onClick={() => {
                    void logout().then(() => navigate('/login', { replace: true }))
                  }}
                >
                  <LogOut size={16} />
                  <span className="flex-1">退出登录</span>
                </button>
              </div>
            ) : (
              <div className="space-y-2" role="menu" aria-label="主题与颜色">
                <button
                  type="button"
                  className="flex w-full items-center gap-2 rounded-token-md px-2 py-2 text-left text-sm font-medium text-text-sub transition-colors duration-200 hover:bg-bg-soft hover:text-text-main"
                  onClick={() => setMenuView('root')}
                >
                  <ChevronLeft size={16} />
                  返回
                </button>

                <div className="space-y-1">
                  {THEME_OPTIONS.map((option) => {
                    const Icon = option.icon
                    const selected = option.value === theme

                    return (
                      <button
                        key={option.value}
                        type="button"
                        className={cn(
                          'flex w-full items-start gap-3 rounded-token-md border px-3 py-2.5 text-left transition-all duration-200',
                          selected
                            ? 'border-primary bg-bg-soft text-text-main shadow-token-sm'
                            : 'border-transparent text-text-sub hover:border-border hover:bg-bg-soft hover:text-text-main',
                        )}
                        onClick={() => {
                          setTheme(option.value)
                          setIsMenuOpen(false)
                        }}
                      >
                        <Icon size={16} className="mt-0.5 shrink-0" />
                        <span className="min-w-0 flex-1">
                          <span className="block text-sm font-medium">{option.label}</span>
                          <span className="mt-0.5 block text-xs text-text-muted">{option.description}</span>
                        </span>
                        {selected ? <Check size={16} className="mt-0.5 shrink-0 text-primary" /> : null}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}
