import json,time,uuid,os,logging
from typing import Any,Dict,Literal,Optional
from fastapi import FastAPI,Depends,HTTPException,File,UploadFile,Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from .database import init_db,SessionLocal,TraceDB,TraceStepDB,BranchDB,engine
from .replay_engine import ReplayEngine
from .agent_tools import SUPPORTED_TOOLS,TOOL_SCHEMAS,execute_builtin_tool
logger=logging.getLogger(__name__)
app=FastAPI(title='Time-Travel AI Debugger API',version='2.0.0')
app.add_middleware(CORSMiddleware,allow_origins=[os.getenv('FRONTEND_ORIGIN','https://ai-time-travel-debugger.onrender.com')],allow_credentials=True,allow_methods=['GET','POST','OPTIONS'],allow_headers=['*'])
_agent_run_requests={}
init_db()
def get_db():
 db=SessionLocal()
 try: yield db
 finally: db.close()
class BranchRequest(BaseModel):
 parent_trace_id:str; fork_step_id:str; modified_prompt:Optional[str]=None; modified_inputs:Optional[Dict[str,Any]]=None; live_llm:bool=False
class ToolReplayRequest(BaseModel): trace_id:str; replay_from_step_id:str; tool_name:str; arguments:Dict[str,Any]=Field(default_factory=dict)
class AgentMessage(BaseModel): role:Literal['user','assistant']; content:str=Field(min_length=1,max_length=12000)
class AgentRunRequest(BaseModel):
 agent_name:str=Field(min_length=1,max_length=80); instructions:str=Field(min_length=1,max_length=6000); model:str=Field(default='gpt-4o',min_length=1,max_length=100); tools:list[str]=Field(default_factory=list,max_length=2); messages:list[AgentMessage]=Field(min_length=1,max_length=20)

def serialize(s): return {'step_id':s.step_id,'parent_step_id':s.parent_step_id,'step_number':s.step_number,'step_type':s.step_type,'status':s.status,'input':json.loads(s.input_json or '{}'),'output':json.loads(s.output_json or '{}'),'state_snapshot_before':json.loads(s.state_snapshot or '{}'),'metrics':{'latency_ms':s.latency_ms,'prompt_tokens':s.prompt_tokens,'completion_tokens':s.completion_tokens}}
@app.get('/health')
def health(): return {'status':'ok','service':'Replay Engine','version':'2.0.0'}

@app.post('/api/v1/agents/run')
def run_agent(req:AgentRunRequest,request:Request,db:Session=Depends(get_db)):
 now=time.monotonic(); forwarded=request.headers.get('x-forwarded-for'); client_ip=forwarded.split(',')[0].strip() if forwarded else (request.client.host if request.client else 'unknown')
 recent=[stamp for stamp in _agent_run_requests.get(client_ip,[]) if now-stamp<60]
 if len(recent)>=12: raise HTTPException(429,'Too many agent runs. Wait a minute and try again.')
 recent.append(now); _agent_run_requests[client_ip]=recent
 if len(_agent_run_requests)>5000:
  for ip in list(_agent_run_requests):
   if not any(now-stamp<60 for stamp in _agent_run_requests[ip]): _agent_run_requests.pop(ip,None)
 if not os.getenv('OPENAI_API_KEY'): raise HTTPException(503,'Agent runs are unavailable: configure OPENAI_API_KEY on the backend.')
 if not req.messages or req.messages[-1].role!='user': raise HTTPException(422,'The last message must be from the user.')
 if sum(len(message.content) for message in req.messages)>60000: raise HTTPException(413,'This conversation is too long. Start a new chat or shorten earlier messages.')
 if len(set(req.tools))!=len(req.tools) or any(name not in SUPPORTED_TOOLS for name in req.tools): raise HTTPException(422,'Choose only the supported tools: calculator and current_time.')
 try:
  from openai import OpenAI
  client=OpenAI()
  messages=[{'role':'system','content':req.instructions}]+[item.model_dump() for item in req.messages]
  tool_specs=[TOOL_SCHEMAS[name] for name in req.tools]
  trace_id=f'trc_agent_{uuid.uuid4().hex[:12]}'; trace_steps=[]; parent_step_id=None; usage={'prompt_tokens':0,'completion_tokens':0}; reply=''
  def record(step_type,input_data,output_data,status='completed',metrics=None):
   nonlocal parent_step_id
   number=len(trace_steps)+1; step_id=f'{trace_id}_step_{number:02d}'
   trace_steps.append({'step_id':step_id,'parent_step_id':parent_step_id,'step_number':number,'step_type':step_type,'status':status,'input':input_data,'output':output_data,'metrics':metrics or {}})
   parent_step_id=step_id
  for turn in range(4):
   request_messages=json.loads(json.dumps(messages))
   started=time.monotonic()
   response=client.chat.completions.create(model=req.model,messages=messages,tools=tool_specs or None,max_tokens=800)
   elapsed=int((time.monotonic()-started)*1000); choice=response.choices[0]; model_message=choice.message
   tool_calls=[]
   for call in model_message.tool_calls or []:
    tool_calls.append({'call_id':call.id,'function_name':call.function.name,'arguments':call.function.arguments})
   output={'content':model_message.content,'tool_calls':tool_calls,'finish_reason':choice.finish_reason}
   usage_data={'prompt_tokens':getattr(response.usage,'prompt_tokens',0) or 0,'completion_tokens':getattr(response.usage,'completion_tokens',0) or 0}
   usage['prompt_tokens']+=usage_data['prompt_tokens']; usage['completion_tokens']+=usage_data['completion_tokens']
   record('llm_call',{'model':req.model,'messages':request_messages,'tools':tool_specs},output,metrics={'latency_ms':elapsed,**usage_data})
   if not model_message.tool_calls:
    reply=model_message.content or ''; break
   assistant_call={'role':'assistant','content':model_message.content,'tool_calls':[{'id':call.id,'type':'function','function':{'name':call.function.name,'arguments':call.function.arguments}} for call in model_message.tool_calls]}
   messages.append(assistant_call)
   if turn==3:
    reply='I reached the tool-call limit for this run. Please try a smaller request.'
    break
   for call_index,call in enumerate(model_message.tool_calls):
    arguments={}
    try:
     arguments=json.loads(call.function.arguments or '{}')
     if call_index>=2: raise ValueError('Maximum of two tool calls per turn reached')
     if call.function.name not in req.tools: raise ValueError('Tool is not enabled for this agent')
     result=execute_builtin_tool(call.function.name,arguments); tool_output={'result':result}; status='completed'
    except Exception as exc:
     tool_output={'error':str(exc)}; status='failed'
    record('tool_execution',{'tool_name':call.function.name,'arguments':arguments},tool_output,status)
    messages.append({'role':'tool','tool_call_id':call.id,'content':json.dumps(tool_output,default=str)})
  now=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
  trace=TraceDB(trace_id=trace_id,agent_name=f'{req.agent_name} Agent',created_at=now,total_steps=len(trace_steps)); db.add(trace)
  for step in trace_steps:
   db.add(TraceStepDB(trace_id=trace_id,step_id=step['step_id'],parent_step_id=step['parent_step_id'],step_number=step['step_number'],step_type=step['step_type'],status=step['status'],input_json=json.dumps(step['input'],default=str),output_json=json.dumps(step['output'],default=str),state_snapshot='{}',latency_ms=step['metrics'].get('latency_ms',0),prompt_tokens=step['metrics'].get('prompt_tokens',0),completion_tokens=step['metrics'].get('completion_tokens',0)))
  db.commit()
  return {'reply':reply,'trace_id':trace_id,'usage':usage,'steps':len(trace_steps)}
 except HTTPException: raise
 except Exception as exc:
  db.rollback()
  status_code=getattr(exc,'status_code',None)
  error_type=type(exc).__name__
  logger.warning('Agent provider request failed: type=%s status=%s',error_type,status_code if isinstance(status_code,int) else 'unknown')
  if status_code==401:
   detail='OpenAI rejected OPENAI_API_KEY. Replace it with a valid OpenAI API key.'
  elif status_code==403:
   detail='The OpenAI key does not have permission to use this model. Check the key project and model access.'
  elif status_code==404:
   detail='The selected OpenAI model was not found or is unavailable to this key. Choose an enabled model.'
  elif status_code==429:
   detail='The OpenAI account is rate limited or out of quota. Check its usage limits and billing.'
  elif error_type=='APIConnectionError':
   detail='The backend could not connect to OpenAI. Check the Render service network and retry.'
  else:
   detail='Agent provider request failed. Check Render logs for the safe error type and HTTP status.'
  raise HTTPException(502,detail) from None

@app.get('/health/db')
def health_db(db:Session=Depends(get_db)):
 db.execute(__import__('sqlalchemy').text('SELECT 1'))
 return {'status':'ok','database':engine.url.get_backend_name(),'database_connected':True}
@app.post('/api/v1/traces/upload')
async def upload_trace(file:UploadFile=File(...),db:Session=Depends(get_db)):
 try:
  data=json.loads(await file.read()); tid=data['trace_id']; steps=data.get('steps',[])
  old=db.query(TraceDB).filter_by(trace_id=tid).first()
  if old: db.delete(old); db.commit()
  t=TraceDB(trace_id=tid,agent_name=data.get('agent_name','UnknownAgent'),created_at=data.get('created_at',''),total_steps=len(steps)); db.add(t)
  for s in steps:
   db.add(TraceStepDB(trace_id=tid,step_id=s['step_id'],parent_step_id=s.get('parent_step_id'),step_number=s['step_number'],step_type=s['step_type'],status=s.get('status','completed'),input_json=json.dumps(s.get('input',{}),default=str),output_json=json.dumps(s.get('output',{}),default=str),state_snapshot=json.dumps(s.get('state_snapshot_before',{}),default=str),latency_ms=s.get('metrics',{}).get('latency_ms',0),prompt_tokens=s.get('metrics',{}).get('prompt_tokens',0),completion_tokens=s.get('metrics',{}).get('completion_tokens',0)))
  db.commit(); return {'status':'success','trace_id':tid,'imported_steps':len(steps)}
 except Exception as e: db.rollback(); raise HTTPException(400,f'Failed to parse trace: {e}')
@app.get('/api/v1/traces')
def list_traces(db:Session=Depends(get_db)):
 return [{'trace_id':t.trace_id,'agent_name':t.agent_name,'created_at':t.created_at,'total_steps':t.total_steps} for t in db.query(TraceDB).order_by(TraceDB.created_at.desc()).all()]
@app.get('/api/v1/traces/{trace_id}')
def get_trace(trace_id:str,db:Session=Depends(get_db)):
 t=db.query(TraceDB).filter_by(trace_id=trace_id).first()
 if not t: raise HTTPException(404,'Trace not found')
 return {'trace_id':t.trace_id,'agent_name':t.agent_name,'created_at':t.created_at,'steps':[serialize(s) for s in db.query(TraceStepDB).filter_by(trace_id=trace_id).order_by(TraceStepDB.step_number).all()]}
@app.get('/api/v1/traces/{trace_id}/step/{step_id}')
def get_step(trace_id:str,step_id:str,db:Session=Depends(get_db)):
 s=db.query(TraceStepDB).filter_by(trace_id=trace_id,step_id=step_id).first()
 if not s: raise HTTPException(404,'Step not found')
 return serialize(s)
@app.post('/api/v1/replay/tool')
def replay_tool(req:ToolReplayRequest,db:Session=Depends(get_db)):
 cursor=db.query(TraceStepDB).filter_by(trace_id=req.trace_id,step_id=req.replay_from_step_id).first()
 if not cursor: raise HTTPException(404,'Replay cursor step not found in trace')
 rows=db.query(TraceStepDB).filter(TraceStepDB.trace_id==req.trace_id,TraceStepDB.step_type=='tool_execution',TraceStepDB.step_number<cursor.step_number).order_by(TraceStepDB.step_number.desc()).all()
 historical=[serialize(x) for x in rows]; result,hit=ReplayEngine().cached_tool_result(historical,req.tool_name,req.arguments)
 if not hit: return {'mode':'cache_miss','replay_from_step_id':cursor.step_id,'tool_name':req.tool_name,'arguments':req.arguments,'message':'No successful exact match exists before the replay cursor; execution was not performed.'}
 return {'mode':'cached','replay_from_step_id':cursor.step_id,'tool_name':req.tool_name,'arguments':req.arguments,'result':result}
@app.post('/api/v1/replay/branch')
def branch(req:BranchRequest,db:Session=Depends(get_db)):
 parent=db.query(TraceDB).filter_by(trace_id=req.parent_trace_id).first()
 fork=db.query(TraceStepDB).filter_by(trace_id=req.parent_trace_id,step_id=req.fork_step_id).first()
 if not parent: raise HTTPException(404,'Parent trace not found')
 if not fork: raise HTTPException(404,'Fork step not found')
 new_id=f'trc_branch_{uuid.uuid4().hex[:10]}'; now=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
 db.add(BranchDB(parent_trace_id=req.parent_trace_id,fork_step_id=req.fork_step_id,new_trace_id=new_id,created_at=now)); nt=TraceDB(trace_id=new_id,agent_name=parent.agent_name+' (Branch)',created_at=now,total_steps=0); db.add(nt)
 source=db.query(TraceStepDB).filter(TraceStepDB.trace_id==req.parent_trace_id,TraceStepDB.step_number<=fork.step_number).order_by(TraceStepDB.step_number).all()
 for s in source:
  inp=json.loads(s.input_json); status=s.status
  if s.step_id==req.fork_step_id:
   if req.modified_inputs: inp.update(req.modified_inputs)
   if req.modified_prompt:
    if inp.get('messages'): inp['messages'][0]['content']=req.modified_prompt
    else: inp['system_prompt']=req.modified_prompt
   status='branched'
  db.add(TraceStepDB(trace_id=new_id,step_id=s.step_id,parent_step_id=s.parent_step_id,step_number=s.step_number,step_type=s.step_type,status=status,input_json=json.dumps(inp),output_json=s.output_json,state_snapshot=s.state_snapshot,latency_ms=s.latency_ms,prompt_tokens=s.prompt_tokens,completion_tokens=s.completion_tokens))
 replay=None; mode='deterministic_cached_replay'
 if req.live_llm and fork.step_type=='llm_call':
  inp=json.loads(fork.input_json); msgs=inp.get('messages',[])
  if req.modified_prompt:
   if msgs: msgs[0]['content']=req.modified_prompt
   else: msgs=[{'role':'system','content':req.modified_prompt}]
  replay=ReplayEngine().live_llm(inp.get('model','gpt-4o'),msgs,inp.get('temperature',0.2),inp.get('tools'))
  if replay and 'error' not in replay:
   mode='live_llm_replay'; db.add(TraceStepDB(trace_id=new_id,step_id=f'{req.fork_step_id}_replay',parent_step_id=req.fork_step_id,step_number=fork.step_number+1,step_type='llm_call',status='replayed_live',input_json=json.dumps(inp),output_json=json.dumps(replay),state_snapshot=fork.state_snapshot,latency_ms=0,prompt_tokens=replay.get('usage',{}).get('prompt_tokens',0),completion_tokens=replay.get('usage',{}).get('completion_tokens',0))); nt.total_steps=len(source)+1
  else: nt.total_steps=len(source)
 else: nt.total_steps=len(source)
 db.commit(); return {'status':'success','new_trace_id':new_id,'forked_at_step':req.fork_step_id,'mode':mode,'live_replay':replay}
