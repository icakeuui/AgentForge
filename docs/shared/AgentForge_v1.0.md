# AgentForge 智能体搭建平台

产品定位、分析与冻结版改进报告（ReAct + Python，无 Workflow 初始版）

版本：v1.0（冻结版）\
日期：2026-04-08\
状态：可冻结（Freeze-Level Spec）\
适用范围：高校 AI 智能体竞赛平台（TRAE 合作）

***

# 一、冻结声明

本版本在以下约束下完成：

1. 严格保留原始系统总体架构方向（智能体平台 + 模型网关 + RAG + 插件体系）
2. 初始版本明确不实现 Workflow Engine（仅保留设计，不进入开发）
3. 执行范式统一为：ReAct + Python
4. 所有改动为“范围收敛”，非架构推翻
5. 本文档可直接用于 v0.1 开发冻结

***

# 二、产品定位（冻结版）

## 2.1 核心定位

AgentForge 是一个基于 ReAct 推理范式与 Python 执行能力的智能体开发与执行平台，服务于高校 AI 智能体竞赛场景，提供低门槛智能体构建、调试与执行能力。

***

## 2.2 产品本质

平台由三层能力构成：

1. 智能体构建层（Prompt + 工具配置）
2. 推理执行层（ReAct + Python）
3. 运行控制层（资源限制 + 日志审计）

说明：

初始版本不包含 Workflow 编排系统，避免复杂度失控。

***

# 三、执行范式（核心冻结）

## 3.1 统一执行模型

所有智能体执行遵循：

ReAct（Reason + Act） + Python Tool Execution

***

## 3.2 执行流程

1. 用户输入问题
2. LLM 进行推理（Reason）
3. 输出 Action（调用 Python / 工具）
4. 执行 Action
5. 返回 Observation
6. LLM 继续推理
7. 达到终止条件输出最终结果

***

## 3.3 ReAct 数据结构（冻结）

LLM 输出：

{
"thought": "...",
"action": "...",
"action\_input": {...}
}

执行返回：

{
"observation": {...}
}

***

## 3.4 执行控制参数

- max\_steps：默认 5
- timeout：单步执行限制
- error\_policy：失败即终止

***

# 四、系统架构（收敛版）

## 4.1 核心模块（保留）

### 1. Agent Service

- 创建智能体
- 配置 Prompt
- 绑定工具

***

### 2. Model Gateway（简化版）

- 统一模型调用接口
- Token 统计
- 基础限流

***

### 3. Python Execution Sandbox（核心模块）

- 执行 Python 代码
- JSON 输入输出
- 隔离运行环境

***

### 4. Tool System（轻量版 Plugin）

- API 工具
- Python 工具
- 统一调用接口

***

### 5. Execution Log System

- 全流程记录
- 模型调用记录
- Python 执行记录

***

## 4.2 暂不实现模块（冻结排除）

以下模块保留设计，但不进入 v0.1：

- Workflow Engine（DAG）
- 可视化编排画布
- 插件市场
- MCP 协议
- 多模型复杂路由

***

# 五、智能体结构（冻结）

## 5.1 Agent 组成

每个 Agent 包含：

- system\_prompt
- model\_config
- tool\_list
- memory（可选）
- constraints（执行限制）

***

## 5.2 Tool 定义规范

统一接口：

{
"name": "tool\_name",
"description": "...",
"input\_schema": {...},
"output\_schema": {...}
}

***

# 六、竞赛控制层（非侵入增强）

## 6.1 Competition Manager

功能：

- 比赛配置（时间、规则）
- 队伍管理
- Token 配额
- 模型权限控制
- 排行榜

说明：

该模块独立存在，不修改核心执行逻辑。

***

## 6.2 资源控制

通过 Model Gateway 实现：

- 每队 Token 限制
- 调用频率限制
- API Key 隐藏

***

# 七、调试与可观测性（核心能力）

## 7.1 调试能力（P0）

必须支持：

- ReAct 步骤可视化
- 每一步 thought / action / observation 展示
- Python 执行结果查看

***

## 7.2 日志结构（增强）

execution\_logs 记录：

- prompt\_input
- react\_steps
- tool\_calls
- python\_exec\_logs
- token\_usage
- error\_message

***

# 八、功能范围（冻结）

## 8.1 v0.1 必须实现

- ChatAgent（基于 ReAct）
- Python Tool 执行
- Tool 调用系统
- Model Gateway（简化）
- Execution Logs
- 基础调试面板
- Competition Manager（基础版）

***

## 8.2 v0.1 明确不做

- Workflow
- 可视化拖拽
- 插件市场
- 高级调度系统

***

# 九、版本策略

## v0.1（当前冻结版本）

目标：

- 保证竞赛可用
- 降低复杂度
- 提供稳定执行环境

***

## v0.5（后续扩展）

- 引入 Workflow Engine
- 引入可视化编排
- 增强 RAG 能力

***

## v1.0（平台化阶段）

- 插件生态
- MCP 协议
- 多模型策略

***

# 十、商业化约束（冻结）

当前阶段：

- 不实现付费系统
- 不引入商业化逻辑
- 保留 Token 使用统计能力

***

# 十一、冻结结论

本版本具备以下特征：

1. 明确去除 Workflow 初始复杂度
2. 统一执行范式为 ReAct + Python
3. 保留原平台架构方向，不做推翻
4. 功能收敛至可在竞赛中稳定运行的最小系统

结论：

该文档为 AgentForge v0.1 可执行冻结规范，可直接进入开发阶段。
