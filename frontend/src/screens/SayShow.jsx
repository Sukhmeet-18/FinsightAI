import { useState } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip as RTooltip } from 'recharts';
import { COMPANIES } from '../data';
import { pct, EM, CORAL, Card } from '../ui';

const SVS = {
  tcs: { tone: 78, quote: '“We see strong demand in AI and cloud, and expect growth to build through the year.”', page: 'p. 12', trend: [1.64, 1.91, 2.25, 2.41, 2.55], ok: true, why: 'Management sounds confident and revenue has risen four years running.' },
  hul: { tone: 58, quote: '“Demand is steady, and we remain cautious on rural recovery.”', page: 'p. 9', trend: [0.47, 0.51, 0.59, 0.62, 0.63], ok: true, why: 'A measured tone matches slow but steady revenue growth.' },
  itc: { tone: 74, quote: '“We are confident about the outlook and see momentum across segments.”', page: 'p. 14', trend: [0.59, 0.76, 0.94, 0.75, 0.67], ok: false, why: 'Management sounds upbeat, yet revenue has fallen for two straight years.' },
  maruti: { tone: 66, quote: '“Record volumes and a strong pipeline of new launches.”', page: 'p. 11', trend: [0.7, 0.88, 1.18, 1.41, 1.62], ok: true, why: 'Optimistic words match fast-rising sales, though margins stay thin.' },
  rel: { tone: 84, quote: '“Our best year yet, and we expect even stronger profitability ahead.”', page: 'p. 7', trend: [5.4, 6.9, 8.8, 9.0, 9.7], ok: false, why: 'Very upbeat tone, but profit margin is only 6.6% and growth has slowed.' },
};
const Gauge = ({ v }) => (
  <div>
    <div className="relative h-4 rounded-full" style={{ background: 'linear-gradient(90deg,#f2c978,#ece3b8,#7fc9a8)' }}><div className="absolute top-1/2 h-8 w-8 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow-md ring-4 ring-brand-700 grid place-items-center text-[11px] font-bold tabular-nums" style={{ left: v + '%' }}>{v}</div></div>
    <div className="flex justify-between text-sm text-stone-600 mt-3"><span>Cautious</span><span>Neutral</span><span>Optimistic</span></div>
  </div>
);
const SayShow = () => {
  const [id, setId] = useState('itc');
  const d = SVS[id], c = COMPANIES.find((x) => x.id === id);
  const data = d.trend.map((v, i) => ({ y: 'FY' + (21 + i), v }));
  const ok = d.ok;
  return (
    <div>
      <div className="mb-5"><span className="text-xs font-semibold uppercase tracking-widest text-brand-800">New</span><h1 className="font-display font-normal text-4xl sm:text-5xl tracking-tight">Say vs. Show</h1><p className="text-stone-600 mt-2 max-w-xl">Does what management says match what the numbers show?</p></div>
      <div className="flex flex-wrap gap-2 mb-5" role="radiogroup" aria-label="Company">{COMPANIES.map((x) => <button key={x.id} role="radio" aria-checked={x.id === id} onClick={() => setId(x.id)} className={'rounded-full px-4 py-2 text-sm font-semibold ring-1 transition ' + (x.id === id ? 'bg-brand-700 text-white ring-brand-700' : 'bg-white text-stone-800 ring-stone-200 hover:bg-stone-50')}>{x.name}</button>)}</div>
      <div className={'rounded-3xl p-6 sm:p-8 flex items-center gap-5 mb-5 ' + (ok ? 'bg-brand-700 text-white' : 'bg-gold-400 text-gold-950')} role="status">
        <div className={'h-16 w-16 shrink-0 rounded-full grid place-items-center text-3xl font-bold bg-white ' + (ok ? 'text-brand-700' : 'text-gold-800')} aria-hidden="true">{ok ? '✓' : '≠'}</div>
        <div><div className="font-display text-5xl sm:text-6xl tracking-tight">{ok ? 'Aligned' : 'Mismatch'}</div><p className="text-lg mt-1">{d.why}</p></div>
      </div>
      <div className="grid gap-5 md:grid-cols-2">
        <Card className="p-6 sm:p-8 !bg-gold-50"><div className="text-sm font-semibold text-gold-900 uppercase tracking-wide">What management says</div><h2 className="text-xl font-bold mt-1 mb-6">Tone of the annual report</h2>
          <Gauge v={d.tone} />
          <blockquote className="mt-8 rounded-2xl bg-white p-4 text-stone-800 leading-relaxed">{d.quote}<footer className="text-xs text-stone-500 mt-2">{c.name} · Annual Report FY25 · {d.page}</footer></blockquote></Card>
        <Card className="p-6 sm:p-8 !bg-brand-50"><div className="text-sm font-semibold text-brand-900 uppercase tracking-wide">What the numbers show</div><h2 className="text-xl font-bold mt-1 mb-1">Revenue, 5 years</h2><p className="text-xs text-stone-500 mb-4">₹ lakh crore</p>
          <div className="h-44"><ResponsiveContainer><LineChart data={data} margin={{ top: 8, right: 12, left: 12, bottom: 0 }}><XAxis dataKey="y" tickLine={false} axisLine={false} fontSize={12} /><YAxis hide domain={['dataMin', 'dataMax']} /><RTooltip formatter={(v) => ['₹' + v + ' lakh cr', 'Revenue']} /><Line dataKey="v" stroke={d.trend[4] >= d.trend[3] ? EM : CORAL} strokeWidth={3} dot={{ r: 4, fill: '#fff', strokeWidth: 2 }} /></LineChart></ResponsiveContainer></div>
          <div className="grid grid-cols-3 gap-3 mt-4 text-center">{[['Growth', pct(c.rev)], ['Margin', c.margin + '%'], ['ROE', c.roe + '%']].map(([k, v]) => <div key={k} className="rounded-xl bg-white py-2"><div className="text-xs text-stone-500">{k}</div><div className="font-bold tabular-nums">{v}</div></div>)}</div></Card>
      </div>
      <p className="text-xs text-stone-500 mt-4">Mock content for this planned feature.</p>
    </div>
  );
};

export default SayShow;