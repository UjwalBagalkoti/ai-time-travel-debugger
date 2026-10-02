import json,time,uuid,os
from typing import Any,Dict,Optional
from fastapi import FastAPI,Depends,HTTPException,File,UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from .database import init_db,SessionLocal,TraceDB,TraceStepDB,BranchDB,engine
from .replay_engine import ReplayEngine
app=FastAPI(title='Time-Travel AI Debugger API',version='2.0.0')
app.add_middleware(CORSMiddleware,allow_origins=[os.getenv('FRONTEND_ORIGIN','https://ai-time-travel-debugger.onrender.com')],allow_credentials=True,allow_methods=['GET','POST','OPTIONS'],allow_headers=['*'])
init_db()
def get_db():
 db=SessionLocal()
 try: yield db
 finally: db.close()
class BranchRequest(BaseModel):
 parent_trace_id:str; fork_step_id:str; modified_prompt:Optional[str]=None; modified_inputs:Optional[Dict[str,Any]]=None; live_llm:bool=False
class ToolReplayRequest(BaseModel): trace_id:str; tool_name:str; arguments:Dict[str,Any]=Field(default_factory=dict)

def serialize(s): return {'step_id':s.step_id,'parent_step_id':s.parent_step_id,'step_number':s.step_number,'step_type':s.step_type,'status':s.status,'input':json.loads(s.input_json or '{}'),'output':json.loads(s.output_json or '{}'),'state_snapshot_before':json.loads(s.state_snapshot or '{}'),'metrics':{'latency_ms':s.latency_ms,'prompt_tokens':s.prompt_tokens,'completion_tokens':s.completion_tokens}}
@app.get('/health')
def health(): return {'status':'ok','service':'Replay Engine','version':'2.0.0'}

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
 rows=db.query(TraceStepDB).filter_by(trace_id=req.trace_id,step_type='tool_execution').all()
 historical=[serialize(x) for x in rows]; result,hit=ReplayEngine().cached_tool_result(historical,req.tool_name,req.arguments)
 if not hit: return {'mode':'cache_miss','tool_name':req.tool_name,'arguments':req.arguments,'message':'No exact historical match; execution blocked by safe replay boundary.'}
 return {'mode':'cached','tool_name':req.tool_name,'arguments':req.arguments,'result':result}
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