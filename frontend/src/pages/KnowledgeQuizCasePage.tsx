import { ArrowRight, Bot, BookOpen, ChevronDown, Database, FileText, MessageSquareText, Search, ShieldCheck, Wrench } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { PlatformShell } from '../components/navigation/PlatformShell'
import { LearningHeader } from './LearningCenterPage'

type Example = {
  title: string
  question: string
  answer: string
  sources: string[]
  evidence: string[]
  note?: string
}

const examples: Example[] = [
  {
    title: '赛题方向',
    question: '2026AIC算法创新赛有哪些赛题方向？',
    answer: '规则共设置 7 道开放式赛题：算法模型创新、AI+软件创新、AI+硬件创新、AI+场景创新、AI+学科交叉、AI+创新创业、AI+OPC 创新创业。参赛团队可结合项目特点选择方向。',
    sources: ['2026AIC算法创新赛赛题规则汇总260506-1.pdf'],
    evidence: ['规则第 1–2 页列出赛题 1 至赛题 7 的名称与说明。'],
  },
  {
    title: '竞赛目录',
    question: '全球校园人工智能算法精英大赛进入国家竞赛目录了吗？在学校属于什么类别？',
    answer: '国家竞赛目录将“全球校园人工智能算法精英大赛”列为第 76 项，备注为“2023年新增”。沈阳航空航天大学《科技竞赛认定目录（2026版）》将该赛事省赛至校赛对应项列为 A2 类。',
    sources: ['附件1：国家竞赛目录.pdf', '沈阳航空航天大学大学生创新创业竞赛认定目录（2026版）.pdf'],
    evidence: ['国家目录第 76 项：全球校园人工智能算法精英大赛，2023年新增。', '学校 2026 版认定目录第 63 项：该赛事（省赛）→（校赛），认定类别 A2。'],
  },
  {
    title: 'RoboCup',
    question: 'RoboCup 是什么？',
    answer: 'RoboCup（Robot World Cup，机器人世界杯）是推动机器人技术与人工智能研究的国际性竞赛与学术活动，包含机器人足球、救援机器人、家庭服务机器人等方向。中国竞赛目录中列有“中国机器人大赛暨 RoboCup 机器人世界杯中国赛”。',
    sources: ['附件1：国家竞赛目录.pdf', '沈阳航空航天大学大学生创新创业竞赛认定目录（2026版）.pdf'],
    evidence: ['国家目录第 37 项列有“中国机器人大赛暨 RoboCup 机器人世界杯中国赛”。', '学校 2026 版认定目录第 9 项列出该中国赛校赛及餐厅 3D 清洁、卫浴 3D 清洁赛项，类别 A1。'],
    note: '回答中的 RoboCup 通用背景介绍属于补充说明；目录中的赛事名称与校内类别来自检索资料。',
  },
]

const knowledgeFiles = [
  { name: '2026AIC算法创新赛赛题规则汇总260506-1.pdf', purpose: '查询赛题方向、竞赛要求与作品提交规范。' },
  { name: '附件1：国家竞赛目录.pdf', purpose: '核对赛事是否列入国家普通高校竞赛目录。' },
  { name: '附件2：辽宁省竞赛目录.pdf', purpose: '查阅辽宁省普通高校大学生创新创业竞赛信息。' },
  { name: '沈阳航空航天大学大学生创新创业竞赛认定目录（2026版）.pdf', purpose: '核对学校竞赛分类、赛道与校赛认定信息。' },
]

const flowSteps = ['PDF 资料', '文档解析', '文本切片', 'BGE 向量化', 'Qdrant', '用户提问', '向量检索', '知识片段', '模型回答']

function ReadonlyField({ label, value, secret = false }: { label: string; value: string; secret?: boolean }) {
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-text-sub">{label}</p>
      <div aria-label={`${label}（只读）`} className="flex min-h-10 items-center rounded-token-md border border-border bg-bg-soft/70 px-3 py-2 text-sm text-text-main">
        <span className="min-w-0 break-all">{secret ? 'YOUR_API_KEY' : value}</span>
      </div>
    </div>
  )
}

function ConfigSection({ icon, title, badge, children }: { icon: React.ReactNode; title: string; badge?: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4 rounded-token-md border border-border bg-bg p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-token-md bg-primary/10 text-primary">{icon}</span>
          <h2 className="text-base font-semibold text-text-main">{title}</h2>
        </div>
        {badge ? <Badge variant="info">{badge}</Badge> : null}
      </div>
      {children}
    </section>
  )
}

function ChatBubble({ role, children }: { role: 'user' | 'assistant'; children: React.ReactNode }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[94%] rounded-token-md border px-3 py-2.5 text-sm leading-6 ${isUser ? 'border-primary/15 bg-primary/5 text-text-main' : 'border-border bg-surface text-text-main'}`}>
        <p className="mb-1 text-[11px] font-semibold text-text-muted">{isUser ? '你' : '知识竞赛助手'}</p>
        {children}
      </div>
    </div>
  )
}

export function KnowledgeQuizCasePage() {
  const navigate = useNavigate()
  const [activeExample, setActiveExample] = useState(0)
  const [showEvidence, setShowEvidence] = useState(false)
  const example = examples[activeExample]

  return (
    <PlatformShell>
    <main className="min-h-screen bg-bg text-text-main">
      <div className="mx-auto w-full max-w-7xl px-5 py-5 sm:px-8">
        <LearningHeader title="知识竞赛助手" subtitle="智能体配置 · 公开只读案例" backTo="/learn" />

        <div className="space-y-5 py-6">
          <section className="rounded-token-md border border-border bg-surface p-5 shadow-token-sm sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex min-w-0 items-start gap-3">
                <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-token-md bg-primary/10 text-primary"><Bot size={21} /></span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-semibold">知识竞赛助手</h2><Badge variant="success">公开只读案例</Badge></div>
                  <p className="mt-1 text-sm leading-6 text-text-sub">面向竞赛学习与备赛的问题解答助手，结合竞赛规则和目录资料提供有依据的回答。</p>
                  <div className="mt-3 flex flex-wrap gap-2">{['System Prompt', '模型连接', 'Embedding', '知识库', 'RAG'].map((tag) => <Badge key={tag} variant="neutral">{tag}</Badge>)}</div>
                </div>
              </div>
              <div className="grid min-w-[230px] flex-1 gap-3 sm:max-w-[390px] sm:grid-cols-2">
                <div className="rounded-token-md border border-border bg-bg-soft/40 p-3"><p className="text-xs text-text-muted">模型</p><p className="mt-1 truncate text-sm font-semibold">deepseek-chat</p></div>
                <div className="rounded-token-md border border-border bg-bg-soft/40 p-3"><p className="text-xs text-text-muted">配置状态</p><p className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-success"><ShieldCheck size={15} />静态只读展示</p></div>
              </div>
            </div>
            <div className="mt-5 flex gap-5 overflow-x-auto border-b border-border text-sm">
              <span className="shrink-0 border-b-2 border-primary px-1 pb-3 font-semibold text-primary">智能体配置</span>
              <span className="shrink-0 px-1 pb-3 text-text-muted">工具</span>
              <span className="shrink-0 px-1 pb-3 text-text-muted">知识库</span>
              <span className="shrink-0 px-1 pb-3 text-text-muted">运行效果</span>
            </div>
          </section>

          <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_390px] xl:grid-cols-[minmax(0,7fr)_minmax(340px,3fr)]">
            <div className="space-y-4">
              <ConfigSection icon={<Bot size={16} />} title="智能体基本信息">
                <div className="grid gap-3 md:grid-cols-2">
                  <ReadonlyField label="智能体名称" value="知识竞赛助手" />
                  <ReadonlyField label="功能定位" value="竞赛资料问答与备赛辅助" />
                </div>
                <p className="text-sm leading-6 text-text-sub">帮助用户理解竞赛规则、查询竞赛目录、分析赛题并整理备赛要点。案例配置来自提供的界面与材料，经脱敏后静态展示。</p>
              </ConfigSection>

              <ConfigSection icon={<MessageSquareText size={16} />} title="人设与逻辑" badge="System Prompt">
                <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(220px,0.42fr)]">
                  <ReadonlyField label="角色" value="专业的知识竞赛智能助手" />
                  <ReadonlyField label="回答风格" value="准确、清晰、分层说明" />
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-semibold">核心提示词</p>
                  <div aria-label="System Prompt 只读内容" className="whitespace-pre-wrap rounded-token-md border border-border bg-surface px-4 py-3 text-sm leading-7">你是一名专业的知识竞赛智能助手，负责帮助用户进行知识学习、竞赛备考和问题解答。

你的目标：
• 帮助用户快速理解各类知识点；针对竞赛题目提供答案、解题思路和相关背景。
• 对选择题分析选项并解释原因；根据复习需求整理知识框架、重点内容和记忆技巧。

回答原则：优先保证知识准确；不确定时明确说明；回答简洁清晰、重点突出；复杂知识点分层解释。</div>
                  <p className="text-xs text-text-muted">根据此前提供的配置界面可见内容整理；未显示部分不作补写。</p>
                </div>
              </ConfigSection>

              <div className="grid gap-4 xl:grid-cols-2">
                <ConfigSection icon={<Wrench size={16} />} title="模型连接">
                  <ReadonlyField label="Model Provider" value="OpenAI Compatible" />
                  <ReadonlyField label="Base URL" value="https://api.deepseek.com" />
                  <ReadonlyField label="API Key" value="" secret />
                  <ReadonlyField label="Model Name" value="deepseek-chat" />
                </ConfigSection>

                <ConfigSection icon={<Bot size={16} />} title="向量模型（Embedding）">
                  <ReadonlyField label="向量模型提供商" value="本地 BGE" />
                  <ReadonlyField label="向量模型名称" value="BAAI/bge-large-zh-v1.5" />
                  <p className="text-xs leading-5 text-text-muted">将知识库文档和用户查询转换成向量，支持语义检索。</p>
                </ConfigSection>
              </div>

              <ConfigSection icon={<Database size={16} />} title="知识库" badge="4 份 PDF">
                <div className="grid gap-3 xl:grid-cols-2">
                  {knowledgeFiles.map((file) => (
                    <div key={file.name} className="flex min-w-0 items-start gap-3 rounded-token-md border border-border bg-surface p-3.5">
                      <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-token-md bg-primary/10 text-primary"><FileText size={17} /></span>
                      <div className="min-w-0"><p className="break-words text-sm font-medium">{file.name}</p><p className="mt-1 text-xs text-text-muted">PDF · {file.purpose}</p></div>
                    </div>
                  ))}
                </div>
                <p className="text-xs leading-5 text-text-muted">以上是本案例引用的资料清单。此公开页不提供原始 PDF 下载，也不读取账户中的知识库记录。</p>
              </ConfigSection>

              <ConfigSection icon={<Search size={16} />} title="RAG 检索流程">
                <div className="flex flex-wrap items-center gap-2">
                  {flowSteps.map((step, index) => <span key={step} className="flex items-center gap-2"><span className="rounded-token-md border border-border bg-surface px-2.5 py-1.5 text-xs font-medium">{step}</span>{index < flowSteps.length - 1 ? <ArrowRight size={13} className="text-text-muted" /> : null}</span>)}
                </div>
                <p className="text-xs leading-5 text-text-muted">回答会结合检索到的相关片段；上传资料本身不代表每次提问都会命中相关内容。</p>
              </ConfigSection>

              <ConfigSection icon={<Wrench size={16} />} title="工具">
                <div className="flex flex-wrap items-center gap-2"><Badge variant="neutral">知识库检索</Badge><Badge variant="neutral">RAG 问答</Badge></div>
                <p className="text-sm leading-6 text-text-sub">本案例问答记录体现了知识库检索流程。现有材料未列出额外工具名称，因此不展示未核实的工具绑定。</p>
              </ConfigSection>
            </div>

            <aside className="overflow-hidden rounded-token-md border border-border bg-surface shadow-token-sm lg:sticky lg:top-5">
              <div className="flex h-14 items-center justify-between border-b border-border px-4">
                <div className="flex items-center gap-2"><span className="font-semibold text-text-main">对话预览</span><Badge variant="success">真实运行记录</Badge></div>
                <BookOpen size={16} className="text-text-muted" />
              </div>
              <div className="border-b border-border p-3">
                <div className="grid grid-cols-3 gap-2">
                  {examples.map((item, index) => <button key={item.title} type="button" onClick={() => { setActiveExample(index); setShowEvidence(false) }} className={`rounded-token-md border px-2 py-2 text-xs font-medium transition-colors ${activeExample === index ? 'border-primary/30 bg-primary/5 text-primary' : 'border-border bg-bg text-text-sub hover:bg-bg-soft'}`}>{`示例 ${index + 1}`}<span className="mt-0.5 block truncate text-[11px] font-normal">{item.title}</span></button>)}
                </div>
              </div>
              <div className="flex min-h-[440px] flex-col gap-4 bg-bg-soft/30 p-4">
                <div className="flex items-center gap-2 text-xs text-text-muted"><Database size={14} className="text-primary" />本轮回答参考知识库资料</div>
                <div className="space-y-3">
                  <ChatBubble role="user">{example.question}</ChatBubble>
                  <ChatBubble role="assistant">{example.answer}</ChatBubble>
                </div>
                <div className="mt-1 rounded-token-md border border-border bg-surface">
                  <button type="button" aria-expanded={showEvidence} onClick={() => setShowEvidence((value) => !value)} className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-xs font-semibold text-text-sub">
                    <span className="flex items-center gap-2"><Search size={14} className="text-primary" />查看检索依据</span><ChevronDown size={15} className={`transition-transform ${showEvidence ? 'rotate-180' : ''}`} />
                  </button>
                  {showEvidence ? <div className="space-y-3 border-t border-border px-3 py-3 text-xs leading-5">
                    <div><p className="font-semibold text-text-sub">引用资料</p><ul className="mt-1 list-inside list-disc text-text-muted">{example.sources.map((source) => <li key={source} className="break-words">{source}</li>)}</ul></div>
                    <div><p className="font-semibold text-text-sub">命中依据</p><ul className="mt-1 list-inside list-disc text-text-muted">{example.evidence.map((item) => <li key={item}>{item}</li>)}</ul></div>
                    {example.note ? <p className="rounded-token-md bg-bg-soft p-2 text-text-muted">{example.note}</p> : null}
                  </div> : null}
                </div>
                <div className="mt-auto flex items-center gap-2 rounded-token-md border border-border bg-surface px-3 py-2.5 text-xs text-text-muted"><span className="flex-1">静态对话记录 · 不调用模型</span><ShieldCheck size={15} className="text-success" /></div>
              </div>
            </aside>
          </div>

          <Card className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div><h2 className="text-base font-semibold">想亲自搭建？</h2><p className="mt-1 text-sm text-text-sub">登录后创建自己的智能体，案例页不会修改现有智能体。</p></div>
            <Button type="button" className="shrink-0 self-start" onClick={() => navigate('/develop/agents')}>登录后创建类似智能体 <ArrowRight size={15} /></Button>
          </Card>
        </div>
      </div>
    </main>
    </PlatformShell>
  )
}
