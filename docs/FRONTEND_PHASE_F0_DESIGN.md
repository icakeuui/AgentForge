# AgentForge 前端 Phase F0 设计规范 (Freeze-Level)

**主题模式**: 浅色专业平台风格 (Light-first, Professional, Minimal)
**基准定位**: AI Agent 开发与运行控制平台 (Platform Console)

## 1. 平台信息架构 (Information Architecture)

基于专业控制台定位，整体功能分为以下五个核心模块：

- **Agents (核心业务)**
  - 列表视图：快速查看所有 Agent（状态、调用频次、健康度）。
  - 创建/配置：分步表单，最简操作路径（2-3步）。
  - 详情区：Agent 配置、环境变量、运行状态概览。
- **Execution / Runs (执行流与日志)**
  - 运行流状态（Running / Success / Failed）。
  - 执行触发区。
  - 终端级可读日志区（支持折叠/展开、代码高亮）。
- **Tool Marketplace (生态扩展)**
  - 市场列表卡片（安装/卸载状态）。
  - 工具绑定：快速挂载至指定 Agent。
- **Logs / Records (全局监控)**
  - 全局系统日志、调用记录追踪（Traceability）。
- **System / Settings (系统配置)**
  - 资源配额（Quota）、API Key 管理、全局系统设置。

## 2. 导航结构 (Navigation Structure)

采用典型的 **App Shell** 结构，保证空间利用率和操作一致性：

- **左侧边栏 (Sidebar - Main Navigation)**
  - Logo 与品牌区。
  - 一级导航：Agents, Executions, Tools, Logs, Settings。
  - 底部：用户/账号入口。
- **顶部全局栏 (Global Header)**
  - 面包屑导航 (Breadcrumbs)：清晰展示层级（如 `Agents / Data Analysis Agent / Settings`）。
  - 快捷操作：全局搜索 (CMD+K)、快捷创建。
- **页面标题区 (Page Header)**
  - 页面大标题 + 关键状态标签（Badge）。
  - 页面级主操作按钮（Primary CTA）。
- **主内容区 (Content Area)**
  - 白底卡片承载业务数据。
  - 灰底页面背景 (`#F8FAFC` / `slate-50`)。

## 3. Layout 方案 (Layout Scheme)

- **容器最大宽度**: 响应式自适应，针对大屏优化（`max-w-7xl` 或 100% 宽度留白）。
- **布局层次**: 
  - Level 1: 页面背景层（浅灰）。
  - Level 2: 导航/侧边栏层（纯白或极浅灰）。
  - Level 3: 内容卡片层（纯白，带 `shadow-sm` 和 `border-slate-200`）。
  - Level 4: 弹出层 / Drawer（悬浮层，高阴影 `shadow-xl`）。
- **空间系统**: 严格遵循 4px/8px 倍数间距（Tailwind scale）。

## 4. 设计 Token 基线 (Design Token Baseline)

基于 UI-UX Pro Max 分析，采用以下基线参数：

### 色彩系统 (Color Palette)
- **主背景 (Background)**: `#F8FAFC` (slate-50)
- **内容区 (Surface)**: `#FFFFFF` (white)
- **强调色/品牌色 (Primary)**: `#2563EB` (blue-600) 或 `#0F172A` (slate-900) 配合极简风
- **边框与分隔线 (Border)**: `#E2E8F0` (slate-200)
- **文本色 (Text)**: 
  - 主标题/正文: `#0F172A` (slate-900)
  - 弱化文本: `#64748B` (slate-500) 或 `#475569` (slate-600)
- **状态色 (Status)**:
  - 成功: `#16A34A` (green-600)
  - 错误: `#DC2626` (red-600)
  - 警告: `#D97706` (amber-600)
  - 信息: `#2563EB` (blue-600)

### 字体系统 (Typography)
- **主字体 (Sans)**: `Plus Jakarta Sans`（或系统默认 `Inter`, `system-ui`），现代、干净的 SaaS 感。
- **代码/日志字体 (Mono)**: `JetBrains Mono` 或 `Fira Code`。专为日志区和代码块优化。
- **层级规范**:
  - H1: 24px (text-2xl), font-semibold
  - H2: 20px (text-xl), font-medium
  - Body: 14px (text-sm), leading-relaxed (1.5)

### 阴影与圆角 (Effects & Borders)
- **圆角 (Radius)**: 适中圆角 `rounded-lg` (8px) 或 `rounded-xl` (12px)，不宜过度圆滑。
- **阴影 (Shadows)**: 
  - 卡片：`shadow-sm` + `border`（轻量感）。
  - 浮层/Modal：`shadow-xl` + 蒙层（`bg-slate-900/20`）。

### 组件准则 (UI Components)
- **Button**: 高对比度，主按钮深色/品牌色，次级按钮白底+边框。
- **Table / List**: 宽松行高，去除不必要的竖向分割线，突出数据行。
- **Log Console**: 黑底/深色卡片或灰底代码块，等宽字体，关键词高亮（Error = Red, Info = Blue），支持平滑滚动。

---
*本规范已冻结，后续所有前端开发 Phase (Coder) 必须严格遵循此规范。*