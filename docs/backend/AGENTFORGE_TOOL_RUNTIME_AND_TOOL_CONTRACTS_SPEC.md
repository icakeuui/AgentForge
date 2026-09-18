版本：v1.0 冻结版 
 Tool定义： 
 {name,description,input_schema,output_schema} 
 执行接口： 
 execute(name,input)->output 
 约束： 
 1. 输入输出必须JSON 
 2. 不允许副作用（默认） 
 3. 执行必须可记录日志 
