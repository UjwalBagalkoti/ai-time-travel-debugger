import json, os
from typing import Any, Dict, Optional

class ReplayEngine:
    """Deterministic replay helpers. Historical tool calls are reused only on exact argument matches."""
    @staticmethod
    def tool_cache_key(name: str, arguments: Dict[str, Any]) -> str:
        return json.dumps({'tool_name': name, 'arguments': arguments}, sort_keys=True, separators=(',', ':'))

    def cached_tool_result(self, historical_steps, tool_name: str, requested_args: Dict[str, Any]):
        key=self.tool_cache_key(tool_name, requested_args)
        for step in historical_steps:
            inp=step.get('input', {})
            if inp.get('tool_name') and self.tool_cache_key(inp['tool_name'], inp.get('arguments', {})) == key:
                out=step.get('output', {})
                return out.get('result', out), True
        return None, False

    def live_llm(self, model: str, messages: list, temperature: float = 0.2, tools=None) -> Optional[Dict[str, Any]]:
        if not os.getenv('OPENAI_API_KEY'): return None
        try:
            from openai import OpenAI
            response=OpenAI().chat.completions.create(model=model,messages=messages,temperature=temperature,tools=tools or None)
            choice=response.choices[0]
            calls=[]
            for tc in choice.message.tool_calls or []:
                try: args=json.loads(tc.function.arguments or '{}')
                except Exception: args={'_raw':tc.function.arguments}
                calls.append({'call_id':tc.id,'function_name':tc.function.name,'arguments':args})
            return {'content':choice.message.content,'tool_calls':calls,'finish_reason':choice.finish_reason,'usage':{'prompt_tokens':getattr(response.usage,'prompt_tokens',0),'completion_tokens':getattr(response.usage,'completion_tokens',0)}}
        except Exception as exc: return {'error':str(exc)}