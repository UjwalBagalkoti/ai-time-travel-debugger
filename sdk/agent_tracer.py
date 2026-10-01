import json, uuid, time
from typing import Any, List
from functools import wraps

class AgentTracer:
    def __init__(self, agent_name: str, output_path: str = 'agent_execution.trace'):
        self.agent_name = agent_name
        self.output_path = output_path
        self.trace_id = f'trc_{uuid.uuid4().hex[:12]}'
        self.steps: List[dict] = []
        self.step_counter = 0

    def _safe(self, value):
        try:
            json.dumps(value)
            return value
        except TypeError:
            return str(value)

    def _record(self, payload):
        self.steps.append(payload)
        self._flush()

    def _flush(self):
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump({'version':'1.0.0','trace_id':self.trace_id,'agent_name':self.agent_name,
                       'created_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                       'steps':self.steps}, f, indent=2, default=str)

    def trace_step(self, step_type='custom', state_snapshot_fn=None):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                self.step_counter += 1
                sid = f'step_{self.step_counter:03d}'
                parent = f'step_{self.step_counter-1:03d}' if self.step_counter > 1 else None
                start = time.time(); error = None; result = None
                snapshot = state_snapshot_fn() if callable(state_snapshot_fn) else {}
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as exc:
                    error = str(exc)
                    raise
                finally:
                    self._record({'step_id':sid,'parent_step_id':parent,'step_number':self.step_counter,
                        'step_type':step_type,'status':'failed' if error else 'completed',
                        'timestamp_start':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(start)),
                        'timestamp_end':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                        'state_snapshot_before':self._safe(snapshot),
                        'input':{'args':[self._safe(a) for a in args],'kwargs':self._safe(kwargs)},
                        'output':result if not error else {'error':error},
                        'metrics':{'latency_ms':int((time.time()-start)*1000)}})
            return wrapper
        return decorator

    def wrap_tool(self, tool_name, fn=None):
        def decorator(func):
            @wraps(func)
            def wrapped(*args, **kwargs):
                self.step_counter += 1
                sid=f'step_{self.step_counter:03d}'; parent=f'step_{self.step_counter-1:03d}' if self.step_counter > 1 else None
                start=time.time(); error=None; result=None
                try:
                    result=func(*args, **kwargs)
                    return result
                except Exception as exc:
                    error=str(exc); raise
                finally:
                    arguments=dict(kwargs)
                    if args: arguments['_args']=[self._safe(a) for a in args]
                    self._record({'step_id':sid,'parent_step_id':parent,'step_number':self.step_counter,
                        'step_type':'tool_execution','status':'failed' if error else 'completed',
                        'timestamp_start':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(start)),
                        'timestamp_end':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                        'input':{'tool_name':tool_name,'arguments':self._safe(arguments)},
                        'output':result if not error else {'error':error},
                        'metrics':{'latency_ms':int((time.time()-start)*1000)}})
            return wrapped
        return decorator(fn) if fn is not None else decorator

    def wrap_openai(self, client):
        original = client.chat.completions.create
        @wraps(original)
        def tracked(*args, **kwargs):
            start=time.time(); response=original(*args, **kwargs)
            self.step_counter += 1
            sid=f'step_{self.step_counter:03d}'; parent=f'step_{self.step_counter-1:03d}' if self.step_counter > 1 else None
            choice=response.choices[0]; calls=[]
            for tc in choice.message.tool_calls or []:
                try: arguments=json.loads(tc.function.arguments or '{}')
                except Exception: arguments={'_raw':tc.function.arguments}
                calls.append({'call_id':tc.id,'function_name':tc.function.name,'arguments':arguments})
            self._record({'step_id':sid,'parent_step_id':parent,'step_number':self.step_counter,'step_type':'llm_call',
                'status':'completed','timestamp_start':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(start)),
                'timestamp_end':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                'input':{'model':kwargs.get('model'),'temperature':kwargs.get('temperature',1.0),
                         'messages':kwargs.get('messages',[]),'tools':kwargs.get('tools',[])},
                'output':{'content':choice.message.content,'tool_calls':calls,'finish_reason':choice.finish_reason},
                'metrics':{'latency_ms':int((time.time()-start)*1000),
                           'prompt_tokens':getattr(response.usage,'prompt_tokens',0),
                           'completion_tokens':getattr(response.usage,'completion_tokens',0)}})
            return response
        client.chat.completions.create = tracked
        return client