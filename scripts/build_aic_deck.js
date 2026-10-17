const pptxgen = require('pptxgenjs');
const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'AgentForge';
pptx.subject = '2026 AIC 算法创新赛 AI+学科交叉赛道';
pptx.title = 'AgentForge 智能体搭建辅助实践平台';
pptx.company = 'AgentForge';
pptx.lang = 'zh-CN';
pptx.theme = { headFontFace: 'Microsoft YaHei', bodyFontFace: 'Microsoft YaHei', lang: 'zh-CN' };

const W = 13.333, H = 7.5;
const C = { navy:'10224A', blue:'2864F0', cyan:'23B7D8', violet:'6E5AE6', ink:'12213D', gray:'5F6B85', light:'F4F7FC', line:'DCE4F2', white:'FFFFFF', green:'39A974', orange:'F39B44' };
const asset = 'C:/Users/韩颖/.codex/generated_images/01a0b81a-53ff-7ff3-9c51-1c5e0a64ad59/exec-280b6aba-40b2-4515-b2e5-878cc3465c1c.png';

function bg(slide, dark=false){ slide.background={color:dark?C.navy:C.white}; if(!dark){slide.addShape(pptx.ShapeType.rect,{x:0,y:0,w:W,h:0.08,fill:{color:C.blue},line:{color:C.blue}});} }
function title(slide, t, sub=''){ slide.addText(t,{x:0.65,y:0.38,w:8.8,h:0.42,fontFace:'Microsoft YaHei',fontSize:24,bold:true,color:C.ink,margin:0}); if(sub) slide.addText(sub,{x:0.68,y:0.87,w:11.5,h:0.24,fontSize:9.5,color:C.gray,margin:0}); }
function footer(slide,n){ slide.addText(`AGENTFORGE  |  AI+学科交叉  ·  ${String(n).padStart(2,'0')}`,{x:0.68,y:7.12,w:5.4,h:0.16,fontSize:7.5,color:C.gray,margin:0}); slide.addText('2026 全球校园人工智能算法精英大赛',{x:8.7,y:7.12,w:3.95,h:0.16,fontSize:7.5,color:C.gray,align:'right',margin:0}); }
function pill(slide, text, x,y,w, color=C.blue){ slide.addShape(pptx.ShapeType.roundRect,{x,y,w,h:0.32,rectRadius:0.06,fill:{color},line:{color}}); slide.addText(text,{x,y:0.03+y,w,h:0.18,fontSize:9,color:C.white,bold:true,align:'center',margin:0}); }
function card(slide,x,y,w,h,head,body,accent=C.blue){ slide.addShape(pptx.ShapeType.roundRect,{x,y,w,h,rectRadius:0.06,fill:{color:C.white},line:{color:C.line,width:1}}); slide.addShape(pptx.ShapeType.rect,{x,y,w:0.08,h,fill:{color:accent},line:{color:accent}}); slide.addText(head,{x:x+0.22,y:y+0.17,w:w-0.35,h:0.25,fontSize:14,bold:true,color:C.ink,margin:0}); slide.addText(body,{x:x+0.22,y:y+0.54,w:w-0.4,h:h-0.68,fontSize:10.5,color:C.gray,breakLine:false,fit:'shrink',margin:0.02, valign:'top'}); }
function node(slide,x,y,w,h,text,color=C.blue){ slide.addShape(pptx.ShapeType.roundRect,{x,y,w,h,rectRadius:0.05,fill:{color},line:{color}}); slide.addText(text,{x,y:y+0.08,w,h:h-0.12,fontSize:11,bold:true,color:C.white,align:'center',valign:'mid',margin:0.02,fit:'shrink'}); }
function arrow(slide,x1,y1,x2,y2,color=C.line){ slide.addShape(pptx.ShapeType.line,{x:x1,y:y1,w:x2-x1,h:y2-y1,line:{color,width:2,beginArrowType:'none',endArrowType:'triangle'}}); }

// 1 Cover
{ const s=pptx.addSlide(); bg(s,true); s.addImage({path:asset,x:7.15,y:0.2,w:6.18,h:6.95,transparency:5}); s.addShape(pptx.ShapeType.rect,{x:0,y:0,w:7.9,h:H,fill:{color:C.navy,transparency:1},line:{color:C.navy,transparency:100}}); s.addText('AgentForge',{x:0.8,y:1.25,w:5.8,h:0.65,fontSize:35,bold:true,color:C.white,margin:0}); s.addText('智能体搭建辅助实践平台',{x:0.83,y:2.05,w:5.8,h:0.45,fontSize:22,color:'D9E7FF',margin:0}); s.addText('人工智能赋能高校学科实践',{x:0.83,y:3.18,w:5.4,h:0.62,fontSize:25,bold:true,color:'65D4F1',margin:0}); s.addText('2026 全球校园人工智能算法精英大赛  ·  算法创新赛  ·  AI+学科交叉赛道',{x:0.84,y:5.72,w:6.3,h:0.28,fontSize:10.5,color:'C8D5F0',margin:0}); s.addText('参赛答辩材料',{x:0.84,y:6.2,w:2.4,h:0.25,fontSize:11,color:'C8D5F0',margin:0}); }

// 2 Background
{ const s=pptx.addSlide(); bg(s); title(s,'高校 AI 应用正在进入“学科实践”阶段','大模型降低了交互门槛，但真实教学与科研仍需要可配置、可执行、可复盘的实践载体'); card(s,0.72,1.5,3.7,3.7,'知识进入课堂','课程资料、实验手册、校规制度与科研文献需要被准确检索并给出依据。',C.blue); card(s,4.82,1.5,3.7,3.7,'任务走向执行','从问答延伸到资料整理、实验辅助、工具调用与结果生成。',C.violet); card(s,8.92,1.5,3.7,3.7,'过程需要被看见','教学与竞赛需要记录检索、调用、权限、成本与最终结果，支持复盘。',C.cyan); s.addText('需求变化：从“会回答”走向“能实践、可解释、可治理”',{x:1.0,y:5.82,w:11.2,h:0.45,fontSize:19,bold:true,color:C.ink,align:'center',margin:0}); footer(s,2); }

// 3 track positioning
{ const s=pptx.addSlide(); bg(s); title(s,'AI+学科交叉：让人工智能成为专业实践的新工具','赛道对应关系：AI 技术嵌入高校教学、科研探索、实验实训和自主学习'); s.addImage({path:asset,x:7.25,y:1.25,w:5.35,h:3.0,crop:{x:0.29,y:0,w:0.71,h:1}}); node(s,0.9,1.55,2.3,0.62,'学科问题',C.violet); node(s,3.5,1.55,2.3,0.62,'智能体能力',C.blue); node(s,0.9,2.75,2.3,0.62,'真实资料',C.cyan); node(s,3.5,2.75,2.3,0.62,'实践结果',C.green); arrow(s,3.2,1.86,3.48,1.86); arrow(s,4.65,2.2,4.65,2.7); arrow(s,3.2,3.06,3.48,3.06); arrow(s,2.05,2.2,2.05,2.7); s.addText('四类入口',{x:7.55,y:4.62,w:1.8,h:0.25,fontSize:12,bold:true,color:C.ink,margin:0}); s.addText('课程助教  ·  科研资料助手  ·  实验实训助手  ·  竞赛实践助手',{x:7.55,y:5.0,w:4.7,h:0.55,fontSize:14,color:C.gray,breakLine:false,fit:'shrink',margin:0}); footer(s,3); }

// 4 pain points
{ const s=pptx.addSlide(); bg(s); title(s,'高校学科实践的四个断点','用户需要的不是更多聊天窗口，而是一条从资料到任务、从试验到复盘的完整链路'); const items=[['搭建门槛高','模型、Prompt、知识库和工具分散在不同技术栈'],['回答缺依据','专业资料没有进入检索链路，结果难以追溯'],['执行不可控','工具权限、代码执行与高风险操作缺少边界'],['成果难复用','本地原型难以发布、展示与形成教学案例']]; items.forEach((it,i)=>{const x=0.9+(i%2)*6.1,y=1.55+Math.floor(i/2)*2.2; card(s,x,y,5.45,1.55,it[0],it[1],[C.blue,C.violet,C.cyan,C.orange][i]);}); s.addText('核心矛盾：学生想快速实践，教师要过程可教，学校要资源可管',{x:1.05,y:6.15,w:11.2,h:0.34,fontSize:17,bold:true,color:C.ink,align:'center',margin:0}); footer(s,4); }

// 5 solution
{ const s=pptx.addSlide(); bg(s); title(s,'AgentForge：把学科问题装配成可运行的智能体实践','用户以学科任务为起点，配置模型、知识与工具，完成测试、调试、发布和复盘'); const labels=[['提出任务','课程 / 科研 / 实验 / 竞赛'],['配置知识','PDF / DOCX / TXT + 混合检索'],['绑定工具','API 工具 / 插件 / Python 沙箱'],['运行复盘','执行轨迹 / 权限 / Token / 日志'],['分享复用','公开体验页 / 模板 / 课程案例']]; labels.forEach((a,i)=>{const x=0.65+i*2.55; node(s,x,2.05,2.0,0.72,a[0], [C.violet,C.blue,C.cyan,C.green,C.orange][i]); s.addText(a[1],{x:x-0.12,y:3.05,w:2.25,h:0.42,fontSize:9.5,color:C.gray,align:'center',fit:'shrink',margin:0}); if(i<4) arrow(s,x+2.04,2.41,x+2.45,2.41,C.line);}); s.addText('一条面向高校实践的智能体闭环',{x:1.7,y:4.65,w:9.9,h:0.5,fontSize:26,bold:true,color:C.ink,align:'center',margin:0}); s.addText('低门槛构建  ·  有依据回答  ·  受控执行  ·  可审计复盘',{x:2.0,y:5.42,w:9.3,h:0.3,fontSize:14,color:C.blue,align:'center',margin:0}); footer(s,5); }

// 6 architecture
{ const s=pptx.addSlide(); bg(s); title(s,'系统技术架构：从配置到执行的可观测链路','前后端分离、分层解耦，围绕“知识、工具、模型、治理”形成统一运行时'); const cols=[['交互层','React + TypeScript\n构建器 / 广场 / 公开页'],['服务层','FastAPI + JWT\n权限 / 团队 / 资源隔离'],['运行层','Agent Service + LangGraph\n单智能体状态与执行'],['能力层','RAG + Model Gateway\n工具 Runtime + Python 沙箱'],['治理层','策略检查 / 配额 / 审计\nToken、频率、高风险确认']]; cols.forEach((a,i)=>{const x=0.55+i*2.56; card(s,x,1.65,2.22,3.5,a[0],a[1],[C.violet,C.blue,C.cyan,C.green,C.orange][i]);}); s.addText('数据闭环：配置 → 检索 → 决策 → 工具调用 → 结果校验 → 日志沉淀',{x:0.9,y:5.78,w:11.5,h:0.4,fontSize:17,bold:true,color:C.ink,align:'center',margin:0}); footer(s,6); }

// 7 core features
{ const s=pptx.addSlide(); bg(s); title(s,'核心功能：让智能体成为可教学、可实验的对象','功能围绕高校使用者的真实任务组织，而不是围绕模型参数堆叠'); const fs=[['可视化构建','配置身份、提示词、模型、知识和工具'],['RAG 知识库','文档解析、切片、向量检索与关键词检索'],['工具调用','内置工具、API 工具、插件与参数校验'],['运行日志','查看检索、调用、失败与最终回答'],['策略治理','权限隔离、风险确认、Token 配额与限流'],['发布复用','公开链接、智能体广场、模板化案例']]; fs.forEach((a,i)=>{const x=0.75+(i%3)*4.15,y=1.45+Math.floor(i/3)*2.35; card(s,x,y,3.55,1.7,a[0],a[1],[C.blue,C.violet,C.cyan,C.green,C.orange,C.blue][i]);}); footer(s,7); }

// 8 scenarios
{ const s=pptx.addSlide(); bg(s); title(s,'AI 赋能学科应用：从“用 AI”到“做实践”','同一套能力适配不同专业任务，输出可验证、可复用的实践成果'); const rows=[['工科实验','读取实验手册，调用计算工具，生成实验记录与误差分析','过程记录 + 可复现实验'],['医学 / 生命','基于课程资料检索知识，辅助病例学习与文献整理','来源可追溯 + 风险提示'],['农业与环境','接入种植、气象或监测数据，辅助分析与方案比较','数据驱动 + 场景适配'],['人文社科','围绕课程文献进行问答、摘要、观点对照与证据标注','资料依据 + 学术表达']]; rows.forEach((r,i)=>{const y=1.35+i*1.23; s.addShape(pptx.ShapeType.line,{x:0.8,y:y+0.93,w:11.75,h:0,line:{color:C.line,width:1}}); s.addText(r[0],{x:0.85,y:y+0.14,w:1.35,h:0.25,fontSize:13,bold:true,color:[C.blue,C.green,C.orange,C.violet][i],margin:0}); s.addText(r[1],{x:2.45,y:y+0.08,w:6.65,h:0.48,fontSize:11,color:C.ink,fit:'shrink',margin:0}); s.addText(r[2],{x:9.65,y:y+0.17,w:2.5,h:0.25,fontSize:10,bold:true,color:C.gray,align:'right',margin:0});}); footer(s,8); }

// 9 innovations
{ const s=pptx.addSlide(); bg(s); title(s,'项目创新点：把“可用”推进到“可验证”','技术创新服务于学科实践中的可信性、可控性与可复盘性'); const ins=[['交叉定位创新','以高校学科任务为入口，把智能体能力嵌入教学、科研与实验过程'],['混合检索创新','向量检索与关键词检索结合，提升专业资料查找的可解释性'],['执行治理创新','执行前、中、后加入策略检查，约束工具权限和高风险操作'],['教学复盘创新','记录检索、工具、失败和成本，让智能体运行过程成为教学素材']]; ins.forEach((a,i)=>{const y=1.35+i*1.26; s.addText(`0${i+1}`,{x:0.95,y:y+0.05,w:0.5,h:0.45,fontSize:25,bold:true,color:[C.blue,C.violet,C.cyan,C.orange][i],margin:0}); s.addText(a[0],{x:1.75,y:y+0.08,w:2.0,h:0.25,fontSize:14,bold:true,color:C.ink,margin:0}); s.addText(a[1],{x:4.0,y:y+0.08,w:8.1,h:0.38,fontSize:12,color:C.gray,fit:'shrink',margin:0}); s.addShape(pptx.ShapeType.line,{x:1.75,y:y+0.75,w:10.35,h:0,line:{color:C.line,width:1}});}); footer(s,9); }

// 10成果展示
{ const s=pptx.addSlide(); bg(s); title(s,'开发成果与系统展示','项目已形成可运行的软件原型，具备从创建到发布的完整演示链路'); s.addImage({path:asset,x:0.82,y:1.35,w:4.3,h:4.45,crop:{x:0.31,y:0,w:0.69,h:1}}); const metrics=[['前端','React + TypeScript'],['后端','FastAPI + SQLAlchemy'],['执行','LangGraph 单智能体'],['部署','前后端分离，可本地运行']]; metrics.forEach((m,i)=>{const x=5.65+(i%2)*3.35,y=1.55+Math.floor(i/2)*1.45; card(s,x,y,2.85,1.05,m[0],m[1],[C.blue,C.violet,C.cyan,C.green][i]);}); s.addText('建议现场演示：创建一个“课程资料助教”智能体，上传资料，检索问答，查看工具与日志，再发布公开体验页。',{x:5.7,y:4.75,w:6.35,h:0.85,fontSize:14,bold:true,color:C.ink,fit:'shrink',margin:0}); footer(s,10); }

// 11 value
{ const s=pptx.addSlide(); bg(s); title(s,'应用价值与推广前景','平台的推广单位不是“一个产品”，而是一套可复制的学科实践方法'); const vals=[['对学生','降低智能体实践门槛，把课程知识转化为可运行作品'],['对教师','用执行记录组织实验、讲解 RAG、工具调用与安全治理'],['对学校','统一资源、权限和配额，沉淀跨专业教学案例'],['对科研团队','快速验证知识助手与轻量业务智能体，再进入定制部署']]; vals.forEach((a,i)=>{const x=0.75+(i%2)*6.05,y=1.5+Math.floor(i/2)*2.2; card(s,x,y,5.45,1.65,a[0],a[1],[C.blue,C.violet,C.cyan,C.green][i]);}); s.addText('推广路径：课程实验 → 创新实验室 → 学科竞赛 → 科研团队与校企实践',{x:1.0,y:6.0,w:11.2,h:0.38,fontSize:17,bold:true,color:C.ink,align:'center',margin:0}); footer(s,11); }

// 12 summary
{ const s=pptx.addSlide(); bg(s,true); s.addText('AgentForge',{x:0.8,y:0.9,w:4.8,h:0.55,fontSize:30,bold:true,color:C.white,margin:0}); s.addText('让人工智能成为高校专业实践的新工具',{x:0.82,y:1.75,w:8.8,h:0.55,fontSize:25,bold:true,color:'65D4F1',margin:0}); s.addText('面向学科任务  |  连接真实知识  |  支持工具执行  |  保留实践证据',{x:0.84,y:2.55,w:8.9,h:0.3,fontSize:14,color:'D9E7FF',margin:0}); node(s,0.9,4.25,2.25,0.65,'今天：可运行原型',C.blue); node(s,3.55,4.25,2.25,0.65,'近期：课程案例库',C.violet); node(s,6.2,4.25,2.25,0.65,'后续：校级推广',C.cyan); node(s,8.85,4.25,2.25,0.65,'长期：学科生态',C.green); arrow(s,3.2,4.58,3.5,4.58,'A5B9E7'); arrow(s,5.85,4.58,6.15,4.58,'A5B9E7'); arrow(s,8.5,4.58,8.8,4.58,'A5B9E7'); s.addText('谢谢各位评委',{x:0.84,y:6.3,w:3.2,h:0.34,fontSize:17,color:C.white,margin:0}); }

pptx.writeFile({ fileName: 'C:/Users/韩颖/PycharmProjects/AgentForge-main/AgentForge_AI学科交叉答辩PPT.pptx' });
