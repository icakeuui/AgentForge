版本：v1.0 冻结版 
 表： 
 agents(id,config,jsonb) 
 executions(id,agent_id,status,token_usage,jsonb) 
 execution_steps(id,execution_id,step,jsonb) 
 索引： 
 execution_id索引；agent_id索引 
