export interface GuidePart {
  title: string
  text: string
}

export interface GuideTopic {
  slug: string
  title: string
  summary: string
  entry: string
  steps: string[]
  parts?: GuidePart[]
  checks?: string[]
  relatedCourse?: string
  action?: { label: string; path: string }
}

export interface GuideModule {
  title: string
  description: string
  slugs: string[]
}

export const guideModules: GuideModule[] = [
  { title: '基础入门', description: '先找到入口，完成账号和第一个智能体。', slugs: ['account', 'home', 'first-agent'] },
  { title: '核心配置', description: '配置提示词、聊天模型与向量模型。', slugs: ['prompt', 'model', 'embedding', 'local-bge'] },
  { title: '知识与运行', description: '接入资料、工具，并通过对话和日志验证效果。', slugs: ['knowledge', 'rag', 'tools', 'run', 'preview', 'logs'] },
  { title: '应用与排错', description: '试用广场中的智能体，定位常见故障。', slugs: ['square', 'faq'] },
]

export const guideTopics: GuideTopic[] = [
  {
    slug: 'account', title: '注册与登录', summary: '用能接收验证码的合法邮箱地址创建账号，然后使用邮箱和密码登录。',
    entry: '首页右上角“登录” → “没有账号？去注册”；已有账号直接进入登录页。',
    steps: ['在注册页填写合法邮箱地址，点击“发送验证码”。', '到收件箱查收验证码；未收到时查看垃圾邮件，再按页面倒计时重发。', '填写验证码并完成邮箱验证，随后设置密码和昵称完成注册。', '注册完成后会进入首页；以后可用注册邮箱和密码登录。'],
    parts: [{ title: '邮箱范围', text: '登录邮箱不限于 QQ；163、Gmail、Outlook 等可接收邮件的地址均可用于注册。能否完成注册取决于验证码是否成功送达。' }],
    checks: ['邮箱已注册时直接登录或使用找回密码。', '验证码发送失败时，先检查后端邮件服务配置及网络；不要反复提交。'],
    action: { label: '前往注册', path: '/register' },
  },
  {
    slug: 'home', title: '首页功能介绍', summary: '从首页选择学习、开发或试用，形成“学 → 做 → 用”的路径。',
    entry: '访问 AgentForge 首页。',
    steps: ['“学习中心”用于平台使用教程、智能体知识课程和 Hello-Agents 阅读。', '“智能体开发”用于创建、配置、调试和运行自己的智能体，需要登录。', '“智能体广场”用于浏览、打开和试用已公开的智能体。'],
    action: { label: '返回首页', path: '/' },
  },
  {
    slug: 'first-agent', title: '创建第一个智能体', summary: '从开发端新建一个有名称、提示词和模型连接的智能体。',
    entry: '首页“智能体开发” → 左侧智能体仓库的“新建智能体”。',
    steps: ['登录后进入开发端，点击左侧“新建智能体”。', '在人设与逻辑中填写名称、核心提示词；按需要设置默认开场白。', '在模型连接区填写兼容接口的基础地址、接口密钥和模型名称。', '先点击“测试连接”检查模型配置，再点击“创建智能体”。', '创建后从左侧选择该智能体，继续配置工具、知识库并运行。'],
    checks: ['创建按钮不可用时，检查名称、核心提示词和模型连接的必填项。'],
    action: { label: '前往智能体开发', path: '/develop/agents' },
  },
  {
    slug: 'prompt', title: '人设与逻辑 / System Prompt', summary: '设置角色、目标、约束和回答方式，让提示词参与每轮对话。',
    entry: '智能体开发 → 选择或新建智能体 → “智能体配置” → “人设与逻辑”。',
    steps: ['填写能识别的智能体名称。', '在“核心提示词”写明角色、任务、回答边界和输出风格。', '保存智能体，再到对话预览中用同一问题验证行为是否符合预期。'],
    parts: [{ title: '基础写法示例', text: '你是一名学习助手。先给出简明答案，再解释依据；不确定时说明不确定，不编造来源。' }],
    checks: ['核心提示词会作为 System Prompt 注入执行，并非只显示在页面上。'],
    relatedCourse: 'prompt', action: { label: '去配置提示词', path: '/develop/agents' },
  },
  {
    slug: 'model', title: '模型连接与配置', summary: '理解 Base URL、API Key、Model Name，并接入符合 OpenAI-compatible 约定的模型服务。',
    entry: '智能体开发 → “智能体配置” → “模型连接”。',
    steps: ['从模型服务商获取兼容接口地址、自己的 API Key 和准确的模型名称。', '将三项分别填入“基础地址”“接口密钥”“模型名称”。', '点击“测试连接”，通过后保存；再用对话预览实际提问。'],
    parts: [
      { title: 'Base URL', text: '模型服务的接口基础地址，不是模型名称，也不是普通网页地址。使用服务商提供的 OpenAI-compatible 地址；当前页面禁止本机或内网地址。' },
      { title: 'API Key', text: '服务商发给你的接口凭据。只填入配置表单，不要写进提示词或公开内容。示例占位：YOUR_API_KEY。' },
      { title: 'Model Name', text: '服务商指定的模型 ID，必须与当前账号可用的模型一致。' },
      { title: 'OpenAI-compatible 与自定义服务', text: 'AgentForge 使用兼容 OpenAI 调用方式的接口；只要服务商的接口和所选模型能力兼容，就可以填写其地址和模型 ID，不限定为 DeepSeek。' },
      { title: 'DeepSeek 示例', text: '若使用 DeepSeek，可将服务商文档中的兼容接口地址填入 Base URL，将 deepseek-chat 填入 Model Name，并填入自己的密钥。此处不展示真实密钥。' },
    ],
    checks: ['401 invalid_api_key：核对密钥、账号权限与环境。', 'Invalid endpoint URL：核对 Base URL 是否为服务商给出的兼容接口地址。', '模型名错误或额度不足：核对 Model Name、账号额度与服务商返回信息。', '模型不能调用工具时，检查该模型是否支持工具调用。'],
    relatedCourse: 'llm-basics', action: { label: '去配置模型', path: '/develop/agents' },
  },
  {
    slug: 'embedding', title: 'Embedding 配置', summary: '为知识库选择文本向量化方式；它与负责对话的聊天模型分工不同。',
    entry: '智能体开发 → “智能体配置” → “向量模型（Embedding）”。',
    steps: ['选择“本地 BGE”或“OpenAI-compatible”。', '选择兼容接口时，填写向量接口地址、接口密钥和向量模型名称。', '选择本地 BGE 时确认模型名称，保存后再上传知识文档。', '上传后查看文档向量化状态，再用一个可在文档中找到答案的问题测试。'],
    parts: [{ title: '与聊天模型的区别', text: '聊天模型负责生成回答；Embedding 模型把文档和问题转为向量，供知识检索使用。两者可以来自不同提供商。' }],
    checks: ['更换向量模型后，已有文档可能需要重新处理才能使用一致的向量配置。'],
    relatedCourse: 'embedding', action: { label: '去配置向量模型', path: '/develop/agents' },
  },
  {
    slug: 'local-bge', title: '本地 BGE', summary: '了解本地中文向量模型适合什么场景，以及首次加载的预期。',
    entry: '智能体开发 → “智能体配置” → “向量模型（Embedding）” → 选择“本地 BGE”。',
    steps: ['在向量模型提供商中选择“本地 BGE”。', '确认模型名称并保存智能体配置。', '上传一份资料，等待向量化完成，再测试知识检索。'],
    parts: [{ title: '使用特点', text: '本地 BGE 用于将中文文本向量化，不需要外部 Embedding API Key；首次加载模型可能较慢，且需要本机具备模型权重和足够资源。' }],
    checks: ['首次加载慢时先等待；如持续失败，查看运行或后端日志以及模型文件是否可用。'],
    relatedCourse: 'embedding', action: { label: '去查看向量模型', path: '/develop/agents' },
  },
  {
    slug: 'knowledge', title: '知识库上传', summary: '把文件接入当前智能体，并检查解析与向量化是否成功。',
    entry: '智能体开发 → 选择智能体 → “知识库”。',
    steps: ['选择当前智能体后打开“知识库”。', '在上传区选择 PDF 或 Word（.docx）文件，填写可选标题并提交。', '等待文本解析、切片和向量化处理，查看文档的 Embedding 状态。', '用文档中明确出现的内容提问，并结合运行日志检查是否命中。'],
    parts: [{ title: '当前上传入口支持的文件', text: '前端上传控件支持 PDF 和 DOCX，单文件上限 100 MB。后端解析器也接受 UTF-8 TXT，但当前页面的文件选择与校验未开放 TXT 上传。' }],
    checks: ['“上传成功”表示文档已被接收；若向量化失败，仍需要检查 Embedding 与 Qdrant 状态。', '扫描版 PDF 若无法提取可复制文本，可能不能用于检索。'],
    relatedCourse: 'rag', action: { label: '去知识库实践', path: '/develop/agents' },
  },
  {
    slug: 'rag', title: 'RAG 检索', summary: '理解资料如何进入检索，以及为什么上传成功不等于一定命中。',
    entry: '智能体开发 → “知识库”上传资料；“运行智能体”提问并查看运行日志。',
    steps: ['上传文件，系统解析文本并切成片段。', 'Embedding 将片段向量化并写入 Qdrant。', '用户提问时，问题也被向量化，系统检索相关片段。', '检索结果注入模型上下文，再由模型生成回答。'],
    parts: [{ title: '处理流程', text: '上传文件 → 文本解析 → 切片 → Embedding → Qdrant → 用户提问 → 向量检索 → 知识注入 → 模型回答。' }],
    checks: ['上传成功 ≠ 一定检索成功。检查向量化状态、Qdrant、检索是否命中，以及提问是否与文档内容对应。', '向量链路失败时，项目可能回退到 SQL 关键词检索；回答质量仍需实际验证。'],
    relatedCourse: 'rag', action: { label: '去知识库实践', path: '/develop/agents' },
  },
  {
    slug: 'tools', title: '工具配置', summary: '为智能体选择可调用的工具，区分工具行动与普通模型回答。',
    entry: '智能体开发 → 选择智能体 → “工具”。',
    steps: ['在工具页勾选当前智能体可使用的工具。', '点击“保存工具配置”。', '用需要外部信息或计算的问题测试，并查看运行日志里的工具调用。'],
    parts: [{ title: '当前可见工具', text: '工具页当前提供“网页搜索”和“运算”。工具让模型在需要时获取公开网页信息或计算确定性表达式；并非每条消息都必然调用工具。工具插件市场按钮目前提示暂未开放。' }],
    checks: ['若没有工具调用，检查工具是否启用、问题是否需要工具，以及所用聊天模型是否支持工具调用。'],
    relatedCourse: 'tools', action: { label: '去配置工具', path: '/develop/agents' },
  },
  {
    slug: 'run', title: '运行智能体', summary: '保存配置后启动一次任务，再观察模型、知识库和工具的实际行为。',
    entry: '智能体开发 → 选择可用智能体 → 页面上方“运行智能体”。',
    steps: ['确认智能体配置已保存且显示“可用”。', '点击“运行智能体”，在右侧对话预览输入具体测试问题。', '观察回答及任务状态；需要时打开“运行日志”看检索、工具和错误详情。'],
    checks: ['按钮不可点击时，检查是否已选择可用智能体、当前任务是否仍在运行。', 'Redis 6379 未运行会影响运行前的限流检查。'],
    action: { label: '去运行智能体', path: '/develop/agents' },
  },
  {
    slug: 'preview', title: '对话预览', summary: '在开发端用真实问题测试当前智能体，而不是只看“配置成功”。',
    entry: '智能体开发页面右侧“对话预览”。',
    steps: ['选中并保存智能体，检查右侧是否出现默认开场白。', '输入一个能明确判断对错的问题并发送。', '比较回答是否符合提示词、是否使用了预期知识或工具。', '若显示失败，切换到运行日志查看具体阶段。'],
    checks: ['模型能回答，不代表知识库一定命中；需要结合检索日志判断。'],
    action: { label: '去对话预览', path: '/develop/agents' },
  },
  {
    slug: 'logs', title: '运行日志', summary: '通过时间线定位模型、Embedding、知识库与工具的故障阶段。',
    entry: '智能体开发 → 选择智能体 → “运行日志”；对话预览中也可进入日志。',
    steps: ['先发起一次任务，再打开“运行日志”。', '检查任务状态、运行时间线及错误信息。', '模型请求报错时检查模型连接；知识检索失败时检查 Embedding 和 Qdrant。', '工具未调用或失败时检查工具是否启用、策略与模型能力。'],
    checks: ['“暂无运行日志”表示当前没有可查看的执行；先运行一次智能体。'],
    action: { label: '去查看运行日志', path: '/develop/agents' },
  },
  {
    slug: 'square', title: '智能体广场', summary: '浏览和试用已发布的智能体；开发端用于配置自己的智能体。',
    entry: '首页“智能体广场”。',
    steps: ['进入广场，浏览已发布的智能体卡片。', '用搜索框查找感兴趣的智能体。', '打开卡片，在展示页试用其公开对话。'],
    checks: ['广场展示的是已公开的智能体；未发布的个人草稿仍在开发端。'],
    action: { label: '前往智能体广场', path: '/square' },
  },
  {
    slug: 'faq', title: '常见问题', summary: '快速定位邮箱、Redis、Qdrant、模型接口和知识检索问题。',
    entry: '遇到问题时，先看页面报错，再根据本页逐项核对服务和配置。',
    steps: [],
    parts: [
      { title: '邮箱验证码发不出去？', text: '检查后端 SMTP 环境变量、发件服务授权与网络；.env 通常不会随代码上传，部署者需自行配置。用户注册邮箱不限定 QQ，关键是能正常接收验证码。不要公开邮箱授权码。' },
      { title: 'Redis 6379 未运行？', text: '运行接口的限流检查依赖 Redis。确认 Redis/Memurai 服务在 127.0.0.1:6379 监听，再重新发起对话。' },
      { title: 'Qdrant 6333 未运行？', text: '向量知识入库和检索依赖 Qdrant。确认 127.0.0.1:6333 可访问，再检查文档向量化状态。' },
      { title: '401 invalid_api_key？', text: '检查当前智能体的接口密钥是否有效、是否属于该模型服务、账号是否有权限；不要把真实密钥发给他人。' },
      { title: 'Invalid endpoint URL？', text: '检查 Base URL 是否为提供商的 OpenAI-compatible 基础地址，是否遗漏协议、路径或填成了网页地址。' },
      { title: '文件上传成功但检索不到？', text: '依次检查文档可提取文本、Embedding 状态、Qdrant 是否运行、向量是否写入、检索是否命中，以及问题是否与文档相关。' },
      { title: '本地 BGE 第一次加载慢？', text: '首次加载可能读取或准备模型权重，耗时较长；持续失败时查看模型文件、机器资源和后端日志。' },
    ],
    action: { label: '返回学习中心', path: '/learn' },
  },
]

export const findGuideTopic = (slug: string | undefined) => guideTopics.find((topic) => topic.slug === slug)
