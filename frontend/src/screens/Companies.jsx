import { useState, useEffect } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, AreaChart, Area } from 'recharts';
import { priceSeries, revData } from '../data';
import { fetchCompanies } from '../api';
import { inr, pct, EM, LABEL, LEVEL, Card, Skel, Tip, LabelChip, Ring, MiniBar, Btn } from '../ui';

const TINT = { 'Strong Buy': 'bg-brand-100', Buy: 'bg-[#E3F1E8]', Hold: 'bg-gold-100', Sell: 'bg-coral-100' };
const CARD_SH = 'shadow-[0_1px_2px_rgba(60,50,30,.05),0_10px_28px_-12px_rgba(60,50,30,.18)]';
const CompanyCard = ({ c, onOpen, compare, selected, onToggle, featured: d }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className={'rounded-2xl overflow-hidden flex flex-col transition hover:-translate-y-0.5 ' + CARD_SH + (d ? ' md:col-span-2 bg-[#0E2A24] text-white' : ' bg-white') + (selected ? ' ring-2 ring-brand-600' : '')}>
      <div className={d ? 'grid md:grid-cols-2 flex-1' : 'flex flex-col flex-1'}>
        <div className={'p-5 sm:p-6 flex flex-col gap-4 ' + (d ? '' : TINT[c.label])}>
          {d && <span className="self-start rounded-full bg-gold-400 text-gold-950 px-3 py-1 text-xs font-bold">★ Highest score of the five</span>}
          <div className="flex items-start gap-4">
            <div className={d ? 'rounded-full bg-white p-1' : ''}><Ring score={c.score} label={c.label} size={d ? 76 : 64} /></div>
            <div className="min-w-0 flex-1">
              <button onClick={() => (compare ? onToggle(c.id) : onOpen(c))} className={'text-left font-semibold leading-tight focus:outline-none focus-visible:underline ' + (d ? 'text-2xl text-white' : 'text-lg text-stone-900 hover:text-brand-800')}>{c.name}</button>
              <div className={'text-xs mt-0.5 ' + (d ? 'text-brand-200' : 'text-stone-600')}>NSE: {c.ticker}</div>
            </div>
            {compare && <label className="flex items-center gap-2 text-xs font-medium cursor-pointer"><input type="checkbox" checked={selected} onChange={() => onToggle(c.id)} className="h-5 w-5 accent-brand-700" />Compare</label>}
          </div>
          <div className="flex items-end justify-between gap-3 mt-auto">
            <div className={'font-bold tabular-nums ' + (d ? 'text-4xl' : 'text-3xl text-stone-900')}>{inr(c.price)}</div>
            <LabelChip label={c.label} />
          </div>
        </div>
        <div className={'p-5 sm:p-6 flex flex-col gap-3 ' + (d ? 'bg-[#143A31]' : '')}>
          <MiniBar dark={d} name="Revenue growth" value={c.rev} max={40} tip="How much the company's sales grew versus last year." />
          <MiniBar dark={d} name="Profit margin" value={c.margin} max={40} tip="Out of every ₹100 of sales, how much is kept as profit." />
          <MiniBar dark={d} name="ROE" value={c.roe} max={50} tip="Return on equity: profit earned on every ₹100 of shareholder money." />
          {d && <div className="h-16 -mx-1 mt-1" aria-hidden="true"><ResponsiveContainer><AreaChart data={revData(c)}><defs><linearGradient id="fg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#E8A93A" stopOpacity=".4" /><stop offset="1" stopColor="#E8A93A" stopOpacity="0" /></linearGradient></defs><Area dataKey="v" stroke="#E8A93A" strokeWidth={2.5} fill="url(#fg)" /></AreaChart></ResponsiveContainer></div>}
        </div>
      </div>
      <div className={'px-5 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-2 border-t ' + (d ? 'border-white/10' : 'border-stone-100')}>
        <div>
          <button onClick={() => setOpen(!open)} aria-expanded={open} className={'text-sm font-semibold flex items-center gap-1.5 focus:outline-none focus-visible:underline ' + (d ? 'text-gold-300' : 'text-brand-800')}><span aria-hidden="true" className={'transition inline-block ' + (open ? 'rotate-90' : '')}>›</span>Why this score?</button>
          {open && <p className={'text-sm mt-2 leading-relaxed max-w-md ' + (d ? 'text-stone-200' : 'text-stone-700')}>{c.why}</p>}
        </div>
        {!compare && <button onClick={() => onOpen(c)} className={'text-sm font-semibold focus:outline-none focus-visible:underline ' + (d ? 'text-white' : 'text-stone-600 hover:text-brand-800')}>View details →</button>}
      </div>
    </div>
  );
};

const Drawer = ({ c, onClose, onAsk }) => {
  useEffect(() => { const k = (e) => e.key === 'Escape' && onClose(); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, []);
  const [ready, setReady] = useState(false);
  useEffect(() => { const t = setTimeout(() => setReady(true), 500); return () => clearTimeout(t); }, [c.id]);
  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={c.name + ' details'}>
      <div className="absolute inset-0 bg-stone-900/30" onClick={onClose} />
      <aside className="absolute right-0 top-0 h-full w-full max-w-xl bg-[#F4EEE3] shadow-2xl overflow-y-auto p-5 sm:p-7 flex flex-col gap-5">
        <div className="flex items-start gap-4">
          <Ring score={c.score} label={c.label} size={72} />
          <div className="flex-1"><h2 className="text-2xl font-bold text-stone-900">{c.full}</h2><div className="flex items-center gap-3 mt-1.5"><LabelChip label={c.label} /><span className="text-xl font-bold tabular-nums">{inr(c.price)}</span></div></div>
          <button onClick={onClose} aria-label="Close" className="h-10 w-10 rounded-full bg-white ring-1 ring-stone-200 text-lg hover:bg-stone-50">✕</button>
        </div>
        <p className="text-stone-700 leading-relaxed">{c.why}</p>
        <Card className="p-5"><h3 className="font-semibold mb-1">Revenue, last 5 years</h3><p className="text-xs text-stone-500 mb-3">₹ lakh crore</p>
          {ready ? <div className="h-44"><ResponsiveContainer><BarChart data={revData(c)}><XAxis dataKey="y" tickLine={false} axisLine={false} fontSize={12} /><YAxis hide /><RTooltip cursor={{ fill: '#f5f1e8' }} formatter={(v) => ['₹' + v + ' lakh cr', 'Revenue']} /><Bar dataKey="v" fill={EM} radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer></div> : <Skel className="h-44" />}</Card>
        <Card className="p-5"><h3 className="font-semibold mb-1">Share price, last 12 months</h3><p className="text-xs text-stone-500 mb-3">Past prices don't predict future prices.</p>
          {ready ? <div className="h-44"><ResponsiveContainer><AreaChart data={priceSeries(c)}><defs><linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={EM} stopOpacity=".25" /><stop offset="1" stopColor={EM} stopOpacity="0" /></linearGradient></defs><XAxis dataKey="m" tickLine={false} axisLine={false} fontSize={12} interval={1} /><YAxis hide domain={['dataMin', 'dataMax']} /><RTooltip formatter={(v) => [inr(v), 'Price']} /><Area dataKey="p" stroke={EM} strokeWidth={2.5} fill="url(#pg)" /></AreaChart></ResponsiveContainer></div> : <Skel className="h-44" />}</Card>
        <Card className="p-5"><h3 className="font-semibold mb-3">Risk snapshot</h3>
          <div className="grid gap-2.5">{c.risks.map(([k, v]) => <div key={k} className="flex items-center justify-between"><span className="text-sm text-stone-700">{k}</span><span className={'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ' + LEVEL[v][0]}><span aria-hidden="true">{LEVEL[v][1]}</span>{v}</span></div>)}</div></Card>
        <Btn onClick={() => onAsk(c.id)}>Ask about this report →</Btn>
      </aside>
    </div>
  );
};

const ComparePanel = ({ items, onClear }) => (
  <Card className="p-5 mb-6">
    <div className="flex items-center justify-between mb-4"><h3 className="font-semibold text-lg">Side by side</h3><button onClick={onClear} className="text-sm text-stone-500 hover:text-stone-900">Clear</button></div>
    <div className={'grid gap-4 ' + (items.length === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-2')}>
      {items.map((c) => (
        <div key={c.id} className="rounded-xl bg-[#F4EEE3] p-4 grid gap-3">
          <div className="flex items-center gap-3"><Ring score={c.score} label={c.label} size={48} /><div><div className="font-semibold leading-tight">{c.name}</div><LabelChip label={c.label} /></div></div>
          <MiniBar name="Revenue growth" value={c.rev} max={40} /><MiniBar name="Profit margin" value={c.margin} max={40} /><MiniBar name="ROE" value={c.roe} max={50} />
        </div>
      ))}
    </div>
  </Card>
);
const Companies = ({ onAsk }) => {
  const [companies, setCompanies] = useState(null);
  const [error, setError] = useState(false);
  const [sel, setSel] = useState(null);
  const [compare, setCompare] = useState(false);
  const [picked, setPicked] = useState([]);
  const load = () => { setError(false); setCompanies(null); fetchCompanies().then(setCompanies).catch(() => setError(true)); };
  useEffect(() => { load(); }, []);
  const loading = companies === null && !error;
  const toggle = (id) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length < 3 ? [...p, id] : p));
  return (
    <div>
      <div className="relative overflow-hidden rounded-3xl bg-[#0E2A24] text-white p-6 sm:p-10 mb-8">
        <span aria-hidden="true" className="absolute -right-20 -top-24 h-80 w-80 rounded-full bg-brand-700/70" />
        <span aria-hidden="true" className="hidden sm:block absolute right-16 -bottom-28 h-60 w-60 rounded-full bg-gold-400" />
        <div className="relative max-w-xl">
          <p className="text-sm font-semibold text-gold-300 mb-3">Companies</p>
          <h1 className="font-display font-normal font-display text-4xl sm:text-6xl leading-[1.05] tracking-tight">Know <em className="text-gold-300">why</em> a stock earns its score.</h1>
          <p className="text-stone-300 mt-4 text-lg max-w-md">Five well-known NSE companies, scored 0–100 on growth, profit and returns. Tap one to see what's behind it.</p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button onClick={() => { setCompare(!compare); setPicked([]); }} aria-pressed={compare} className="rounded-full bg-white text-[#0E2A24] px-5 py-2.5 text-sm font-semibold hover:bg-gold-100 transition focus:outline-none focus-visible:ring-2 ring-gold-300">{compare ? 'Exit compare' : 'Compare 2–3 companies'}</button>
            <span className="text-sm text-stone-300">Score guide:</span>
            <div className="flex flex-wrap gap-1.5">{['Strong Buy', 'Buy', 'Hold', 'Sell'].map((l) => <LabelChip key={l} label={l} />)}</div>
          </div>
        </div>
      </div>
      {compare && <p className="text-sm text-stone-600 mb-4 rounded-xl bg-brand-50 px-4 py-2.5">Pick 2 or 3 companies. {picked.length}/3 selected.</p>}
      {compare && picked.length >= 2 && <ComparePanel items={(companies || []).filter((c) => picked.includes(c.id))} onClear={() => setPicked([])} />}
      {error && <Card className="p-6 mb-6 !bg-coral-50"><h3 className="font-semibold">Can't reach the backend</h3><p className="text-sm text-stone-700 mt-1">Is uvicorn running on port 8000? Start it from the project folder, then try again.</p><Btn className="mt-4" onClick={load}>Try again</Btn></Card>}
      {loading && <p className="text-sm text-stone-600 mb-4" aria-live="polite">Fetching live data. The first load can take 10–20 seconds.</p>}
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {loading ? [0, 1, 2].map((i) => <Card key={i} className="p-5 grid gap-4"><div className="flex gap-4"><Skel className="h-16 w-16 rounded-full" /><div className="flex-1 grid gap-2"><Skel className="h-5 w-2/3" /><Skel className="h-3 w-1/3" /></div></div><Skel className="h-8 w-1/2" /><Skel className="h-12" /><Skel className="h-12" /></Card>)
          : (companies || []).map((c, n) => <CompanyCard key={c.id} featured={n === 0 && !compare} c={c} onOpen={setSel} compare={compare} selected={picked.includes(c.id)} onToggle={toggle} />)}
      </div>
      {companies && <p className="text-xs text-stone-500 mt-4">Scores, prices and ratios are live from the backend. Charts, the "Why" text and risk tags are still sample content.</p>}
      {sel && <Drawer c={sel} onClose={() => setSel(null)} onAsk={(id) => { setSel(null); onAsk(id); }} />}
    </div>
  );
};

export default Companies;