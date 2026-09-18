# AgentForge 单智能体 ReAct + Tool Call 手动测试指南

## 1. 介绍

本文档旨在提供 AgentForge 单智能体 ReAct 执行系统的手动测试方法和一系列测试任务。这些测试任务基于 `SINGLE_AGENT_REACT_PLAN.md` 中定义的验收标准，旨在验证系统的功能性、稳定性和契约符合性。

## 2. 前置条件

在执行手动测试之前，请确保满足以下条件：

1.  **环境搭建**：已成功启动 AgentForge 后端服务和前端界面。
    *   推荐使用 `./scripts/start_fullstack_merged.sh` 脚本启动。
    *   确保后端服务在 `http://localhost:8000` 运行。
    *   确保前端界面在 `http://localhost:5173` 运行。
2.  **数据库配置**：后端数据库已正确配置并可访问。
    *   如果使用 SQLite，请确保 `DB_URL` 环境变量设置为 `sqlite+aiosqlite:///$(pwd)/agentforge_preview.db`。
    *   如果使用 PostgreSQL，请确保数据库角色和权限已正确设置。
3.  **Agent 创建**：已通过前端界面或 API 创建一个 Agent，并配置了 `filesystem` 工具。
    *   `system_prompt` 可以设置为："You are an AI coding agent. Use tools when needed. Always read file before writing. Keep output minimal and precise. Stop when task is complete."
    *   `model_config` 确保指向可用的 LLM 服务。
    *   `tools` 列表中包含 `filesystem/read_file`, `filesystem/write_file`, `filesystem/list_dir`。
4.  **工具安装与绑定**：确保 `filesystem` 工具已安装并绑定到 Agent。

## 3. 手动测试方法

以下是执行手动测试的通用步骤：

1.  **访问前端界面**：在浏览器中打开 `http://localhost:5173`。
2.  **选择 Agent**：选择您已创建并配置好的 Agent。
3.  **输入任务**：在输入框中输入测试任务描述。
4.  **观察执行**：
    *   观察前端界面上 Agent 的思考过程 (`thought`，即模型返回的 `content`)、工具调用 (`tool_call`) 和观察结果 (`observation`)。
    *   同时关注后端服务的日志输出，检查是否有错误或异常。
5.  **验证结果**：根据每个测试任务的具体要求，严格验证 Agent 的最终输出 (`final_answer`)、文件系统 Artifacts 变化或日志记录。

## 4. 测试任务

以下是基于 `SINGLE_AGENT_REACT_PLAN.md` 验收标准的测试任务列表。

### 4.1 功能验证

#### 任务 1: 读取文件并总结

**描述**：验证 Agent 能否成功读取沙盒内的文件内容，并对其进行总结。

**步骤**：
1.  在沙盒目录（例如，项目根目录下的 `sandbox` 文件夹）中创建一个名为 `test_read.txt` 的文件，并写入一些内容，例如："This is a test file for AgentForge. It contains some sample text that the agent should read and summarize."
2.  在前端界面输入任务："请读取 `test_read.txt` 文件的内容，并总结它。"
3.  **预期结果**：
    *   Agent 成功调用 `filesystem/read_file` 工具。
    *   Agent 返回对文件内容的准确总结。
    *   后端日志中记录了 `filesystem/read_file` 的工具调用和 Observation。

#### 任务 2: 创建新文件

**描述**：验证 Agent 能否成功在沙盒内创建一个新文件，并写入指定内容。

**步骤**：
1.  在前端界面输入任务："请在沙盒目录中创建一个名为 `new_file.txt` 的文件，并写入内容 'Hello, AgentForge!'"
2.  **预期结果**：
    *   Agent 成功调用 `filesystem/write_file` 工具。
    *   沙盒目录中出现 `new_file.txt` 文件，其内容为 "Hello, AgentForge!"。
    *   后端日志中记录了 `filesystem/write_file` 的工具调用和 Observation。

#### 任务 3: 修改单文件 (read → write)

**描述**：验证 Agent 能否先读取一个文件，然后修改其内容。

**步骤**：
1.  确保沙盒目录中存在 `test_read.txt` 文件（可使用任务 1 创建）。
2.  在前端界面输入任务："请读取 `test_read.txt` 文件的内容，然后在文件末尾追加一行 'This line was added by AgentForge.'"
3.  **预期结果**：
    *   Agent 成功调用 `filesystem/read_file` 工具。
    *   Agent 成功调用 `filesystem/write_file` 工具，写入完整的新内容。
    *   `test_read.txt` 文件的内容变为 "This is a test file for AgentForge. It contains some sample text that the agent should read and summarize.\nThis line was added by AgentForge."
    *   后端日志中记录了 `read_file` 和 `write_file` 的工具调用和 Observation。

#### 任务 4: 使用工具完成任务

**描述**：验证 Agent 能否综合运用多个工具（例如 `list_dir` 和 `read_file`）来完成一个更复杂的任务。

**步骤**：
1.  确保沙盒目录中存在多个文件（例如 `test_read.txt`, `new_file.txt`）。
2.  在前端界面输入任务："请列出沙盒目录中的所有文件，然后读取 `new_file.txt` 的内容。"
3.  **预期结果**：
    *   Agent 成功调用 `filesystem/list_dir` 工具，并获取文件列表。
    *   Agent 成功调用 `filesystem/read_file` 工具，并获取 `new_file.txt` 的内容。
    *   Agent 返回文件列表和 `new_file.txt` 的内容。
    *   后端日志中记录了 `list_dir` 和 `read_file` 的工具调用和 Observation。

#### 任务 5: 正确停止 ReAct

**描述**：验证 Agent 在完成任务后，能够正确地输出 `thought` 并返回符合 Final Answer Contract 的结果，从而停止 ReAct 循环。

**步骤**：
1.  在前端界面输入任务："请告诉我今天的日期。" (假设 Agent 没有工具可以获取实时日期，但会尝试思考并给出最终答案)
2.  **预期结果**：
    *   模型返回响应中包含非空的 `content` (即 `thought`)，且 `tool_calls` 为空。系统将其严格提取为 `final_answer`。
    *   ReAct 循环正常终止，状态流转为 `SUCCEEDED`。
    *   `termination_reason` 必须严格为 `SUCCESS` 枚举值。
    *   后端日志中完整记录了 `final_answer` 阶段及对应的状态。

### 4.2 稳定性验证

#### 任务 6: 达到 MAX_STEPS 限制

**描述**：验证 Agent 在达到最大步数限制时，系统能够强制终止执行并返回枚举化的 `MAX_STEPS_REACHED`。

**步骤**：
1.  创建一个 Agent，将其 `constraints.max_steps` 设置为一个较小的值（例如 2 或 3）。
2.  给 Agent 一个需要多步才能完成的任务，或者一个会陷入循环的任务。
3.  **预期结果**：
    *   Agent 执行步数达到 `MAX_STEPS` 后立即被引擎强行终止。
    *   状态必须流转为 `FAILED` 或 `TERMINATED` (取决于 Engine 规范)。
    *   `termination_reason` 必须严格为 `MAX_STEPS_REACHED` 枚举值。
    *   Agent 最终抛出的结果包含“达到最大步数限制”的相关信息。
    *   后端日志中准确记录了终止事件。

#### 任务 7: 工具调用失败 (Retry & Fallback)

**描述**：验证单轮单 tool call 规则及失败重试：工具调用失败时，触发一次重试，重试仍失败后追加带对应 `tool_call_id` 的 error observation，最终模型生成带 `thought` 的 Final Answer。

**步骤**：
1.  **模拟工具失败**：修改 `marketplace_tool_adapter.py`，使读取特定文件时强制返回 `ToolObservation` 错误。
2.  在前端界面输入任务："请读取 `error_path.txt` 文件。"
3.  **预期结果**：
    *   模型输出 `thought` 并仅发出一个 `tool_call`（调用失败）。
    *   系统记录失败并触发一次重试。
    *   重试仍失败后，系统将错误信息（需包含对应的 `tool_call_id`）作为 observation 追加给模型。
    *   模型最终生成包含解释性 `thought` 的 `final_answer`。
    *   ReAct 循环正常终止，`termination_reason` 为 `SUCCESS` (因模型最终成功解释了失败)。

#### 任务 8: Loop Protection 触发

**描述**：验证 Agent 在触发 Loop Protection 时，能够立刻停止并返回结构化错误。

**步骤**：
1.  **模拟循环**：通过特定输入诱导 Agent 反复发出相同的 `tool_call`。
2.  **预期结果**：
    *   系统检测到触发条件（连续相同 `tool_id`、参数及 observation hash）。
    *   系统强行阻断并终止执行，状态流转为 `FAILED` 或 `TERMINATED`。
    *   `termination_reason` 必须严格为 `ERROR_TERMINATED` 枚举值（或 `LOOP_DETECTED` 如果新增此枚举）。
    *   后端日志完整记录该过程。

## 5. 最终验收

所有测试任务都应能稳定通过，且在执行过程中：

*   Agent 不会陷入无限循环。
*   Agent 不会崩溃或出现 Silent Failure。
*   所有错误都应有明确的日志记录和可解释的错误信息。
*   `Execution Step Log Contract` 和 `Observation Contract` 必须严格遵守。
*   `Final Answer Contract` 必须统一。
