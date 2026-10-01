'use client';
import {useMemo} from 'react'; import {ReactFlow,Background,Controls} from '@xyflow/react'; import '@xyflow/react/dist/style.css';
export type Step={step_id:string;parent_step_id:string|null;step_number:number;step_type:string;status:string};
export default function TraceCanvas({steps,selected,onSelect}:{steps:Step[];selected:string|null;onSelect:(id:string)=>void}){
 const {nodes,edges}=useMemo(()=>({nodes:steps.map((s,i)=>({id:s.step_id,position:{x:i*220,y:100},data:{label:`Step ${s.step_number}\n${s.step_type}`},style:{width:180,background:selected===s.step_id?'#0369a1':s.step_type==='llm_call'?'#111827':'#1e293b',color:'#f8fafc',border:selected===s.step_id?'2px solid #38bdf8':'1px solid #334155',borderRadius:10,padding:12,fontSize:12,fontWeight:600,whiteSpace:'pre-line' as const}})),edges:steps.filter(s=>s.parent_step_id).map(s=>({id:`e-${s.parent_step_id}-${s.step_id}`,source:s.parent_step_id!,target:s.step_id,animated:true,style:{stroke:'#38bdf8'}}))}),[steps,selected]);
 return <div style={{height:430,width:'100%'}}><ReactFlow nodes={nodes} edges={edges} onNodeClick={(_,n)=>onSelect(n.id)} fitView><Background gap={20}/><Controls/></ReactFlow></div>
}