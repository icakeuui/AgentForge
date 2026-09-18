版本：v1.0 冻结版 
 一、执行模型 
 ReAct循环：thought→action→action_input→execute→observation 
 二、接口 
 run(agent_id,input)->execution_id 
 step(context)->ReactStep 
 三、循环控制 
 max_steps=5（默认）；timeout单步<=10s；总执行<=60s 
 四、终止条件 
 action=final_answer 或 达到max_steps 或 error 
 五、错误处理 
 工具或Python失败返回observation.error，不抛异常至LLM外层 
