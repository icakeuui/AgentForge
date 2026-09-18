版本：v1.0 冻结版 
 状态：created→running→(success|failed|timeout|cancelled) 
 step状态：pending→running→(success|failed) 
 规则： 
 1. created后必须进入running 
 2. 任一步失败则execution标记failed 
 3. 超时统一标记timeout 
 4. success仅在final_answer产生时成立 
