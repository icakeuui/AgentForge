export interface LearningCourse {
  id: string
  title: string
  description: string
  level: '入门' | '进阶'
  page: number
  reading: string
  takeaways: string[]
  practice: string
}

export interface LearningStage {
  title: string
  description: string
  topics: string[]
  courseIds: string[]
  platformLink: string
}

export const pdfUrl = '/learning/Hello-Agents.pdf'
export const pdfPages = 720

export const courses: LearningCourse[] = [
  {
    id: 'agent-intro', title: '初识智能体', level: '入门', page: 10, reading: '第一章 · 初识智能体',
    description: '理解 Agent 与固定 Workflow 的区别，认识感知、思考、行动、观察的循环。',
    takeaways: ['智能体围绕目标选择下一步行动，而固定流程通常预先定义步骤。', '模型、工具、环境反馈共同构成 Agent Loop。'],
    practice: '进入智能体开发，观察一个已有智能体的人设、工具与运行结果。',
  },
  {
    id: 'llm-basics', title: '大语言模型基础', level: '入门', page: 52, reading: '第三章 · 大语言模型基础',
    description: '了解语言模型如何理解上下文、生成回答，以及能力与局限。',
    takeaways: ['模型通过上下文生成输出，回答质量受提示和上下文影响。', '模型可能产生不准确内容，需要工具或知识来源辅助。'],
    practice: '打开模型连接，认识接口地址、模型名称和密钥各自的作用。',
  },
  {
    id: 'agent-loop', title: '5 分钟理解 Agent Loop', level: '入门', page: 16, reading: '第一章 · 智能体运行机制',
    description: '从一次用户输入出发，看智能体如何判断、调用工具并处理反馈。',
    takeaways: ['一次任务可以经历多轮思考与行动。', '每次工具返回都可能改变下一步计划。'],
    practice: '运行一个已有智能体，并在运行日志中观察执行步骤。',
  },
  {
    id: 'prompt', title: 'Prompt 与 System Prompt', level: '入门', page: 52, reading: '第三章 · 提示与语言模型',
    description: '用清晰的角色、目标、边界和输出格式控制智能体行为。',
    takeaways: ['System Prompt 定义持续生效的人设与规则。', '好的提示应明确任务、约束和期望输出。'],
    practice: '在“人设与逻辑”调整系统提示词，比较前后回答。',
  },
  {
    id: 'tools', title: '工具调用基础', level: '入门', page: 82, reading: '第四章 · 智能体经典范式构建',
    description: '学习智能体何时调用工具，以及工具结果如何进入后续推理。',
    takeaways: ['工具将模型的能力连接到外部操作或信息。', '工具的输入、输出和失败处理需要清晰定义。'],
    practice: '查看“工具”列表，为智能体配置可用工具并进行一次运行。',
  },
  {
    id: 'rag', title: 'RAG 与知识库', level: '进阶', page: 257, reading: '第八章 · 记忆与检索',
    description: '把自有资料接入智能体，让回答有可检索的知识依据。',
    takeaways: ['RAG 先检索相关片段，再把片段交给模型生成回答。', '知识库质量、切片与检索结果都会影响答案。'],
    practice: '在“知识库”上传一份资料，提问并观察检索结果。',
  },
  {
    id: 'embedding', title: 'Embedding 与向量检索', level: '进阶', page: 257, reading: '第八章 · 记忆与检索',
    description: '理解文本向量、相似度检索与向量数据库在 RAG 中的作用。',
    takeaways: ['Embedding 将文本映射为可比较的向量。', '向量检索帮助找到语义相关的知识片段。'],
    practice: '查看“向量模型”配置，再到知识库体验检索。',
  },
  {
    id: 'react', title: 'ReAct 智能体', level: '进阶', page: 82, reading: '第四章 · ReAct、规划与反思',
    description: '认识思考与行动交替的执行方式，以及规划和反思的用途。',
    takeaways: ['ReAct 让推理与工具行动交替进行。', '规划和反思有助于处理多步骤任务。'],
    practice: '运行智能体，并从运行日志中追踪行动与反馈。',
  },
  {
    id: 'multi-agent', title: '多智能体基础', level: '进阶', page: 372, reading: '第十章 · 智能体通信协议',
    description: '了解多个智能体的分工协作与 MCP、A2A 等通信概念。',
    takeaways: ['多智能体系统需要明确角色、交接与共享信息。', 'MCP、A2A 等协议解决不同层面的连接与协作问题。'],
    practice: '先设计一个单智能体的职责与工具边界；多智能体编排属于延伸学习。',
  },
  {
    id: 'complete-agent', title: '完整 Agent 应用', level: '进阶', page: 497, reading: '第十二章 · 智能体性能评估',
    description: '把提示词、模型、工具、知识库与评估结合为可运行的应用。',
    takeaways: ['先定义目标和评估标准，再逐项配置能力。', '通过真实任务和运行日志反复检查回答质量。'],
    practice: '参考“知识竞赛助手”，在开发端完成配置、运行与检查。',
  },
]

export const stages: LearningStage[] = [
  {
    title: '认识智能体', description: '建立概念：Agent、Workflow、LLM 和感知—思考—行动循环。',
    topics: ['什么是 Agent', 'Agent 与 Workflow', 'LLM 驱动原理', 'Agent Loop'],
    courseIds: ['agent-intro', 'llm-basics', 'agent-loop'], platformLink: '认识现有智能体',
  },
  {
    title: '搭建智能体', description: '把提示词、模型连接与工具组织成一个可运行的智能体。',
    topics: ['System Prompt', '模型连接与 OpenAI Compatible 接口', 'Agent 配置', '工具调用'],
    courseIds: ['prompt', 'tools'], platformLink: '配置智能体',
  },
  {
    title: '知识与检索', description: '学习 Embedding、向量数据库、RAG、知识库与记忆。',
    topics: ['Embedding', '向量检索', 'RAG 与知识库', 'Memory'],
    courseIds: ['embedding', 'rag'], platformLink: '体验知识库',
  },
  {
    title: '进阶智能体', description: '理解 ReAct、规划、反思、上下文工程与通信协议。',
    topics: ['ReAct / Planning / Reflection', '上下文工程', 'MCP / A2A'],
    courseIds: ['react', 'multi-agent'], platformLink: '查看运行过程',
  },
  {
    title: '综合实践', description: '通过案例、评估和完整应用，把所学连接到开发过程。',
    topics: ['案例学习', '多智能体概念', '智能体评估', '完整 Agent 应用'],
    courseIds: ['complete-agent'], platformLink: '前往智能体开发',
  },
]
