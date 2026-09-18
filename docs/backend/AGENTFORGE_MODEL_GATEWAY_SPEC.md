版本：v1.0 冻结版 
 职责：统一模型调用、限流、统计 
 接口： 
 chat(messages,config)->response 
 约束： 
 1. 必须通过gateway调用模型 
 2. 每次调用记录token_usage 
 3. 支持per-team token_limit与QPS限制 
 4. 错误统一包装返回 
