import { useState, useEffect } from 'react';
import { COMPANIES } from '../data';
import { fetchDetector } from '../api';
import { Card, Skel, Btn } from '../ui';

const VERDICT = {
  consistent: { title: 'Aligned', why: 'Compared with the other companies, the tone of the report matches what the numbers show.', ok: true },
  says_more_than_shows: { title: 'Says more than it shows', why: 'The report sounds more upbeat than the numbers justify, compared with the other companies.', ok: false },
  shows_more_than_says: { title: 'Shows more than it says', why: 'The numbers look stronger than the report’s cautious tone suggests, compared with the other companies.', ok: false },
  not_enough_data: { title: 'Not enough data', why: 'We could not measure the tone or the trend for this company.', ok: null },
  not_enough_companies: { title: 'Not enough companies', why: 'Comparison needs at least three analysed companies.', ok: null },
};
const clamp = (x) => Math.max(0, Math.min(100, x));
const sign = (v, d = 1) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d);

const Gauge = ({ z, left, right, label }) => (
  <div role="img" aria-label={label}>
    <div className="relative h-4 rounded-full" style={{ background: 'linear-gradient(90deg,#f2c978,#ece3b8,#7fc9a8)' }}>
      <div className="absolute top-1/2 h-7 w-7 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow-md ring-4 ring-brand-700" style={{ left: clamp(50 + (z || 0) * 25) + '%' }} />
    </div>
    <div className="flex justify-between text-sm text-stone-600 mt-3"><span>{left}</span><span>Average of the five</span><span>{right}</span></div>
  </div>
);

const Quote = ({ q, name, kind }) => (
  <blockquote className="rounded-2xl bg-white p-4 text-stone-800 leading-relaxed text-sm">
    <div className="text-xs font-semibold uppercase tracking-wide text-stone-500 mb-1">{kind}</div>
    “{q.text}”<footer className="text-xs text-stone-500 mt-2">{name} · annual report · PDF page {q.page}</footer>
  </blockquote>
);

const SayShow = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [id, setId] = useState('itc');
  const load = () => { setError(''); setData(null); fetchDetector().then(setData).catch((e) => setError(e.message)); };
  useEffect(() => { load(); }, []);
  const co = COMPANIES.find((x) => x.id === id);
  const r = data && data.companies.find((x) => x.ticker === co.ticker);
  const v = r && (VERDICT[r.verdict] || VERDICT.not_enough_data);
  const tr = r && r.trend;
  return (
    <div>
      <div className="mb-5"><span className="text-xs font-semibold uppercase tracking-widest text-brand-800">Experimental</span><h1 className="font-display font-normal text-4xl sm:text-5xl tracking-tight">Say vs. Show</h1><p className="text-stone-600 mt-2 max-w-xl">Does what the annual report says match what the numbers show?</p></div>
      <div className="flex flex-wrap gap-2 mb-5" role="radiogroup" aria-label="Company">{COMPANIES.map((x) => <button key={x.id} role="radio" aria-checked={x.id === id} onClick={() => setId(x.id)} className={'rounded-full px-4 py-2 text-sm font-semibold ring-1 transition ' + (x.id === id ? 'bg-brand-700 text-white ring-brand-700' : 'bg-white text-stone-800 ring-stone-200 hover:bg-stone-50')}>{x.name}</button>)}</div>
      {error && <Card className="p-6 mb-5 !bg-coral-50" role="alert"><h3 className="font-semibold">Say vs. Show is not ready</h3><p className="text-sm text-stone-700 mt-1">{error}</p><Btn className="mt-4" onClick={load}>Try again</Btn></Card>}
      {!error && !data && <div className="grid gap-4"><Skel className="h-28 rounded-3xl" /><div className="grid gap-5 md:grid-cols-2"><Skel className="h-64 rounded-2xl" /><Skel className="h-64 rounded-2xl" /></div></div>}
      {data && !r && <Card className="p-6 mb-5"><p className="text-stone-700">No result for {co.name} yet. Build its report index and run the analysis again.</p></Card>}
      {r && (
        <>
          <div className={'rounded-3xl p-6 sm:p-8 flex items-center gap-5 mb-5 ' + (v.ok === true ? 'bg-brand-700 text-white' : v.ok === false ? 'bg-gold-400 text-gold-950' : 'bg-stone-200 text-stone-900')} role="status">
            <div className={'h-16 w-16 shrink-0 rounded-full grid place-items-center text-3xl font-bold bg-white ' + (v.ok === true ? 'text-brand-700' : v.ok === false ? 'text-gold-800' : 'text-stone-600')} aria-hidden="true">{v.ok === true ? '✓' : v.ok === false ? '≠' : '?'}</div>
            <div><div className="font-display text-4xl sm:text-5xl tracking-tight">{v.title}</div><p className="text-lg mt-1">{v.why}</p></div>
          </div>
          <div className="grid gap-5 md:grid-cols-2">
            <Card className="p-6 sm:p-8 !bg-gold-50">
              <div className="text-sm font-semibold text-gold-900 uppercase tracking-wide">What the report says</div>
              <h2 className="text-xl font-bold mt-1 mb-6">Tone of the narrative</h2>
              <Gauge z={r.tone_z} left="More cautious" right="More upbeat" label="Tone compared with the other companies" />
              <p className="text-sm text-stone-600 mt-4">{r.sentences} sentences read. Positive {Math.round((r.positive_share || 0) * 100)}%, negative {Math.round((r.negative_share || 0) * 100)}%. Net tone {r.tone == null ? 'n/a' : sign(r.tone, 2)}.</p>
              <div className="grid gap-3 mt-4">
                {r.most_positive && r.most_positive[0] && <Quote q={r.most_positive[0]} name={co.name} kind="Most upbeat sentence" />}
                {r.most_negative && r.most_negative[0] && <Quote q={r.most_negative[0]} name={co.name} kind="Most cautious sentence" />}
              </div>
            </Card>
            <Card className="p-6 sm:p-8 !bg-brand-50">
              <div className="text-sm font-semibold text-brand-900 uppercase tracking-wide">What the numbers show</div>
              <h2 className="text-xl font-bold mt-1 mb-6">Growth, margin and return</h2>
              <Gauge z={r.trend_z} left="Weaker" right="Stronger" label="Trend compared with the other companies" />
              {tr ? (
                <div className="grid grid-cols-3 gap-3 mt-6 text-center">
                  {[['Latest revenue growth', tr.revenue_growth_latest == null ? 'n/a' : sign(tr.revenue_growth_latest * 100) + '%'], ['Margin change', tr.margin_change == null ? 'n/a' : sign(tr.margin_change * 100) + ' pts'], ['ROE change', tr.roe_change == null ? 'n/a' : sign(tr.roe_change * 100) + ' pts']].map(([k, val]) => <div key={k} className="rounded-xl bg-white py-3 px-1"><div className="text-xs text-stone-500">{k}</div><div className="font-bold tabular-nums">{val}</div></div>)}
                </div>
              ) : <p className="text-sm text-stone-600 mt-6">No yearly results were found for this company.</p>}
              {tr && <p className="text-xs text-stone-500 mt-3">Based on yearly results for {tr.years.join(', ')}. A single one-off item can distort a short trend.</p>}
            </Card>
          </div>
          <p className="text-xs text-stone-500 mt-4">Annual reports usually sound upbeat, so each score is compared with the other four companies and a flag is raised only when the gap between the two is large (gap {r.gap == null ? 'n/a' : sign(r.gap, 2)}). This is experimental: the thresholds have not yet been checked against labelled examples.</p>
        </>
      )}
    </div>
  );
};

export default SayShow;
