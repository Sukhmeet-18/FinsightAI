import { useState, useEffect, useRef } from 'react';
import { COMPANIES } from '../data';
import { Card, Skel, Btn } from '../ui';

const SUGG = ['What drove revenue growth this year?', 'What are the biggest risks management mentions?', 'How much debt does the company have?'];
const ANS = [
  ['Revenue grew mainly on large digital and cloud deals. Management also credits a stronger order book carried in from last year.', ['Annual Report FY25 · p. 42', 'Annual Report FY25 · p. 18']],
  ['Three risks come up repeatedly: slower client spending, currency swings, and rising staff costs. Each is discussed with a short mitigation plan.', ['Annual Report FY25 · p. 67', 'Annual Report FY25 · p. 71']],
  ['Borrowings are small compared with equity. The report describes the company as effectively debt-free for operations.', ['Annual Report FY25 · p. 104']],
];
const Ask = ({ initial }) => {
  const [co, setCo] = useState(initial || 'tcs');
  const [msgs, setMsgs] = useState([]);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState('');
  const end = useRef(null);
  useEffect(() => { if (initial) setCo(initial); }, [initial]);
  useEffect(() => { if (end.current) end.current.scrollTop = end.current.scrollHeight; }, [msgs, busy]);
  const send = (t) => { if (!t.trim() || busy) return; const i = SUGG.indexOf(t); setMsgs((m) => [...m, { r: 'u', t }]); setQ(''); setBusy(true); setTimeout(() => { const a = ANS[i >= 0 ? i : msgs.length % 3]; setMsgs((m) => [...m, { r: 'a', t: a[0], s: a[1] }]); setBusy(false); }, 1400); };
  const c = COMPANIES.find((x) => x.id === co);
  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="font-display font-normal text-4xl sm:text-5xl tracking-tight">Ask a Report</h1>
      <p className="text-stone-600 mt-2 mb-5">Ask plain questions about a company's annual report. Every answer points to the page it came from.</p>
      <div className="flex flex-wrap gap-2 mb-4" role="radiogroup" aria-label="Company">{COMPANIES.map((x) => <button key={x.id} role="radio" aria-checked={x.id === co} onClick={() => { setCo(x.id); setMsgs([]); }} className={'rounded-full px-4 py-2 text-sm font-semibold ring-1 transition ' + (x.id === co ? 'bg-brand-700 text-white ring-brand-700' : 'bg-white text-stone-800 ring-stone-200 hover:bg-stone-50')}>{x.name}</button>)}</div>
      <Card className="flex flex-col h-[560px]">
        <div ref={end} className="flex-1 overflow-y-auto p-5 grid gap-4 content-start" aria-live="polite">
          {msgs.length === 0 && <div className="text-center py-8"><div className="text-stone-500 text-sm mb-4">Asking about {c.full} · Annual Report FY25</div><div className="grid gap-2 max-w-md mx-auto">{SUGG.map((s) => <button key={s} onClick={() => send(s)} className="text-left rounded-2xl bg-[#F4EEE3] hover:bg-brand-50 px-4 py-3 text-stone-800 font-medium transition">{s}</button>)}</div></div>}
          {msgs.map((m, i) => m.r === 'u' ? <div key={i} className="justify-self-end max-w-[85%] rounded-2xl rounded-br-md bg-brand-700 text-white px-4 py-3">{m.t}</div> :
            <div key={i} className="max-w-[90%]"><div className="rounded-2xl rounded-bl-md bg-[#f4f0e6] px-4 py-3 text-stone-900 leading-relaxed">{m.t}</div><div className="flex flex-wrap gap-2 mt-2">{m.s.map((s) => <span key={s} className="inline-flex items-center gap-1.5 rounded-full bg-white ring-1 ring-stone-200 px-3 py-1 text-xs font-medium text-stone-700"><span aria-hidden="true">❡</span>{s}</span>)}</div></div>)}
          {busy && <div className="grid gap-2 max-w-[70%]"><Skel className="h-4" /><Skel className="h-4 w-4/5" /></div>}
        </div>
        <form onSubmit={(e) => { e.preventDefault(); send(q); }} className="border-t border-stone-100 p-3 flex gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} aria-label="Your question" placeholder={'Ask about ' + c.name + '…'} className="flex-1 rounded-full bg-[#F4EEE3] px-5 py-3 outline-none focus:ring-2 ring-brand-600" />
          <Btn type="submit" disabled={!q.trim() || busy}>Ask</Btn>
        </form>
      </Card>
      <p className="text-xs text-stone-500 mt-3">Preview with mock answers. Real answers may be wrong, so check the cited page.</p>
    </div>
  );
};

export default Ask;