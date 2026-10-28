import { useState, useEffect, useRef } from 'react';
import { COMPANIES } from '../data';
import { askReport } from '../api';
import { Card, Skel, Btn } from '../ui';

const SUGG = ['What was the total revenue this year?', 'What are the biggest risks the company mentions?', 'How much debt does the company have?'];

const SourceChip = ({ s, open, onToggle }) => (
  <button type="button" onClick={onToggle} aria-expanded={open} className={'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ring-1 transition ' + (s.cited ? 'bg-brand-50 text-brand-900 ring-brand-200' : 'bg-white text-stone-600 ring-stone-200 hover:bg-stone-50')}>
    <span aria-hidden="true">❡</span>p. {s.page}{s.cited ? '' : ' (nearby)'}
  </button>
);

const Answer = ({ m }) => {
  const [openPage, setOpenPage] = useState(null);
  const shown = m.s.find((x) => x.page === openPage);
  return (
    <div className="max-w-[92%]">
      <div className="rounded-2xl rounded-bl-md bg-[#f4f0e6] px-4 py-3 text-stone-900 leading-relaxed whitespace-pre-line">{m.t}</div>
      {m.unverified && m.unverified.length > 0 && <p className="text-xs text-[#8f3526] mt-2">This answer cites {m.unverified.map((p) => 'p. ' + p).join(', ')}, which was not among the passages found. Check the report yourself.</p>}
      {m.found === false && <p className="text-xs text-stone-500 mt-2">Nothing matched closely. These are the nearest passages.</p>}
      <div className="flex flex-wrap gap-2 mt-2">{m.s.map((s) => <SourceChip key={s.page} s={s} open={openPage === s.page} onToggle={() => setOpenPage(openPage === s.page ? null : s.page)} />)}</div>
      {shown && <p className="mt-2 rounded-xl bg-white ring-1 ring-stone-200 px-4 py-3 text-sm text-stone-700 leading-relaxed">“{shown.text}…”<span className="block text-xs text-stone-500 mt-1">PDF page {shown.page}</span></p>}
    </div>
  );
};

const Ask = ({ initial }) => {
  const [co, setCo] = useState(initial || 'tcs');
  const [msgs, setMsgs] = useState([]);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState('');
  const end = useRef(null);
  useEffect(() => { if (initial) setCo(initial); }, [initial]);
  useEffect(() => { if (end.current) end.current.scrollTop = end.current.scrollHeight; }, [msgs, busy]);
  const c = COMPANIES.find((x) => x.id === co);
  const send = (t) => {
    if (!t.trim() || busy) return;
    setMsgs((m) => [...m, { r: 'u', t }]); setQ(''); setBusy(true);
    askReport(c.ticker, t)
      .then((a) => setMsgs((m) => [...m, { r: 'a', t: a.answer, s: a.sources || [], found: a.found, unverified: a.unverified_pages }]))
      .catch((e) => setMsgs((m) => [...m, { r: 'e', t: e.message }]))
      .finally(() => setBusy(false));
  };
  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="font-display font-normal text-4xl sm:text-5xl tracking-tight">Ask a Report</h1>
      <p className="text-stone-600 mt-2 mb-5">Ask plain questions about a company's annual report. Every answer points to the page it came from.</p>
      <div className="flex flex-wrap gap-2 mb-4" role="radiogroup" aria-label="Company">{COMPANIES.map((x) => <button key={x.id} role="radio" aria-checked={x.id === co} onClick={() => { setCo(x.id); setMsgs([]); }} className={'rounded-full px-4 py-2 text-sm font-semibold ring-1 transition ' + (x.id === co ? 'bg-brand-700 text-white ring-brand-700' : 'bg-white text-stone-800 ring-stone-200 hover:bg-stone-50')}>{x.name}</button>)}</div>
      <Card className="flex flex-col h-[560px]">
        <div ref={end} className="flex-1 overflow-y-auto p-5 grid gap-4 content-start" aria-live="polite">
          {msgs.length === 0 && <div className="text-center py-8"><div className="text-stone-500 text-sm mb-4">Asking about {c.full} · latest annual report</div><div className="grid gap-2 max-w-md mx-auto">{SUGG.map((s) => <button key={s} onClick={() => send(s)} className="text-left rounded-2xl bg-[#F4EEE3] hover:bg-brand-50 px-4 py-3 text-stone-800 font-medium transition">{s}</button>)}</div></div>}
          {msgs.map((m, i) => m.r === 'u'
            ? <div key={i} className="justify-self-end max-w-[85%] rounded-2xl rounded-br-md bg-brand-700 text-white px-4 py-3">{m.t}</div>
            : m.r === 'e'
              ? <div key={i} role="alert" className="max-w-[90%] rounded-2xl rounded-bl-md bg-coral-50 text-stone-900 ring-1 ring-coral-100 px-4 py-3">{m.t}</div>
              : <Answer key={i} m={m} />)}
          {busy && <div className="grid gap-2 max-w-[70%]" aria-label="Searching the report"><Skel className="h-4" /><Skel className="h-4 w-4/5" /></div>}
        </div>
        <form onSubmit={(e) => { e.preventDefault(); send(q); }} className="border-t border-stone-100 p-3 flex gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} aria-label="Your question" placeholder={'Ask about ' + c.name + '…'} className="flex-1 rounded-full bg-[#F4EEE3] px-5 py-3 outline-none focus:ring-2 ring-brand-600" />
          <Btn type="submit" disabled={!q.trim() || busy}>Ask</Btn>
        </form>
      </Card>
      <p className="text-xs text-stone-500 mt-3">An AI writes each answer from passages of the annual report and can be wrong. Open the cited page in the PDF to check it.</p>
    </div>
  );
};

export default Ask;
