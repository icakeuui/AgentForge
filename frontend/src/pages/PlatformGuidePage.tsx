import { ArrowRight, BookOpen, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'

import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { PlatformShell } from '../components/navigation/PlatformShell'
import { LearningHeader } from './LearningCenterPage'
import { findGuideTopic, guideModules, guideTopics } from './platformGuideContent'

const guidePath = (slug: string) => `/learn/guide/${slug}`

function TopicList({ slugs }: { slugs: string[] }) {
  const navigate = useNavigate()

  return (
    <ol className="divide-y divide-border">
      {slugs.map((slug) => {
        const topic = findGuideTopic(slug)
        if (!topic) return null
        const number = guideTopics.findIndex((item) => item.slug === slug) + 1
        return (
          <li key={slug}>
            <button type="button" className="group flex w-full items-center justify-between gap-3 py-3 text-left" onClick={() => navigate(guidePath(slug))}>
              <span className="flex min-w-0 items-center gap-3">
                <span className="w-6 shrink-0 text-xs font-semibold text-primary">{String(number).padStart(2, '0')}</span>
                <span className="min-w-0 text-sm font-medium text-text-main group-hover:text-primary">{topic.title}</span>
              </span>
              <ArrowRight size={15} className="shrink-0 text-text-muted group-hover:text-primary" />
            </button>
          </li>
        )
      })}
    </ol>
  )
}

export function PlatformGuidePage() {
  const navigate = useNavigate()

  return (
    <PlatformShell>
    <main className="min-h-screen bg-bg text-text-main">
      <div className="mx-auto w-full max-w-6xl px-5 py-5 sm:px-8">
        <LearningHeader title="AgentForge 使用指南" subtitle="先会用平台，再学习智能体原理" backTo="/learn/deep" />
        <div className="space-y-7 py-8">
          <Card className="p-5 sm:p-6">
            <Badge variant="info">平台操作 · 15 个主题</Badge>
            <h2 className="mt-4 text-xl font-semibold">从第一次登录到运行自己的智能体</h2>
            <p className="mt-2 max-w-3xl text-sm leading-7 text-text-sub">按模块学习真实页面中的操作。每节都提供清晰入口、逐步操作和必要的配置说明；知识原理可继续到五阶段学习路径深入阅读。</p>
            <Button type="button" className="mt-5" onClick={() => navigate(guidePath('account'))}>从注册与登录开始 <ArrowRight size={15} /></Button>
          </Card>
          <div className="grid gap-4 md:grid-cols-2">
            {guideModules.map((module, index) => (
              <Card key={module.title} className="p-5">
                <Badge variant="neutral">模块 {index + 1}</Badge>
                <h2 className="mt-3 text-lg font-semibold">{module.title}</h2>
                <p className="mt-1 text-sm leading-6 text-text-sub">{module.description}</p>
                <div className="mt-4"><TopicList slugs={module.slugs} /></div>
              </Card>
            ))}
          </div>
          <Card className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-semibold">想进一步理解 Agent 原理？</h2>
              <p className="mt-1 text-sm text-text-sub">五阶段学习路径和 Hello-Agents 教程继续讲 Prompt、RAG、Embedding 与 ReAct。</p>
            </div>
            <Button type="button" variant="secondary" className="shrink-0 self-start" onClick={() => navigate('/learn/deep')}>
              前往智能体学习路径 <BookOpen size={15} />
            </Button>
          </Card>
        </div>
      </div>
    </main>
    </PlatformShell>
  )
}

export function PlatformGuideTopicPage() {
  const navigate = useNavigate()
  const { slug } = useParams()
  const topic = findGuideTopic(slug)
  const index = guideTopics.findIndex((item) => item.slug === slug)
  const moduleIndex = guideModules.findIndex((module) => module.slugs.includes(slug ?? ''))

  if (!topic) {
    return (
      <PlatformShell>
      <main className="min-h-screen bg-bg text-text-main">
        <div className="mx-auto w-full max-w-6xl px-5 py-5 sm:px-8">
          <LearningHeader title="教程未找到" subtitle="请从使用指南目录选择主题" backTo="/learn/guide" />
          <Button type="button" className="mt-8" onClick={() => navigate('/learn/guide')}>返回使用指南</Button>
        </div>
      </main>
      </PlatformShell>
    )
  }

  const previous = index > 0 ? guideTopics[index - 1] : null
  const next = index < guideTopics.length - 1 ? guideTopics[index + 1] : null

  return (
    <PlatformShell>
    <main className="min-h-screen bg-bg text-text-main">
      <div className="mx-auto w-full max-w-6xl px-5 py-5 sm:px-8">
        <LearningHeader title={topic.title} subtitle="AgentForge 使用指南" backTo="/learn/guide" />
        <div className="mx-auto max-w-4xl space-y-5 py-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Badge variant="info">{guideModules[moduleIndex]?.title}</Badge>
              <span className="text-xs text-text-muted">{index + 1} / {guideTopics.length}</span>
            </div>
            <Button type="button" variant="ghost" size="sm" onClick={() => navigate('/learn/guide')}>查看全部目录</Button>
          </div>

          <Card className="p-5 sm:p-7">
            <h2 className="text-xl font-semibold">{topic.title}</h2>
            <section className="mt-4 rounded-token-md bg-bg-soft p-4">
              <h3 className="text-sm font-semibold">这一步是做什么的</h3>
              <p className="mt-1 text-sm leading-7 text-text-sub">{topic.summary}</p>
            </section>
            <div className="mt-7 space-y-7">
              <section>
                <h2 className="text-base font-semibold">从哪里进入</h2>
                <p className="mt-2 text-sm leading-7 text-text-sub">{topic.entry}</p>
              </section>

              {topic.steps.length > 0 ? (
                <section>
                  <h2 className="text-base font-semibold">操作步骤</h2>
                  <ol className="mt-3 space-y-3">
                    {topic.steps.map((step, stepIndex) => (
                      <li key={step} className="flex gap-3 text-sm leading-7 text-text-sub">
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">{stepIndex + 1}</span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                </section>
              ) : null}

              {topic.slug === 'faq' ? (
                <section>
                  <h2 className="text-base font-semibold">按问题查看</h2>
                  <div className="mt-3 space-y-2">
                    {topic.parts?.map((part) => (
                      <details key={part.title} className="rounded-token-md border border-border bg-bg-soft px-4 py-3">
                        <summary className="cursor-pointer text-sm font-medium text-text-main">{part.title}</summary>
                        <p className="mt-3 text-sm leading-7 text-text-sub">{part.text}</p>
                      </details>
                    ))}
                  </div>
                </section>
              ) : topic.parts?.length ? (
                <section>
                  <h2 className="text-base font-semibold">配置项说明</h2>
                  <div className="mt-3 space-y-3">
                    {topic.parts.map((part) => (
                      <div key={part.title} className="rounded-token-md border border-border bg-bg-soft p-4">
                        <h3 className="text-sm font-semibold">{part.title}</h3>
                        <p className="mt-1 text-sm leading-7 text-text-sub">{part.text}</p>
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}

              {topic.checks?.length ? (
                <section>
                  <h2 className="text-base font-semibold">检查与常见问题</h2>
                  <ul className="mt-3 list-inside list-disc space-y-2 text-sm leading-7 text-text-sub">
                    {topic.checks.map((check) => <li key={check}>{check}</li>)}
                  </ul>
                </section>
              ) : null}
            </div>
          </Card>

          <Card className="p-5">
            <h2 className="text-base font-semibold">下一步</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {topic.action ? <Button type="button" size="sm" onClick={() => navigate(topic.action!.path)}>{topic.action.label} <ExternalLink size={14} /></Button> : null}
              {topic.relatedCourse ? <Button type="button" variant="secondary" size="sm" onClick={() => navigate(`/learn/course/${topic.relatedCourse}`)}>学习相关原理 <BookOpen size={14} /></Button> : null}
              {next ? <Button type="button" variant="secondary" size="sm" onClick={() => navigate(guidePath(next.slug))}>下一篇：{next.title} <ChevronRight size={14} /></Button> : null}
            </div>
          </Card>
          <div className="flex flex-wrap items-center justify-between gap-3 pb-8">
            {previous ? <Button type="button" variant="ghost" size="sm" onClick={() => navigate(guidePath(previous.slug))}><ChevronLeft size={14} />上一篇：{previous.title}</Button> : <span />}
            <Button type="button" variant="ghost" size="sm" onClick={() => navigate('/learn')}>返回学习中心</Button>
          </div>
        </div>
      </div>
    </main>
    </PlatformShell>
  )
}
