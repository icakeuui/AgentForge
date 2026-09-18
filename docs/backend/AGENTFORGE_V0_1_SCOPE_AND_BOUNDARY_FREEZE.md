版本：v1.0 冻结版 
 一、必须实现 
 ReAct执行引擎、PythonSandbox、ToolRuntime、ModelGateway（简化）、ExecutionLogs、CompetitionManager（基础） 
 二、明确不做 
 Workflow、可视化编排、插件市场、复杂多模型路由、前端设计 
 三、边界约束 
 不得在v0.1引入任何“流程编排能力”；所有执行必须为单Agent ReAct循环 
 四、禁止事项 
 禁止新增未定义字段；禁止引入隐式状态；禁止绕过ModelGateway调用模型 
