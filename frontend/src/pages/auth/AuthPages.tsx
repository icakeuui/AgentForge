import { ArrowLeft, Camera, Check, Copy, KeyRound, Loader2, LogIn, Mail, Plus, UserCircle, X } from 'lucide-react'
import { type ChangeEvent, type FormEvent, type ReactNode, useEffect, useRef, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import * as authAdapter from '../../features/auth/auth.adapter'
import { useAuthStore } from '../../features/auth/auth.store'
import { notify } from '../../features/notifications/notify'
import { cn } from '../../lib/cn'

type RegisterStep = 'email' | 'code' | 'password' | 'profile'
type PasswordStrength = 'weak' | 'medium' | 'strong'

const maxAvatarUploadSize = 5 * 1024 * 1024

function getFlowErrorCode(error: unknown): string | null {
  const raw = (error as { raw?: unknown })?.raw
  if (!raw || typeof raw !== 'object') return null
  const data = (raw as { data?: unknown }).data
  if (!data || typeof data !== 'object') return null
  const errorCode = (data as { error_code?: unknown }).error_code
  return typeof errorCode === 'string' ? errorCode : null
}

function getRetryAfter(error: unknown): number | null {
  const raw = (error as { raw?: unknown })?.raw
  if (!raw || typeof raw !== 'object') return null
  const data = (raw as { data?: unknown }).data
  if (!data || typeof data !== 'object') return null
  const retryAfter = (data as { retry_after_seconds?: unknown }).retry_after_seconds
  return typeof retryAfter === 'number' && Number.isFinite(retryAfter) ? retryAfter : null
}

function getFlowErrorDetail(error: unknown): string | null {
  const raw = (error as { raw?: unknown })?.raw
  if (!raw || typeof raw !== 'object') return null
  const data = (raw as { data?: unknown }).data
  if (!data || typeof data !== 'object') return null
  const detail = (data as { error_detail?: unknown }).error_detail
  return typeof detail === 'string' && detail.trim().length > 0 ? detail : null
}

function errorMessage(error: unknown): string {
  const candidate = error as { message?: unknown; raw?: { message?: unknown } }
  const flowCode = getFlowErrorCode(error)
  const flowDetail = getFlowErrorDetail(error)
  const messages: Record<string, string> = {
    EMAIL_PROVIDER_NOT_CONFIGURED: '系统邮件服务暂不可用，请稍后再试',
    EMAIL_SEND_FAILED: '验证码发送失败，请重试',
    EMAIL_SEND_RATE_LIMITED: '发送过于频繁，请稍后重试',
    EMAIL_ALREADY_REGISTERED: '该邮箱已注册，请直接登录',
    VERIFICATION_CODE_INVALID: '验证码不正确',
    VERIFICATION_CODE_EXPIRED: '验证码已过期，请重新发送',
    VERIFICATION_CODE_ATTEMPTS_EXCEEDED: '验证码错误次数过多，请重新发送',
    REGISTRATION_TOKEN_INVALID: '注册验证已失效，请重新验证邮箱',
    REGISTRATION_TOKEN_EXPIRED: '注册验证已过期，请重新验证邮箱',
    PASSWORD_CONFIRM_MISMATCH: '两次输入的密码不一致',
    ACCOUNT_DISABLED: '账号已停用',
  }
  if (flowCode === 'EMAIL_SEND_FAILED' && flowDetail) {
    return `验证码发送失败：${flowDetail}`
  }
  if (flowCode && messages[flowCode]) return messages[flowCode]
  if (typeof candidate.raw?.message === 'string') return candidate.raw.message
  if (typeof candidate.message === 'string') return candidate.message
  return '请求失败，请稍后重试'
}

function AuthFrame({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-bg px-4 py-8 text-text-main">
      <section className="w-full max-w-lg rounded-token-lg border border-border bg-surface p-5 shadow-token-lg sm:p-6">{children}</section>
    </main>
  )
}

function BackButton({ onBack }: { onBack: () => void }) {
  return (
    <Button type="button" size="icon" variant="ghost" className="-ml-2 shrink-0" aria-label="返回上一步" title="返回上一步" onClick={onBack}>
      <ArrowLeft size={17} />
    </Button>
  )
}

function AuthHeader({ icon, title, subtitle, onBack }: { icon: ReactNode; title: string; subtitle: string; onBack: () => void }) {
  return (
    <div className="mb-6 flex items-center gap-3">
      <BackButton onBack={onBack} />
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-token-md bg-primary/10 text-primary">{icon}</div>
      <div className="min-w-0">
        <h1 className="truncate text-lg font-semibold">{title}</h1>
        <p className="text-sm text-text-muted">{subtitle}</p>
      </div>
    </div>
  )
}

function passwordStrength(password: string): PasswordStrength {
  const categories = [/[a-zA-Z]/.test(password), /\d/.test(password), /[^a-zA-Z0-9]/.test(password)].filter(Boolean).length
  if (password.length >= 12 && categories >= 3) return 'strong'
  if (password.length >= 8 && categories >= 2) return 'medium'
  return 'weak'
}

function PasswordStrengthIndicator({ password }: { password: string }) {
  const strength = passwordStrength(password)
  const strengthIndex = strength === 'strong' ? 3 : strength === 'medium' ? 2 : 1
  const meta: Record<PasswordStrength, { label: string; text: string; bar: string }> = {
    weak: { label: '弱', text: 'text-error', bar: 'bg-error' },
    medium: { label: '中', text: 'text-warning', bar: 'bg-warning' },
    strong: { label: '强', text: 'text-success', bar: 'bg-success' },
  }

  return (
    <div className="space-y-2" aria-live="polite">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-text-sub">密码强度</span>
        <span className={cn('font-semibold', meta[strength].text)}>{meta[strength].label}</span>
      </div>
      <div className="grid grid-cols-3 gap-1">
        {[1, 2, 3].map((index) => (
          <span key={index} className={cn('h-1.5 rounded-full transition-colors duration-200', index <= strengthIndex ? meta[strength].bar : 'bg-bg-soft')} />
        ))}
      </div>
    </div>
  )
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(reader.error ?? new Error('读取头像失败'))
    reader.readAsDataURL(file)
  })
}

function AvatarUploader({
  value,
  disabled,
  onChange,
  onUploadingChange,
}: {
  value: string
  disabled?: boolean
  onChange: (avatarUrl: string) => void
  onUploadingChange?: (uploading: boolean) => void
}) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const mountedRef = useRef(true)
  const [previewUrl, setPreviewUrl] = useState(() => value)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      onUploadingChange?.(false)
    }
  }, [onUploadingChange])

  const setAvatarUploading = (nextUploading: boolean) => {
    setUploading(nextUploading)
    onUploadingChange?.(nextUploading)
  }

  const handleAvatarChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    event.target.value = ''
    if (!file) return
    if (!['image/png', 'image/jpeg'].includes(file.type)) {
      notify.error('请选择 PNG、JPG 或 JPEG 图片')
      return
    }
    if (file.size > maxAvatarUploadSize) {
      notify.error('头像文件不能超过 5MB')
      return
    }

    try {
      const preview = await readFileAsDataUrl(file)
      if (!mountedRef.current) return
      setPreviewUrl(preview)
      setAvatarUploading(true)
      const uploaded = await authAdapter.uploadAvatar(file)
      if (!mountedRef.current) return
      onChange(uploaded.avatar_url)
      setPreviewUrl(uploaded.avatar_url)
    } catch (error) {
      if (!mountedRef.current) return
      onChange('')
      setPreviewUrl('')
      notify.error(errorMessage(error))
    } finally {
      if (mountedRef.current) {
        setAvatarUploading(false)
      }
    }
  }

  return (
    <div className="space-y-2">
      <div className="text-xs font-medium text-text-sub">头像</div>
      <div className="flex items-center gap-4">
        <button
          type="button"
          className="group relative flex h-24 w-24 shrink-0 items-center justify-center overflow-visible rounded-full border border-border bg-bg-soft text-text-muted transition-colors duration-200 hover:border-primary/60 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={disabled || uploading}
          onClick={() => inputRef.current?.click()}
          aria-label="上传头像"
          title="上传头像"
        >
          <span className="flex h-full w-full items-center justify-center overflow-hidden rounded-full">
            {previewUrl ? <img src={previewUrl} alt="头像预览" className="h-full w-full object-cover" /> : <UserCircle size={34} />}
          </span>
          <span className="absolute -bottom-1 -right-1 flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface text-primary shadow-token-sm transition-colors duration-200 group-hover:bg-primary group-hover:text-white">
            {uploading ? <Loader2 size={16} className="animate-spin" /> : <Plus size={17} />}
          </span>
        </button>
        <input ref={inputRef} id="register-avatar-upload" type="file" accept="image/png,image/jpeg" className="hidden" onChange={handleAvatarChange} disabled={disabled || uploading} />
      </div>
    </div>
  )
}

function registerStepSubtitle(step: RegisterStep): string {
  if (step === 'email') return '先验证邮箱'
  if (step === 'code') return '输入邮件验证码'
  if (step === 'password') return '设置登录密码'
  return '填写公开资料'
}

export function LoginPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const login = useAuthStore((state) => state.login)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/" replace />

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (error) {
      notify.error(errorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthFrame>
      <AuthHeader icon={<LogIn size={20} />} title="登录 AgentForge" subtitle="邮箱和密码" onBack={() => navigate(-1)} />

      <form className="space-y-4" onSubmit={onSubmit}>
        <Input id="login-email" label="邮箱" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <Input
          id="login-password"
          label="密码"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? '登录中...' : '登录'}
        </Button>
      </form>

      <div className="mt-4 flex items-center justify-between text-sm">
        <Link className="text-primary hover:underline" to="/register">
          没有账号？去注册
        </Link>
        <Link className="text-text-muted hover:text-primary" to="/forgot-password">
          忘记密码
        </Link>
      </div>
    </AuthFrame>
  )
}

export function RegisterPage() {
  const navigate = useNavigate()
  const registerComplete = useAuthStore((state) => state.registerComplete)
  const [step, setStep] = useState<RegisterStep>('email')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [registrationToken, setRegistrationToken] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [avatarUrl, setAvatarUrl] = useState('')
  const [avatarUploading, setAvatarUploading] = useState(false)
  const [retryAfter, setRetryAfter] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const registrationRequestInFlightRef = useRef(false)

  useEffect(() => {
    if (retryAfter <= 0) return
    const timer = window.setInterval(() => {
      setRetryAfter((value) => Math.max(0, value - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [retryAfter])

  const clearRegistrationProgress = () => {
    setCode('')
    setRegistrationToken('')
    setPassword('')
    setConfirmPassword('')
    setDisplayName('')
    setAvatarUrl('')
    setAvatarUploading(false)
    setRetryAfter(0)
  }

  const handleBack = () => {
    if (step === 'email') {
      navigate(-1)
      return
    }
    if (step === 'code') {
      clearRegistrationProgress()
      setStep('email')
      return
    }
    if (step === 'password') {
      setStep('code')
      return
    }
    setStep('password')
  }

  const sendCode = async (event?: FormEvent) => {
    event?.preventDefault()
    if (registrationRequestInFlightRef.current) return
    registrationRequestInFlightRef.current = true
    setSubmitting(true)
    try {
      const response = await authAdapter.registerStart({ email })
      setCode('')
      setRegistrationToken('')
      setRetryAfter(response.retry_after_seconds)
      setStep('code')
    } catch (error) {
      const retry = getRetryAfter(error)
      if (retry !== null) setRetryAfter(retry)
      notify.error(errorMessage(error))
    } finally {
      registrationRequestInFlightRef.current = false
      setSubmitting(false)
    }
  }

  const verifyCode = async (event: FormEvent) => {
    event.preventDefault()
    if (registrationRequestInFlightRef.current) return
    registrationRequestInFlightRef.current = true
    setSubmitting(true)
    try {
      const verified = await authAdapter.registerVerify({ email, code: code.trim() })
      setRegistrationToken(verified.registration_token)
      setStep('password')
    } catch (error) {
      notify.error(errorMessage(error))
    } finally {
      registrationRequestInFlightRef.current = false
      setSubmitting(false)
    }
  }

  const confirmPasswordStep = (event: FormEvent) => {
    event.preventDefault()
    if (password !== confirmPassword) {
      notify.error('两次输入的密码不一致')
      return
    }
    setStep('profile')
  }

  const completeRegistration = async (event: FormEvent) => {
    event.preventDefault()
    if (registrationRequestInFlightRef.current) return
    registrationRequestInFlightRef.current = true
    setSubmitting(true)
    try {
      await registerComplete({
        email,
        registration_token: registrationToken,
        password,
        confirm_password: confirmPassword,
        display_name: displayName,
        avatar_url: avatarUrl.trim() ? avatarUrl.trim() : null,
      })
      navigate('/', { replace: true })
    } catch (error) {
      notify.error(errorMessage(error))
    } finally {
      registrationRequestInFlightRef.current = false
      setSubmitting(false)
    }
  }

  return (
    <>
      <AuthFrame>
        <AuthHeader icon={<Mail size={20} />} title="邮箱注册" subtitle={registerStepSubtitle(step)} onBack={handleBack} />

        {step === 'email' && (
          <form className="space-y-4" onSubmit={sendCode}>
            <Input id="register-email" label="邮箱" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? '发送中...' : '发送验证码'}
            </Button>
          </form>
        )}

        {step === 'code' && (
          <form className="space-y-4" onSubmit={verifyCode}>
            <Input id="verify-email" label="邮箱" type="email" autoComplete="email" value={email} readOnly required />
            <Input id="verify-code" label="验证码" autoComplete="one-time-code" inputMode="numeric" value={code} onChange={(event) => setCode(event.target.value)} required />
            <div className="flex items-center justify-between text-sm">
              <button type="button" className="text-primary hover:underline disabled:text-text-muted" disabled={submitting || retryAfter > 0} onClick={() => void sendCode()}>
                {retryAfter > 0 ? `${retryAfter} 秒后重新发送` : '重新发送验证码'}
              </button>
              <button
                type="button"
                className="text-text-muted hover:text-primary"
                onClick={() => {
                  clearRegistrationProgress()
                  setStep('email')
                }}
              >
                修改邮箱
              </button>
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? '验证中...' : '验证邮箱'}
            </Button>
          </form>
        )}

        {step === 'password' && (
          <form className="space-y-4" onSubmit={confirmPasswordStep}>
            <Input
              id="register-password"
              label="密码"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
            <PasswordStrengthIndicator password={password} />
            <Input
              id="register-confirm-password"
              label="确认密码"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
            />
            <Button type="submit" className="w-full">
              下一步
            </Button>
          </form>
        )}

        {step === 'profile' && (
          <form className="space-y-4" onSubmit={completeRegistration}>
            <AvatarUploader value={avatarUrl} disabled={submitting} onChange={setAvatarUrl} onUploadingChange={setAvatarUploading} />
            <Input id="register-name" label="昵称" autoComplete="nickname" value={displayName} onChange={(event) => setDisplayName(event.target.value)} required />
            <Button type="submit" className="w-full" disabled={submitting || avatarUploading}>
              {submitting ? '创建中...' : '完成注册'}
            </Button>
          </form>
        )}

        <div className="mt-4 text-sm">
          <Link className="text-primary hover:underline" to="/login">
            已有账号，去登录
          </Link>
        </div>
      </AuthFrame>

    </>
  )
}

export function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    try {
      const response = await authAdapter.requestPasswordReset(email)
      navigate('/reset-password', { state: { email, devCode: response.dev_code } })
    } catch (error) {
      notify.error(errorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthFrame>
      <AuthHeader icon={<KeyRound size={20} />} title="找回密码" subtitle="发送重置验证码" onBack={() => navigate(-1)} />
      <form className="space-y-4" onSubmit={onSubmit}>
        <Input id="forgot-email" label="邮箱" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? '发送中...' : '发送重置码'}
        </Button>
      </form>
    </AuthFrame>
  )
}

export function ResetPasswordPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const initialEmail =
    typeof location.state === 'object' && location.state !== null && 'email' in location.state
      ? String((location.state as { email?: unknown }).email ?? '')
      : ''
  const devCode =
    typeof location.state === 'object' && location.state !== null && 'devCode' in location.state
      ? String((location.state as { devCode?: unknown }).devCode ?? '')
      : ''
  const [email, setEmail] = useState(initialEmail)
  const [code, setCode] = useState(devCode)
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    try {
      await authAdapter.resetPassword({ email, code, new_password: password })
      const currentUser = useAuthStore.getState().user
      if (currentUser?.email.trim().toLowerCase() === email.trim().toLowerCase()) {
        useAuthStore.getState().clearSession()
      }
      notify.success('密码已更新')
      navigate('/login', { replace: true })
    } catch (error) {
      notify.error(errorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthFrame>
      <AuthHeader icon={<KeyRound size={20} />} title="重置密码" subtitle="设置新的登录密码" onBack={() => navigate(-1)} />
      <form className="space-y-4" onSubmit={onSubmit}>
        <Input id="reset-email" label="邮箱" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <Input id="reset-code" label="重置码" autoComplete="one-time-code" value={code} onChange={(event) => setCode(event.target.value)} required />
        <Input
          id="reset-password"
          label="新密码"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        <PasswordStrengthIndicator password={password} />
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? '更新中...' : '更新密码'}
        </Button>
      </form>
    </AuthFrame>
  )
}

export function ProfilePage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const updateProfile = useAuthStore((state) => state.updateProfile)
  const [isEditingName, setIsEditingName] = useState(false)
  const [displayName, setDisplayName] = useState('')
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)
  const [savingName, setSavingName] = useState(false)
  const [savingAvatar, setSavingAvatar] = useState(false)
  const avatarInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setDisplayName(user?.display_name ?? '')
  }, [user?.display_name])

  useEffect(() => () => {
    if (avatarPreview?.startsWith('blob:')) URL.revokeObjectURL(avatarPreview)
  }, [avatarPreview])

  if (!user) return <Navigate to="/login" replace />

  const handleAvatarSelection = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.currentTarget.files?.[0]
    event.currentTarget.value = ''
    if (!file) return
    if (!['image/png', 'image/jpeg'].includes(file.type)) {
      notify.error('请选择 PNG 或 JPG/JPEG 图片')
      return
    }
    if (file.size > maxAvatarUploadSize) {
      notify.error('头像文件不能超过 5MB')
      return
    }
    setAvatarFile(file)
    setAvatarPreview(URL.createObjectURL(file))
  }

  const cancelAvatarChange = () => {
    setAvatarFile(null)
    setAvatarPreview(null)
  }

  const saveAvatar = async () => {
    if (!avatarFile) return
    setSavingAvatar(true)
    try {
      const uploaded = await authAdapter.uploadAvatar(avatarFile)
      await updateProfile({ avatar_url: uploaded.avatar_url })
      setAvatarFile(null)
      setAvatarPreview(null)
      notify.success('头像已更新')
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '头像保存失败，请稍后重试')
    } finally {
      setSavingAvatar(false)
    }
  }

  const saveDisplayName = async () => {
    const normalizedName = displayName.trim()
    if (!normalizedName) {
      notify.error('昵称不能为空')
      return
    }
    if (normalizedName.length > 80) {
      notify.error('昵称不能超过 80 个字符')
      return
    }
    setSavingName(true)
    try {
      await updateProfile({ display_name: normalizedName })
      setDisplayName(normalizedName)
      setIsEditingName(false)
      notify.success('昵称已更新')
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '昵称保存失败，请稍后重试')
    } finally {
      setSavingName(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-4xl flex-col gap-6 overflow-auto px-5 py-8 md:px-10 md:py-12">
      <div>
        <div className="text-sm font-medium text-primary">账号设置</div>
        <div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-text-main">个人资料</h1>
          <p className="mt-2 text-sm text-text-muted">管理你的公开资料与账号信息</p>
        </div>
      </div>

      <section className="rounded-token-xl border border-border/80 bg-surface p-5 shadow-token-sm md:p-8">
        <div className="flex flex-col gap-6 border-b border-border/70 pb-7 sm:flex-row sm:items-center">
          <div className="relative h-20 w-20 shrink-0">
            <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-full border border-border bg-bg-soft text-lg font-semibold text-text-muted">
              {avatarPreview || user.avatar_url
                ? <img src={avatarPreview ?? user.avatar_url ?? ''} alt={`${user.display_name} 头像`} className="h-full w-full object-cover" />
                : <UserCircle size={34} />}
            </div>
            <button type="button" onClick={() => avatarInputRef.current?.click()} className="absolute bottom-0 right-0 flex h-8 w-8 items-center justify-center rounded-full border-2 border-surface bg-primary text-white shadow-token-sm transition-colors hover:bg-primary-hover" aria-label="更换头像">
              <Camera size={15} />
            </button>
          </div>
          <input ref={avatarInputRef} type="file" accept="image/png,image/jpeg" className="hidden" onChange={handleAvatarSelection} />
          <div className="min-w-0 flex-1">
            <div className="text-base font-semibold text-text-main">头像</div>
            <p className="mt-1 text-sm text-text-muted">支持 PNG、JPG 或 JPEG，文件大小不超过 5MB。</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button type="button" variant="secondary" size="sm" leftIcon={<Camera size={15} />} onClick={() => avatarInputRef.current?.click()}>
                更换头像
              </Button>
              {avatarFile && <>
                <Button type="button" size="sm" leftIcon={<Check size={15} />} disabled={savingAvatar} onClick={() => void saveAvatar()}>
                  {savingAvatar ? '保存中...' : '保存头像'}
                </Button>
                <Button type="button" variant="ghost" size="sm" leftIcon={<X size={15} />} disabled={savingAvatar} onClick={cancelAvatarChange}>取消</Button>
              </>}
            </div>
          </div>
        </div>

        <div className="divide-y divide-border/70">
          <div className="grid gap-3 py-5 sm:grid-cols-[150px_minmax(0,1fr)] sm:items-center">
            <div className="text-sm font-medium text-text-sub">昵称</div>
            {isEditingName ? <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <Input aria-label="昵称" value={displayName} maxLength={80} onChange={(event) => setDisplayName(event.target.value)} />
              <div className="flex shrink-0 gap-2">
                <Button type="button" size="sm" leftIcon={<Check size={15} />} disabled={savingName} onClick={() => void saveDisplayName()}>{savingName ? '保存中...' : '保存'}</Button>
                <Button type="button" size="sm" variant="secondary" leftIcon={<X size={15} />} disabled={savingName} onClick={() => { setDisplayName(user.display_name); setIsEditingName(false) }}>取消</Button>
              </div>
            </div> : <div className="flex items-center justify-between gap-4">
              <span className="truncate text-sm text-text-main">{user.display_name}</span>
              <Button type="button" variant="secondary" size="sm" onClick={() => setIsEditingName(true)}>编辑</Button>
            </div>}
          </div>
          <div className="grid gap-2 py-5 sm:grid-cols-[150px_minmax(0,1fr)] sm:items-center">
            <div className="text-sm font-medium text-text-sub">邮箱</div>
            <div className="text-sm text-text-muted">{user.email}</div>
          </div>
          <div className="grid gap-2 py-5 sm:grid-cols-[150px_minmax(0,1fr)] sm:items-center">
            <div className="text-sm font-medium text-text-sub">Search ID</div>
            <div className="flex items-center justify-between gap-3">
              <span className="font-mono text-sm text-text-muted">{user.search_id}</span>
              <Button type="button" size="icon" variant="ghost" title="复制 Search ID" onClick={() => { void navigator.clipboard.writeText(String(user.search_id)); notify.success('Search ID 已复制') }}>
                <Copy size={16} />
              </Button>
            </div>
          </div>
          <div className="grid gap-2 py-5 sm:grid-cols-[150px_minmax(0,1fr)] sm:items-center">
            <div className="text-sm font-medium text-text-sub">Team ID</div>
            <div className="truncate font-mono text-sm text-text-muted">{user.team_id ?? '—'}</div>
          </div>
        </div>

        <div className="mt-2 border-t border-border/70 pt-6">
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              void logout().then(() => navigate('/login', { replace: true }))
            }}
          >
            退出登录
          </Button>
        </div>
      </section>
    </div>
  )
}
