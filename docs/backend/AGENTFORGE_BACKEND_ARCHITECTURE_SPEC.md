版本：v1.0 冻结版 
 目标：定义后端整体架构与模块边界，不涉及前端实现 
 一、架构总览 
 系统采用分层架构：API层（FastAPI）→ 服务层（Services）→ 核心引擎层（ExecutionEngine/ModelGateway/ToolRuntime/PythonSandbox）→ 数据层（PostgreSQL/Redis/Object Storage） 
 二、核心模块 
 1. AgentService：管理Agent配置（CRUD） 
 2. ExecutionEngine：执行ReAct循环，负责状态与上下文管理 
 3. ModelGateway：统一模型调用、限流、统计 
 4. ToolRuntime：统一工具调用 
 5. PythonSandbox：执行Python代码，强隔离 
 6. ExecutionLogService：记录与查询执行日志 
 7. CompetitionManager：比赛配置与配额控制 
 三、模块边界 
 API层仅调用Service层；Service层仅调用核心引擎；核心引擎不得直接访问数据库（通过Service） 
 四、并发模型 
 ExecutionEngine为无状态调度，执行上下文持久化于DB，支持水平扩展 
 五、非功能 
 所有外部调用必须可观测（trace_id），所有关键路径必须记录日志 
