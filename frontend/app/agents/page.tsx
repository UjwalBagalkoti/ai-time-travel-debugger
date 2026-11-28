'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowLeft, Bot, Clock3, Plus, Save, Send, Sparkles } from 'lucide-react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const STORAGE_KEY = 'time-travel-debugger.agents.v1';

type AgentProfile = {
  id: string;
  name: string;
  instructions: string;
  model: string;
  tools: string[];
};
type ChatMessage = { role: 'user' | 'assistant'; content: string };

const starterAgent: AgentProfile = {
  id: 'starter-assistant',
  name: 'Research assistant',
  instructions: 'You are a clear, careful research assistant. Ask a question when a request is ambiguous. Use the enabled tools when they help.',
  model: 'gpt-4o',
  tools: ['calculator', 'current_time'],
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [activeId, setActiveId] = useState('');
  const [ready, setReady] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [traceId, setTraceId] = useState('');
  const activeAgent = agents.find((agent) => agent.id === activeId);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      const profiles = saved ? (JSON.parse(saved) as AgentProfile[]) : [starterAgent];
      const safeProfiles = Array.isArray(profiles) && profiles.length ? profiles : [starterAgent];
      setAgents(safeProfiles);
      setActiveId(safeProfiles[0].id);
    } catch {
      setAgents([starterAgent]);
      setActiveId(starterAgent.id);
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (ready) localStorage.setItem(STORAGE_KEY, JSON.stringify(agents));
  }, [agents, ready]);

  const updateAgent = (changes: Partial<AgentProfile>) => {
    if (!activeAgent) return;
    setAgents((all) => all.map((agent) => agent.id === activeAgent.id ? { ...agent, ...changes } : agent));
  };

  const createAgent = () => {
    const agent: AgentProfile = {
      id: crypto.randomUUID(),
      name: 'New agent',
      instructions: 'Describe the role, goal, boundaries, and response style for your agent.',
      model: 'gpt-4o',
      tools: [],
    };
    setAgents((all) => [...all, agent]);
    setActiveId(agent.id);
    setMessages([]);
    setTraceId('');
    setError('');
  };

  const selectAgent = (id: string) => {
    setActiveId(id);
    setMessages([]);
    setTraceId('');
    setError('');
  };

  const toggleTool = (tool: string) => {
    if (!activeAgent) return;
    const tools = activeAgent.tools.includes(tool)
      ? activeAgent.tools.filter((item) => item !== tool)
      : [...activeAgent.tools, tool];
    updateAgent({ tools });
  };

  const run = async () => {
    if (!activeAgent || !draft.trim() || busy) return;
    const nextMessages = [...messages, { role: 'user' as const, content: draft.trim() }];
    setMessages(nextMessages);
    setDraft('');
    setError('');
    setBusy(true);
    try {
      const response = await fetch(`${API}/api/v1/agents/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_name: activeAgent.name,
          instructions: activeAgent.instructions,
          model: activeAgent.model,
          tools: activeAgent.tools,
          messages: nextMessages,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Agent run failed.');
      setMessages([...nextMessages, { role: 'assistant', content: data.reply }]);
      setTraceId(data.trace_id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Agent run failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main style={{ minHeight: '100vh', padding: 24, maxWidth: 1200, margin: 'auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, borderBottom: '1px solid #1e293b', paddingBottom: 18, marginBottom: 20 }}>
        <div>
          <Link href="/" style={{ display: 'inline-flex', gap: 7, alignItems: 'center', color: '#7dd3fc', textDecoration: 'none', fontSize: 13, marginBottom: 12 }}><ArrowLeft size={15} />Debugger</Link>
          <h1 style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: 24, margin: 0 }}><Bot color="#38bdf8" />Agent Studio</h1>
          <p className="muted" style={{ margin: '6px 0 0', fontSize: 13 }}>Create instruction-driven assistants, try them, and inspect each run as a trace.</p>
        </div>
        <button className="panel" onClick={createAgent} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', color: '#e2e8f0', cursor: 'pointer' }}><Plus size={16} />New agent</button>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 0.9fr) minmax(360px, 1.1fr)', gap: 18 }}>
        <section className="panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}><Sparkles size={17} color="#38bdf8" /><strong>Agent configuration</strong></div>
          {agents.length > 1 && <label className="muted" htmlFor="agent-profile" style={{ display: 'block', fontSize: 12, marginBottom: 6 }}>SAVED AGENTS</label>}
          {agents.length > 1 && <select id="agent-profile" value={activeId} onChange={(event) => selectAgent(event.target.value)} style={fieldStyle}>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name || 'Untitled agent'}</option>)}</select>}
          <label className="muted" htmlFor="agent-name" style={labelStyle}>AGENT NAME</label>
          <input id="agent-name" value={activeAgent?.name || ''} onChange={(event) => updateAgent({ name: event.target.value })} placeholder="For example, study planner" style={fieldStyle} />
          <label className="muted" htmlFor="agent-instructions" style={labelStyle}>INSTRUCTIONS</label>
          <textarea id="agent-instructions" value={activeAgent?.instructions || ''} onChange={(event) => updateAgent({ instructions: event.target.value })} placeholder="What should this agent do? What boundaries should it follow?" style={{ ...fieldStyle, minHeight: 180, resize: 'vertical' }} />
          <label className="muted" htmlFor="agent-model" style={labelStyle}>MODEL</label>
          <input id="agent-model" value={activeAgent?.model || ''} onChange={(event) => updateAgent({ model: event.target.value })} style={fieldStyle} />
          <div className="muted" style={{ ...labelStyle, marginTop: 18 }}>BUILT-IN TOOLS</div>
          <label style={checkboxStyle}><input type="checkbox" checked={activeAgent?.tools.includes('calculator') || false} onChange={() => toggleTool('calculator')} /> Calculator <span className="muted">(safe arithmetic)</span></label>
          <label style={checkboxStyle}><input type="checkbox" checked={activeAgent?.tools.includes('current_time') || false} onChange={() => toggleTool('current_time')} /> Current time <span className="muted">(UTC)</span></label>
          <div className="muted" style={{ fontSize: 12, lineHeight: 1.5, marginTop: 16 }}>Profiles are saved in this browser. Runs are stored as traces; don’t include secrets or private data.</div>
        </section>

        <section className="panel" style={{ padding: 20, display: 'flex', flexDirection: 'column', minHeight: 610 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: 14 }}><strong>Try your agent</strong>{traceId && <Link href={`/?trace=${encodeURIComponent(traceId)}`} style={{ color: '#7dd3fc', fontSize: 12 }}>Inspect latest run</Link>}</div>
          <div aria-live="polite" style={{ display: 'flex', flexDirection: 'column', gap: 12, flex: 1, overflowY: 'auto', padding: '16px 0' }}>
            {!messages.length && <div className="muted" style={{ margin: 'auto', textAlign: 'center', maxWidth: 320 }}><Clock3 size={22} /><p>Set the role and instructions, then send a message to run the agent.</p></div>}
            {messages.map((message, index) => <div key={`${index}-${message.role}`} style={{ alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '88%', background: message.role === 'user' ? '#082f49' : '#111827', border: '1px solid #334155', borderRadius: 12, padding: '10px 13px', whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>{message.content}</div>)}
            {busy && <div className="muted">Agent is thinking…</div>}
          </div>
          {error && <div role="alert" style={{ color: '#fca5a5', background: '#450a0a', borderRadius: 8, padding: 10, marginBottom: 10, fontSize: 13 }}>{error}</div>}
          <textarea aria-label="Message to agent" value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void run(); } }} placeholder="Ask your agent something…" style={{ ...fieldStyle, minHeight: 88, resize: 'vertical' }} />
          <button onClick={() => void run()} disabled={busy || !draft.trim() || !activeAgent?.instructions.trim()} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 10, border: 0, borderRadius: 9, padding: '11px 14px', background: '#0284c7', color: 'white', fontWeight: 700, cursor: 'pointer', opacity: busy || !draft.trim() ? 0.6 : 1 }}><Send size={15} />{busy ? 'Running…' : 'Run agent'}</button>
          <div style={{ textAlign: 'center', fontSize: 11, color: '#64748b', marginTop: 10 }}><Save size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />Agent edits save automatically in this browser</div>
        </section>
      </div>
    </main>
  );
}

const labelStyle = { display: 'block', fontSize: 11, fontWeight: 700, margin: '16px 0 6px' };
const fieldStyle = { width: '100%', color: '#e2e8f0', background: '#020617', border: '1px solid #334155', borderRadius: 8, padding: 10 };
const checkboxStyle = { display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, fontSize: 13, cursor: 'pointer' };
