import { ArrowLeft, ArrowRight, BookOpen, ExternalLink, FileText, FlaskConical, Layers3, Map, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { PlatformShell } from '../components/navigation/PlatformShell'
import { courses, pdfPages, pdfUrl, stages } from './learningContent'

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

function SectionHeading({ title, description }: { title: string; description: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-xl font-semibold text-text-main">{title}</h2>
      <p className="mt-1 text-sm leading-6 text-text-sub">{description}</p>
    </div>
  )
}

export function LearningCenterPage() {
  const navigate = useNavigate()
  const { hash } = useLocation()
  const [activeStageIndex, setActiveStageIndex] = useState(0)
  const activeStage = stages[activeStageIndex]
  const activeStageCourses = courses.filter((course) => activeStage.courseIds.includes(course.id))

  useEffect(() => {
    if (hash === '#learning-paths') {
      document.getElementById('learning-paths')?.scrollIntoView()
    }
  }, [hash])

  return (
    <PlatformShell>
      <main className="min-h-screen px-5 py-6 sm:px-8 sm:py-8 lg:px-10">
        <div className="mx-auto w-full max-w-[1400px] space-y-6 lg:space-y-7">
          <section className="relative isolate overflow-hidden rounded-token-xl border border-border bg-gradient-to-r from-white via-white to-blue-50/80 px-6 py-6 shadow-token-sm sm:px-8 sm:py-7">
            <div aria-hidden="true" className="pointer-events-none absolute -right-12 -top-24 -z-10 h-64 w-64 rounded-full bg-blue-100/60 blur-3xl" />
            <div className="flex flex-wrap items-end justify-between gap-5">
              <div>
                <Badge variant="info" className="bg-white/80"><Sparkles size={13} className="mr-1.5" />AgentForge 学习中心</Badge>
                <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">学习中心</h1>
                <p className="mt-2 max-w-2xl text-sm leading-7 text-text-sub sm:text-base">从会用平台开始，循序了解智能体原理，再把知识带进实践。</p>
              </div>
              <Button type="button" className="shrink-0" onClick={() => navigate('/learn/guide')}>开始学习 <ArrowRight size={15} /></Button>
            </div>
          </section>

          <nav aria-label="学习中心分区" className="platform-nav-scroll flex gap-1 overflow-x-auto border-b border-border/80 px-1">
            {[
              ['platform-guide', '使用指南'],
              ['learning-paths', '学习路径'],
              ['recommended-courses', '推荐课程'],
              ['learning-resources', '学习资料'],
              ['practice-cases', '实践案例'],
            ].map(([id, label]) => <a key={id} href={`#${id}`} className="shrink-0 rounded-t-token-md px-4 py-3 text-sm font-medium text-text-sub transition-colors hover:bg-surface hover:text-primary">{label}</a>)}
          </nav>

          <section id="platform-guide" aria-labelledby="platform-guide-title" className="scroll-mt-6">
            <div className="relative isolate overflow-hidden rounded-token-xl border border-primary/10 bg-gradient-to-br from-blue-50/80 via-white to-sky-50/60 p-6 sm:p-8">
              <div aria-hidden="true" className="pointer-events-none absolute -right-10 -top-14 -z-10 h-64 w-64 rounded-full border-[32px] border-white/60" />
              <div className="flex flex-col items-start justify-between gap-6 lg:flex-row lg:items-center">
                <div className="min-w-0 max-w-3xl">
                  <Badge variant="info" className="bg-white/80"><Map size={13} className="mr-1.5" />第一步 · 先会用平台</Badge>
                  <h2 id="platform-guide-title" className="mt-4 text-2xl font-semibold tracking-tight">AgentForge 使用指南</h2>
                  <p className="mt-2 text-sm leading-7 text-text-sub">从注册登录、创建智能体到模型配置、知识库和运行调试，快速熟悉 AgentForge 的主要操作。</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {['快速上手', '创建第一个智能体', '模型连接与配置', 'Embedding 与知识库', '工具与运行', '常见问题'].map((topic) => <Badge key={topic} variant="neutral" className="bg-white/85">{topic}</Badge>)}
                  </div>
                </div>
                <Button type="button" className="shrink-0 self-start lg:self-center" onClick={() => navigate('/learn/guide')}>查看使用指南 <ArrowRight size={15} /></Button>
              </div>
            </div>
          </section>

          <section id="learning-paths" aria-labelledby="learning-path-title" className="scroll-mt-6 rounded-token-xl border border-border bg-surface p-5 shadow-token-sm sm:p-7">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div><p className="text-xs font-semibold text-primary">学会使用平台后</p><h2 id="learning-path-title" className="mt-1 text-xl font-semibold">智能体学习路径</h2><p className="mt-1 text-sm leading-6 text-text-sub">选择一个阶段，按知识点和课程逐步实践。</p></div>
              <Badge variant="info">阶段 {activeStageIndex + 1} / {stages.length}</Badge>
            </div>
            <div className="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-5">
              {stages.map((stage, index) => <button key={stage.title} type="button" aria-pressed={activeStageIndex === index} onClick={() => setActiveStageIndex(index)} className={`group flex min-h-[76px] items-center gap-3 rounded-token-md border px-3 py-3 text-left transition-colors ${activeStageIndex === index ? 'border-primary/25 bg-blue-soft/70 text-primary' : 'border-transparent bg-bg hover:border-border hover:bg-bg-soft'}`}>
                <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${activeStageIndex === index ? 'bg-primary text-white' : 'bg-white text-text-muted shadow-token-sm'}`}>{index + 1}</span>
                <span className="min-w-0"><span className="block text-[11px] text-text-muted">阶段 {index + 1}</span><span className="mt-0.5 block truncate text-xs font-semibold sm:text-sm">{stage.title}</span></span>
              </button>)}
            </div>
            <div className="mt-4 grid gap-5 rounded-token-lg border border-border bg-gradient-to-r from-white to-bg/80 p-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:items-center sm:p-6">
              <div>
                <div className="flex items-center gap-2"><Layers3 size={17} className="text-primary" /><Badge variant="info">阶段 {activeStageIndex + 1}</Badge></div>
                <h3 className="mt-3 text-lg font-semibold">{activeStage.title}</h3>
                <p className="mt-2 text-sm leading-6 text-text-sub">{activeStage.description}</p>
                <ul className="mt-4 flex flex-wrap gap-2" aria-label={`${activeStage.title}知识点`}>{activeStage.topics.map((topic) => <li key={topic}><Badge variant="neutral">{topic}</Badge></li>)}</ul>
                <div className="mt-5 flex flex-wrap gap-2"><Button type="button" size="sm" onClick={() => navigate(`/learn/course/${activeStage.courseIds[0]}`)}>开始阶段 <ArrowRight size={14} /></Button><Button type="button" variant="secondary" size="sm" onClick={() => navigate('/develop/agents')}>去平台实践</Button></div>
              </div>
              <div className="rounded-token-lg border border-border/80 bg-white/80 p-4 sm:p-5">
                <p className="mb-3 text-xs font-semibold text-text-muted">本阶段推荐内容</p>
                <div className="space-y-2">{activeStageCourses.map((course) => <button key={course.id} type="button" onClick={() => navigate(`/learn/course/${course.id}`)} className="flex w-full items-center gap-3 rounded-token-md px-3 py-2.5 text-left transition-colors hover:bg-bg-soft">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-token-md bg-blue-soft text-primary"><BookOpen size={15} /></span><span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{course.title}</span><span className="mt-0.5 block truncate text-xs text-text-muted">{course.level} · {course.reading}</span></span><ArrowRight size={14} className="shrink-0 text-text-muted" />
                </button>)}</div>
              </div>
            </div>
          </section>

          <section id="recommended-courses" aria-labelledby="recommended-courses-title" className="scroll-mt-6">
            <SectionHeading title="推荐课程" description="从核心概念出发，结合原书阅读和平台实践继续学习。" />
            <div className="flex snap-x gap-3 overflow-x-auto pb-3">
              {courses.map((course) => <button key={course.id} type="button" onClick={() => navigate(`/learn/course/${course.id}`)} className="group flex w-[260px] shrink-0 snap-start flex-col rounded-token-lg border border-border bg-surface p-4 text-left shadow-token-sm transition hover:border-primary/25 hover:shadow-token-lg">
                <div className="flex items-center justify-between gap-2"><Badge variant={course.level === '入门' ? 'info' : 'warning'}>{course.level}</Badge><span className="text-[11px] text-text-muted">Hello-Agents</span></div><h3 className="mt-3 text-sm font-semibold">{course.title}</h3><p className="mt-2 line-clamp-2 flex-1 text-xs leading-5 text-text-sub">{course.description}</p><span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary">开始学习 <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" /></span>
              </button>)}
            </div>
          </section>

          <div className="grid gap-4 xl:grid-cols-2">
            <section id="learning-resources" aria-labelledby="learning-resources-title" className="scroll-mt-6">
              <SectionHeading title="学习资料" description="在站内阅读教程原文，保留 PDF 原始内容。" />
              <Card className="flex h-full flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-4"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-token-md bg-red-50 text-red-600"><FileText size={21} /></span><div><h3 id="learning-resources-title" className="text-base font-semibold">Hello-Agents《从零开始构建智能体》</h3><p className="mt-1 text-sm leading-6 text-text-sub">从基础理论到实际应用，系统讲解智能体设计与实现。</p><p className="mt-2 text-xs text-text-muted">PDF · {pdfPages} 页 · Datawhale</p></div></div>
                <Button type="button" className="shrink-0 self-start" onClick={() => navigate('/learn/read')}>在线阅读 <ArrowRight size={15} /></Button>
              </Card>
            </section>

            <section id="practice-cases" aria-labelledby="practice-cases-title" className="scroll-mt-6">
              <SectionHeading title="实践案例" description="查看公开智能体的配置与真实问答效果。" />
              <Card className="flex h-full flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-4"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-token-md bg-amber-50 text-amber-600"><FlaskConical size={21} /></span><div><h3 id="practice-cases-title" className="text-base font-semibold">知识竞赛助手</h3><p className="mt-1 text-sm leading-6 text-text-sub">从系统提示词、模型连接到资料检索，了解一个 RAG 智能体的配置方式。</p><div className="mt-3 flex flex-wrap gap-2">{['System Prompt', '模型连接', 'Embedding', '知识库', 'RAG'].map((topic) => <Badge key={topic} variant="neutral">{topic}</Badge>)}</div></div></div>
                <Button type="button" variant="secondary" className="shrink-0 self-start" onClick={() => navigate('/learn/cases/knowledge-quiz')}>查看案例 <ArrowRight size={14} /></Button>
              </Card>
            </section>
          </div>
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
          <LearningHeader title="课程未找到" subtitle="请从学习中心选择课程" backTo="/learn" />
          <Button type="button" className="mt-8" onClick={() => navigate('/learn')}>返回学习中心</Button>
        </div>
      </main>
      </PlatformShell>
    )
  }

  return (
    <PlatformShell>
    <main className="min-h-screen bg-bg text-text-main">
      <div className="mx-auto w-full max-w-6xl px-5 py-5 sm:px-8">
        <LearningHeader title={course.title} subtitle="学习要点 · 原文阅读 · 平台实践" backTo="/learn" />
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
        <LearningHeader title="Hello-Agents《从零开始构建智能体》" subtitle={`PDF · ${pdfPages} 页 · 当前从第 ${page} 页阅读`} backTo="/learn" />
        <div className="flex items-center justify-between gap-3 py-4">
          <p className="text-sm text-text-sub">使用浏览器内置 PDF 阅读器浏览、搜索和缩放。</p>
          <Button type="button" variant="secondary" size="sm" onClick={() => navigate('/learn')}>返回学习中心</Button>
        </div>
        <div className="min-h-[70vh] flex-1 overflow-hidden rounded-token-lg border border-border bg-surface shadow-token-sm">
          <iframe key={page} title="Hello-Agents PDF 在线阅读" src={`${pdfUrl}#page=${page}&view=FitH`} className="h-[calc(100vh-155px)] min-h-[70vh] w-full" />
        </div>
      </div>
    </main>
    </PlatformShell>
  )
}
