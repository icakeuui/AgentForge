import { ArrowRight, BookOpen, ChevronRight, FileText, Layers3 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { PlatformShell } from '../components/navigation/PlatformShell'
import { LearningHeader } from './LearningCenterPage'
import { courses, pdfPages, stages, type LearningCourse } from './learningContent'
import { findGuideTopic, guideModules, guideTopics } from './platformGuideContent'

function GuideTopicList({ slugs }: { slugs: string[] }) {
  const navigate = useNavigate()

  return (
    <ol className="divide-y divide-border">
      {slugs.map((slug) => {
        const topic = findGuideTopic(slug)
        if (!topic) return null
        const number = guideTopics.findIndex((item) => item.slug === slug) + 1
        return (
          <li key={slug}>
            <button type="button" className="group flex w-full items-center justify-between gap-3 py-2.5 text-left" onClick={() => navigate(`/learn/guide/${slug}`)}>
              <span className="flex min-w-0 items-center gap-3">
                <span className="w-6 shrink-0 text-xs font-semibold text-primary">{String(number).padStart(2, '0')}</span>
                <span className="min-w-0 text-sm font-medium text-text-main group-hover:text-primary">{topic.title}</span>
              </span>
              <ChevronRight size={15} className="shrink-0 text-text-muted group-hover:text-primary" />
            </button>
          </li>
        )
      })}
    </ol>
  )
}

export function DeepLearningPage() {
  const navigate = useNavigate()
  const [activeStageIndex, setActiveStageIndex] = useState(0)
  const activeStage = stages[activeStageIndex]
  const activeStageCourses = activeStage.courseIds
    .map((id) => courses.find((course) => course.id === id))
    .filter((course): course is LearningCourse => course !== undefined)
  const practicePath = activeStage.practice.guideSlug
    ? `/learn/guide/${activeStage.practice.guideSlug}`
    : activeStage.practice.to ?? '/develop/agents'

  return (
    <PlatformShell>
      <main className="min-h-screen">
        <div className="mx-auto w-full max-w-[1440px] space-y-8 px-5 py-7 sm:px-8 lg:px-10 lg:py-9">
          <LearningHeader title="深入学习 Agent" subtitle="从基础概念到实际开发，循序渐进地学习智能体技术。" backTo="/learn" />

          <section aria-labelledby="deep-path-title">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 id="deep-path-title" className="text-xl font-semibold text-text-main">五阶段学习路径</h2>
                <p className="mt-1 text-sm leading-6 text-text-sub">选择一个阶段，查看对应的学习目标、知识点、推荐课程与 Hello-Agents 章节。</p>
              </div>
              <Badge variant="info">阶段 {activeStageIndex + 1} / {stages.length}</Badge>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
              {stages.map((stage, index) => (
                <button
                  key={stage.title}
                  type="button"
                  aria-pressed={activeStageIndex === index}
                  onClick={() => setActiveStageIndex(index)}
                  className={`group flex min-h-[76px] items-center gap-3 rounded-token-md border px-3 py-3 text-left transition-colors ${activeStageIndex === index ? 'border-primary/25 bg-blue-soft/70 text-primary' : 'border-transparent bg-surface shadow-token-sm hover:border-border hover:bg-bg-soft'}`}
                >
                  <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${activeStageIndex === index ? 'bg-primary text-white' : 'bg-white text-text-muted shadow-token-sm'}`}>{index + 1}</span>
                  <span className="min-w-0"><span className="block text-[11px] text-text-muted">阶段 {index + 1}</span><span className="mt-0.5 block truncate text-xs font-semibold sm:text-sm">{stage.title}</span></span>
                </button>
              ))}
            </div>
            <div className="mt-4 rounded-token-xl border border-border bg-surface p-5 shadow-token-sm sm:p-6">
              <div className="grid gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
                <div>
                  <div className="flex items-center gap-2">
                    <Layers3 size={17} className="text-primary" />
                    <Badge variant="info">阶段 {activeStageIndex + 1}</Badge>
                  </div>
                  <h3 className="mt-3 text-lg font-semibold text-text-main">{activeStage.title}</h3>
                  <p className="mt-1 text-xs text-text-muted">{activeStage.description}</p>
                  <div className="mt-4">
                    <p className="text-xs font-semibold text-text-muted">学习目标</p>
                    <p className="mt-1 text-sm leading-6 text-text-sub">{activeStage.goal}</p>
                  </div>
                  <div className="mt-4">
                    <p className="text-xs font-semibold text-text-muted">本阶段知识点</p>
                    <ul className="mt-2 flex flex-wrap gap-2" aria-label={`${activeStage.title}知识点`}>
                      {activeStage.topics.map((topic) => <li key={topic}><Badge variant="neutral">{topic}</Badge></li>)}
                    </ul>
                  </div>
                  <div className="mt-5 flex flex-wrap gap-2">
                    {activeStageCourses.length > 0 && (
                      <Button type="button" size="sm" onClick={() => navigate(`/learn/course/${activeStageCourses[0].id}`)}>开始本阶段学习 <ArrowRight size={14} /></Button>
                    )}
                    <Button type="button" variant="secondary" size="sm" onClick={() => navigate(practicePath)}>{activeStage.practice.label}</Button>
                  </div>
                </div>
                <div className="rounded-token-lg border border-border/80 bg-white/80 p-4 sm:p-5 lg:self-start">
                  <p className="mb-3 text-xs font-semibold text-text-muted">本阶段推荐课程</p>
                  <div className="space-y-2">
                    {activeStageCourses.map((course) => (
                      <div key={course.id} className="rounded-token-md border border-border/70 bg-surface px-3 py-2.5">
                        <button type="button" onClick={() => navigate(`/learn/course/${course.id}`)} className="group flex w-full items-center gap-3 text-left">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-token-md bg-blue-soft text-primary"><BookOpen size={15} /></span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium text-text-main group-hover:text-primary">{course.title}</span>
                            <span className="mt-0.5 block truncate text-xs text-text-muted">{course.level} · {course.reading}</span>
                          </span>
                          <ChevronRight size={14} className="shrink-0 text-text-muted group-hover:text-primary" />
                        </button>
                        <div className="mt-1.5 flex items-center justify-between gap-2 pl-11">
                          <span className="truncate text-[11px] text-text-muted">Hello-Agents 原书第 {course.page} 页起</span>
                          <button type="button" className="shrink-0 text-[11px] font-medium text-primary hover:underline" onClick={() => navigate(`/learn/read?page=${course.page}`)}>阅读原文</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section aria-labelledby="deep-book-title">
            <div className="mb-4">
              <h2 id="deep-book-title" className="text-xl font-semibold text-text-main">Hello-Agents 原书阅读</h2>
              <p className="mt-1 text-sm leading-6 text-text-sub">在站内阅读完整 PDF 教材，支持翻页、缩放与搜索。</p>
            </div>
            <Card className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-4">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-token-md bg-red-50 text-red-600"><FileText size={21} /></span>
                <div>
                  <h3 className="text-base font-semibold text-text-main">Hello-Agents《从零开始构建智能体》</h3>
                  <p className="mt-1 text-sm leading-6 text-text-sub">从基础理论到实际应用，系统讲解智能体设计与实现。</p>
                  <p className="mt-2 text-xs text-text-muted">PDF · {pdfPages} 页 · Datawhale</p>
                </div>
              </div>
              <Button type="button" className="shrink-0 self-start" onClick={() => navigate('/learn/read')}>在线阅读 <ArrowRight size={15} /></Button>
            </Card>
          </section>

          <section aria-labelledby="deep-guide-title">
            <div className="mb-4">
              <h2 id="deep-guide-title" className="text-xl font-semibold text-text-main">平台使用与进阶操作</h2>
              <p className="mt-1 text-sm leading-6 text-text-sub">模型配置、Embedding、本地 BGE、知识库上传、RAG 检索、工具配置与运行日志等平台教程。</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {guideModules.map((module, index) => (
                <Card key={module.title} className="p-5">
                  <Badge variant="neutral">模块 {index + 1}</Badge>
                  <h3 className="mt-3 text-lg font-semibold text-text-main">{module.title}</h3>
                  <p className="mt-1 text-sm leading-6 text-text-sub">{module.description}</p>
                  <div className="mt-3"><GuideTopicList slugs={module.slugs} /></div>
                </Card>
              ))}
            </div>
          </section>

          <footer className="border-t border-border/80 pt-4 text-xs text-text-muted">深入学习 Agent · 五阶段学习路径 · Hello-Agents 教材 · 平台实践</footer>
        </div>
      </main>
    </PlatformShell>
  )
}
