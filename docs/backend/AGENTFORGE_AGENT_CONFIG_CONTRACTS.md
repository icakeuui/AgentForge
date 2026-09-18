版本：v1.0 冻结版 
 Agent结构： 
 { 
  "id":uuid, 
  "system_prompt":string(required), 
  "model_config":{"model":string,"temperature":float,"max_tokens":int}, 
  "tools":[string], 
  "constraints":{"max_steps":int} 
 } 
 约束： 
 字段不可缺失；未知字段拒绝写入；默认temperature=0.7 
