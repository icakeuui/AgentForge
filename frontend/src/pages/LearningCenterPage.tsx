import type { ComponentType } from 'react'
import { ArrowLeft, ArrowRight, BookOpen, ChevronRight, ExternalLink, FlaskConical, GraduationCap } from 'lucide-react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { PlatformShell } from '../components/navigation/PlatformShell'
import { courses, pdfPages, pdfUrl } from './learningContent'

export function LearningHeader({ title, subtitle, backTo = '/' }: { title: string; subtitle: string; backTo?: string }) {
  const navigate = useNavigate()

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
      <div className="flex min-w-0 items-center gap-3">
        <Button type="button" variant="ghost" size="icon" aria-label="返回" title="返回" onClick={() => navigate(backTo)}>
          <ArrowLeft size={16} />
        </Button>
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-token-md bg-primary/10 text-primary">
          <BookOpen size={19} />
        </span>
        <div className="min-w-0">
          <h1 className="text-lg font-semibold text-text-main">{title}</h1>
          <p className="text-sm text-text-sub">{subtitle}</p>
        </div>
      </div>
      <Badge variant="info">学 · 做 · 用</Badge>
    </header>
  )
}

const quickStartSteps = [
  {
    title: '创建智能体',
    text: '进入「智能体开发」，点击新建，填写智能体名称和用途，并按提示选择可用模型。',
  },
  {
    title: '添加知识资料',
    text: '根据需要上传 PDF 或 Word 等资料，让智能体能够结合这些内容回答问题。知识资料不是必选项，没有资料也可以使用智能体。',
  },
  {
    title: '开始使用',
    text: '在对话预览中向智能体提问，检查回答效果。满意后还可以发布到智能体广场，与其他人分享。',
  },
]

function EntryCard({
  icon: Icon,
  title,
  description,
  onClick,
  iconClass,
}: {
  icon: ComponentType<{ size?: number; className?: string }>
  title: string
  description: string
  onClick: () => void
  iconClass: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex min-h-[88px] w-full items-center gap-4 rounded-token-xl border border-border bg-surface px-5 py-4 text-left shadow-token-sm transition-colors hover:border-primary/25 sm:px-6 sm:py-5"
    >
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-token-md sm:h-11 sm:w-11 ${iconClass}`}>
        <Icon size={20} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-base font-semibold text-text-main group-hover:text-primary">{title}</span>
        <span className="mt-1 block text-sm leading-6 text-text-sub">{description}</span>
      </span>
      <ChevronRight size={18} className="shrink-0 text-text-muted transition-colors group-hover:text-primary" />
    </button>
  )
}

export function LearningCenterPage() {
  const navigate = useNavigate()

  return (
    <PlatformShell>
      <main className="min-h-screen px-5 py-7 sm:px-8 lg:px-10 lg:py-9">
        <div className="w-full space-y-6 lg:space-y-7">
          <section className="rounded-token-xl border border-primary/10 bg-gradient-to-r from-blue-soft via-blue-soft/60 to-white px-6 py-8 sm:px-9 sm:py-10">
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">学习中心</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-text-sub sm:text-base">从这里开始，轻松创建你的第一个 AI 智能体。</p>
          </section>

          <section aria-labelledby="quick-start-title">
            <div className="mb-4">
              <h2 id="quick-start-title" className="text-xl font-semibold text-text-main">快速上手</h2>
              <p className="mt-1 text-sm leading-6 text-text-sub">只需简单三步，就能创建自己的 AI 助手。</p>
            </div>
            <ol aria-label="快速上手步骤">
              {quickStartSteps.map((step, index) => (
                <li key={step.title} className="flex items-stretch gap-4 sm:gap-5">
                  <div className="flex w-10 shrink-0 flex-col items-center pt-6">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-primary/15 bg-blue-soft text-base font-semibold text-primary">
                      {index + 1}
                    </span>
                    {index < quickStartSteps.length - 1 ? (
                      <span aria-hidden="true" className="mt-3 w-px flex-1 rounded-full bg-primary/15" />
                    ) : null}
                  </div>
                  <div className={`min-w-0 flex-1 ${index < quickStartSteps.length - 1 ? 'pb-5' : ''}`}>
                    <div className="rounded-token-lg border border-border bg-surface px-5 py-6 shadow-token-sm sm:px-7 sm:py-7">
                      <h3 className="text-base font-semibold text-text-main">{step.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-text-sub">{step.text}</p>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
            <div className="mt-5">
              <Button type="button" onClick={() => navigate('/develop/agents')}>
                去创建智能体 <ArrowRight size={15} />
              </Button>
            </div>
          </section>

          <section aria-label="实践案例与深入学习">
            <div className="flex w-full flex-col gap-4 sm:gap-5">
              <EntryCard
                icon={FlaskConical}
                iconClass="bg-amber-50 text-amber-600"
                title="实践案例 · 知识竞赛助手"
                description="查看一个真实智能体的配置过程和应用效果。"
                onClick={() => navigate('/learn/cases/knowledge-quiz')}
              />
              <EntryCard
                icon={GraduationCap}
                iconClass="bg-blue-soft text-primary"
                title="想进一步了解 Agent？"
                description="学习 Agent 相关知识，阅读 Hello-Agents，了解智能体的工作原理与关键技术。"
                onClick={() => navigate('/learn/deep')}
              />
            </div>
          </section>

          <footer className="border-t border-border/80 pt-4 text-xs text-text-muted">AgentForge 学习中心 · 学习、搭建与实践</footer>
        </div>
      </main>
    </PlatformShell>
  )
}

export function LearningCoursePage() {
  const navigate = useNavigate()
  const { courseId } = useParams()
  const course = courses.find((item) => item.id === courseId)
  const relatedGuide: Record<string, string> = {
    'llm-basics': 'model',
    prompt: 'prompt',
    tools: 'tools',
    rag: 'knowledge',
    embedding: 'embedding',
    react: 'run',
    'complete-agent': 'first-agent',
  }

  if (!course) {
    return (
      <PlatformShell>
      <main className="min-h-screen bg-bg text-text-main">
        <div className="mx-auto w-full max-w-6xl px-5 py-5 sm:px-8">
          <LearningHeader title="课程未找到" subtitle="请从学习中心选择课程" backTo="/learn/deep" />
          <Button type="button" className="mt-8" onClick={() => navigate('/learn/deep')}>返回深入学习</Button>
        </div>
      </main>
      </PlatformShell>
    )
  }

  return (
    <PlatformShell>
    <main className="min-h-screen bg-bg text-text-main">
      <div className="mx-auto w-full max-w-6xl px-5 py-5 sm:px-8">
        <LearningHeader title={course.title} subtitle="学习要点 · 原文阅读 · 平台实践" backTo="/learn/deep" />
        <div className="grid gap-5 py-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,1fr)]">
          <Card>
            <div className="flex items-center gap-2"><Badge variant={course.level === '入门' ? 'info' : 'warning'}>{course.level}</Badge><span className="text-xs text-text-muted">来源：Hello-Agents</span></div>
            <h2 className="mt-5 text-xl font-semibold">{course.title}</h2>
            <p className="mt-3 text-sm leading-7 text-text-sub">{course.description}</p>
            <h3 className="mt-7 text-base font-semibold">这节课要理解</h3>
            <ul className="mt-3 space-y-3 text-sm leading-7 text-text-sub">
              {course.takeaways.map((point) => <li key={point} className="flex gap-3"><span className="font-semibold text-primary">•</span><span>{point}</span></li>)}
            </ul>
            <div className="mt-8 rounded-token-md border border-border bg-bg-soft p-4">
              <p className="text-sm font-semibold">对应原书：{course.reading}</p>
              <p className="mt-1 text-sm text-text-sub">从 PDF 第 {course.page} 页开始阅读；可用原生阅读器继续浏览整本教程。</p>
              <Button type="button" size="sm" className="mt-4" onClick={() => navigate(`/learn/read?page=${course.page}`)}>阅读原文 <BookOpen size={14} /></Button>
            </div>
          </Card>
          <Card className="self-start">
            <Badge variant="success">去实践</Badge>
            <h2 className="mt-4 text-base font-semibold">在 AgentForge 动手做</h2>
            <p className="mt-3 text-sm leading-7 text-text-sub">{course.practice}</p>
            <p className="mt-4 text-xs leading-5 text-text-muted">进入开发端后可选择已有智能体或新建智能体；具体配置项由当前智能体决定。</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {relatedGuide[course.id] ? (
                <Button type="button" variant="secondary" size="sm" onClick={() => navigate(`/learn/guide/${relatedGuide[course.id]}`)}>
                  查看平台操作指南 <BookOpen size={14} />
                </Button>
              ) : null}
              <Button type="button" variant="secondary" size="sm" onClick={() => navigate('/develop/agents')}>
                前往智能体开发 <ExternalLink size={14} />
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </main>
    </PlatformShell>
  )
}

export function LearningReaderPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const requestedPage = Number(searchParams.get('page'))
  const page = Number.isInteger(requestedPage) && requestedPage >= 1 && requestedPage <= pdfPages ? requestedPage : 1

  return (
    <PlatformShell>
    <main className="min-h-screen bg-bg text-text-main">
      <div className="mx-auto flex min-h-screen w-full max-w-[1600px] flex-col px-5 py-5 sm:px-8">
        <LearningHeader title="Hello-Agents《从零开始构建智能体》" subtitle={`PDF · ${pdfPages} 页 · 当前从第 ${page} 页阅读`} backTo="/learn/deep" />
        <div className="flex items-center justify-between gap-3 py-4">
          <p className="text-sm text-text-sub">使用浏览器内置 PDF 阅读器浏览、搜索和缩放。</p>
          <Button type="button" variant="secondary" size="sm" onClick={() => navigate('/learn/deep')}>返回深入学习</Button>
        </div>
        <div className="min-h-[70vh] flex-1 overflow-hidden rounded-token-lg border border-border bg-surface shadow-token-sm">
          <iframe key={page} title="Hello-Agents PDF 在线阅读" src={`${pdfUrl}#page=${page}&view=FitH`} className="h-[calc(100vh-155px)] min-h-[70vh] w-full" />
        </div>
      </div>
    </main>
    </PlatformShell>
  )
}
