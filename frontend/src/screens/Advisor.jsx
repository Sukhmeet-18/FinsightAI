import { useState, useEffect } from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { COMPANIES } from '../data';
import { buildPortfolio } from '../api';
import { inr, EM, Card, Tip, Btn } from '../ui';
import { GoalFields, AdvisorExtras } from './AdvisorExtras';
const QUESTIONS = [
  ['How long can you keep this money invested?', ['Under 2 years', '2–4 years', '4–7 years', 'More than 7 years']],
  ['Your portfolio falls 20% in a month. What do you do?', ['Sell everything', 'Sell some to be safe', 'Hold and wait', 'Buy more at lower prices']],
  ['What is the main goal for this money?', ['Protect what I have', 'Steady income', 'Grow over time', 'Grow as fast as possible']],
  ['How much investing experience do you have?', ['None yet', 'A little (FDs, mutual funds)', 'Some (I own stocks)', 'A lot (I follow markets)']],
  ['How stable is your income?', ['Uncertain', 'Fairly stable', 'Stable', 'Stable, with big savings']],
];
const PROFILE = {
  conservative: ['◔', 'Conservative investor', 'You prefer to protect what you have and keep the ups and downs small.'],
  balanced: ['◐', 'Balanced investor', 'You are happy to take some ups and downs for steady growth.'],
  aggressive: ['◕', 'Growth-focused investor', 'You can sit through big swings in return for higher long-term growth.'],
};
const BUILD = ['Reading market data…', 'Forecasting risk…', 'Balancing your portfolio…'];
const CAP = [['₹1L', 100000], ['₹5L', 500000], ['₹10L', 1000000]];
     
const nameOf = (t) => COMPANIES.find((c) => c.ticker === t)?.name || t;
const p1 = (x) => (Math.round(x * 1000) / 10).toFixed(1) + '%'; // 0.1545 -> 15.5% (rounds half up)

const Advisor = () => {
  const [step, setStep] = useState(0); // 0-4 questions, 5 capital, 6 building, 7 result
  const [ans, setAns] = useState([]);
  const [cap, setCap] = useState(500000);
  const [goal, setGoal] = useState({ on: false, amount: 1500000, years: 7, sip: 5000 });
  const [bi, setBi] = useState(0);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => { if (step !== 6) return; setBi(0); const a = setTimeout(() => setBi(1), 2200), b = setTimeout(() => setBi(2), 4400); return () => [a, b].forEach(clearTimeout); }, [step]);
  const reset = () => { setStep(0); setAns([]); setResult(null); setErr(''); };
  const build = () => {
    setErr(''); setResult(null); setStep(6);
       buildPortfolio(ans.map((a) => a + 1), cap, goal.on ? { goal_amount: goal.amount, years: goal.years, monthly_contribution: goal.sip } : null).then((r) => { setResult(r); setStep(7); }).catch((e) => setErr(e.message));
  };
  const prog = step <= 5 ? (step / 6) * 100 : 100;

  if (step === 7 && result) return <Result r={result} reset={reset} />;
  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <div className="flex justify-between text-sm text-stone-600 mb-2"><span>{step < 5 ? `Question ${step + 1} of 5` : step === 5 ? 'Last step' : 'Building'}</span><span className="tabular-nums">{Math.round(prog)}%</span></div>
        <div className="h-2 rounded-full bg-stone-200/70" role="progressbar" aria-valuenow={Math.round(prog)} aria-valuemin="0" aria-valuemax="100"><div className="h-full rounded-full bg-brand-700 transition-all duration-500" style={{ width: prog + '%' }} /></div>
      </div>
      {step < 5 && <div>
        <h1 className="font-display font-normal text-3xl sm:text-4xl text-stone-900 tracking-tight mb-6 text-balance">{QUESTIONS[step][0]}</h1>
        <div className="grid gap-3 sm:grid-cols-2" role="radiogroup">
          {QUESTIONS[step][1].map((o, i) => { const on = ans[step] === i; return (
            <button key={o} role="radio" aria-checked={on} onClick={() => { const a = [...ans]; a[step] = i; setAns(a); setTimeout(() => setStep(step + 1), 220); }} className={'min-h-[88px] text-left rounded-2xl p-5 bg-white shadow-[0_1px_2px_rgba(60,50,30,.05),0_8px_24px_-12px_rgba(60,50,30,.12)] flex items-center gap-4 transition hover:-translate-y-0.5 focus:outline-none focus-visible:ring-2 ring-brand-600 ' + (on ? 'ring-2 ring-brand-600 bg-brand-50' : '')}>
              <span className={'h-7 w-7 shrink-0 rounded-full grid place-items-center text-xs font-bold ' + (on ? 'bg-brand-700 text-white' : ['bg-brand-100 text-brand-800', 'bg-gold-100 text-gold-800', 'bg-coral-100 text-coral-800', 'bg-stone-100 text-stone-700'][i])}>{on ? '✓' : 'ABCD'[i]}</span>
              <span className="font-medium text-stone-900 text-lg leading-snug">{o}</span></button>); })}
        </div>
        {step > 0 && <button onClick={() => setStep(step - 1)} className="mt-6 text-sm font-medium text-stone-600 hover:text-stone-900">← Back</button>}
      </div>}
      {step === 5 && <div>
        <h1 className="font-display font-normal text-3xl sm:text-4xl text-stone-900 tracking-tight mb-2">How much would you like to invest?</h1>
        <p className="text-stone-600 mb-6">A rough figure is fine. You can change it later.</p>
        <Card className="p-6">
          <label htmlFor="cap" className="text-sm text-stone-600">Amount</label>
          <div className="flex items-center gap-2 border-b-2 border-brand-700 pb-2 mt-1"><span className="text-3xl font-bold text-stone-400">₹</span><input id="cap" inputMode="numeric" value={cap.toLocaleString('en-IN')} onChange={(e) => setCap(Number(e.target.value.replace(/\D/g, '')) || 0)} className="w-full text-4xl font-bold tabular-nums bg-transparent outline-none text-stone-900" /></div>
          <div className="flex flex-wrap gap-2 mt-5">{CAP.map(([l, v]) => <button key={l} onClick={() => setCap(v)} aria-pressed={cap === v} className={'rounded-full px-5 py-2.5 text-sm font-semibold ring-1 transition ' + (cap === v ? 'bg-brand-700 text-white ring-brand-700' : 'bg-white text-stone-800 ring-stone-200 hover:bg-stone-50')}>{l}</button>)}</div>
          <GoalFields goal={goal} setGoal={setGoal} />
        </Card>
        <div className="flex items-center justify-between mt-6"><button onClick={() => setStep(4)} className="text-sm font-medium text-stone-600">← Back</button><Btn disabled={cap < 10000 || (goal.on && (goal.amount <= 0 || goal.years <= 0))} onClick={build}>Build my portfolio</Btn></div>
      </div>}
      {step === 6 && (err
        ? <Card className="p-8 text-center !bg-coral-50" role="alert">
          <h1 className="font-display font-normal text-2xl">We couldn't build your portfolio</h1>
          <p className="text-stone-700 mt-2">{err}</p>
          <div className="mt-6 flex justify-center gap-3"><Btn kind="secondary" onClick={() => setStep(5)}>Back</Btn><Btn onClick={build}>Try again</Btn></div>
        </Card>
        : <Card className="p-8 text-center" aria-live="polite">
          <div className="mx-auto h-14 w-14 rounded-full border-4 border-brand-100 border-t-brand-700 animate-spin" />
          <h1 className="font-display font-normal text-2xl mt-6">Building your portfolio</h1>
          <p className="text-stone-600 mt-1">This can take 10–30 seconds the first time.</p>
          <ul className="mt-6 grid gap-3 text-left max-w-xs mx-auto">{BUILD.map((b, i) => <li key={b} className={'flex items-center gap-3 text-lg ' + (i > bi ? 'text-stone-400' : 'text-stone-900')}><span className={'h-6 w-6 rounded-full grid place-items-center text-xs ' + (i < bi ? 'bg-brand-700 text-white' : i === bi ? 'bg-brand-100 text-brand-800 animate-pulse' : 'bg-stone-100')}>{i < bi ? '✓' : ''}</span>{b}</li>)}</ul>
        </Card>)}
    </div>
  );
};

const Stat = ({ label, value, note, tone }) => <Card className={'p-5 ' + tone}><div className="text-sm text-stone-600">{label}</div><div className="text-3xl font-bold tabular-nums text-stone-900 mt-1">{value}</div><p className="text-xs text-stone-500 mt-2 leading-snug">{note}</p></Card>;
const Result = ({ r, reset }) => {
  const [all, setAll] = useState(false);
  const [icon, title, blurb] = PROFILE[r.profile] || PROFILE.balanced;
  const rows = all ? r.allocation : r.allocation.slice(0, 5);
  const maxW = Math.max(...r.allocation.map((a) => a.weight));
  const split = [['Large-cap', Math.round((r.cap_split.large || 0) * 100), EM], ['Mid-cap', Math.round((r.cap_split.mid || 0) * 100), '#d4a24c'], ['Small-cap', Math.round((r.cap_split.small || 0) * 100), '#e8907f']];
  const f = r.risk_forecast;
  const cov = f && /(\d+)\s*\/\s*(\d+)/.exec(f.coverage || '');
  const asOf = r.as_of ? new Date(r.as_of).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }) : '';
  return (
    <div className="grid gap-6">
      <Card className="relative overflow-hidden p-6 sm:p-10 flex flex-wrap items-center justify-between gap-4 !bg-[#0E2A24] text-white">
        <div><span className="inline-flex items-center gap-2 rounded-full bg-gold-400 text-gold-950 px-4 py-1.5 text-sm font-semibold"><span aria-hidden="true">{icon}</span>{title}</span>
          <h1 className="font-display font-normal text-4xl sm:text-5xl tracking-tight mt-3">Your portfolio for {inr(r.capital)}</h1>
          <p className="text-stone-300 mt-2 max-w-xl text-lg">{blurb} Here is a mix of {r.allocation.length} stocks that fits.</p></div>
        <span aria-hidden="true" className="absolute -right-16 -top-20 h-64 w-64 rounded-full bg-brand-700/70" /><Btn kind="secondary" className="relative" onClick={reset}>Start over</Btn>
      </Card>
      {r.notes && r.notes.length > 0 && <p className="text-sm text-gold-900 rounded-xl bg-gold-100 px-4 py-2.5">Heads-up: the optimizer could not reach its usual target for this mix, so it chose the lowest-risk option available.</p>}
      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="p-6 lg:col-span-2"><h2 className="font-semibold mb-2">Company size mix</h2>
          <div className="relative h-52"><ResponsiveContainer><PieChart><Pie data={split.map(([n, v]) => ({ n, v }))} dataKey="v" innerRadius={62} outerRadius={88} paddingAngle={3} stroke="none">{split.map((s) => <Cell key={s[0]} fill={s[2]} />)}</Pie></PieChart></ResponsiveContainer><div className="absolute inset-0 grid place-items-center text-center pointer-events-none"><div><div className="text-3xl font-bold tabular-nums">{r.allocation.length}</div><div className="text-xs text-stone-500">stocks</div></div></div></div>
          <ul className="grid gap-2 mt-3">{split.map(([n, v, c]) => <li key={n} className="flex items-center gap-2 text-sm"><span className="h-3 w-3 rounded-full" style={{ background: c }} /><span className="flex-1 text-stone-700">{n}</span><span className="font-semibold tabular-nums">{v}%</span></li>)}</ul></Card>
        <Card className="p-6 lg:col-span-3"><h2 className="font-semibold mb-4">{all ? 'All holdings' : 'Top holdings'}</h2>
          <ul className="grid gap-3">{rows.map((a) => <li key={a.ticker} className="rounded-xl bg-[#F4EEE3] px-4 py-3"><div className="flex justify-between items-baseline"><span className="font-medium text-stone-900">{nameOf(a.ticker)}</span><span className="tabular-nums font-semibold">{p1(a.weight)} <span className="text-xs font-normal text-stone-500">· {inr(a.amount)}</span></span></div><div className="h-1.5 rounded-full bg-white mt-2 overflow-hidden"><div className="h-full rounded-full bg-brand-700" style={{ width: (a.weight / maxW) * 100 + '%' }} /></div><div className="text-xs text-stone-500 mt-1.5">{a.cap.charAt(0).toUpperCase() + a.cap.slice(1)}-cap · {a.shares > 0 ? `${a.shares} ${a.shares === 1 ? 'share' : 'shares'} at ${inr(a.price)}` : `below 1 share at ${inr(a.price)}`}</div></li>)}</ul>
          {r.allocation.length > 5 && <button onClick={() => setAll(!all)} className="mt-4 text-sm font-semibold text-brand-800 hover:underline">{all ? 'Show top 5' : `Show all ${r.allocation.length} →`}</button>}</Card>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat tone="!bg-brand-100" label="Expected yearly return" value={p1(r.metrics.exp_return)} note="An assumption based on past data, not a promise. Real returns can be lower or negative." />
        <Stat tone="!bg-gold-100" label={<Tip term="Volatility" tip="How much the portfolio value usually swings up and down in a year." />} value={p1(r.metrics.volatility)} note="In a typical year, value may move about this much either way." />
        <Stat tone="!bg-brand-50" label={<Tip term="Return per unit of risk" tip="Also called the Sharpe ratio. Higher means you are paid more for each bit of risk." />} value={r.metrics.sharpe.toFixed(2)} note="Higher is better. Under 0.5 is common for stock-only portfolios." />
      </div>
      {f && <Card className="p-6 sm:p-8">
        <h2 className="text-xl font-bold">Risk forecast</h2><p className="text-stone-600 mt-1 mb-5">What a rough patch could look like on {inr(r.capital)}. Also called <Tip term="bad-day loss" tip="Value at Risk (VaR): a loss level you'd only expect to cross on 1 in 20 days." />.</p>
        <div className="grid gap-4 md:grid-cols-3">
          {[['On a bad day', '1 in 20', f.var_95_1d_amount, 'you could lose more than this'], ['On those bad days', 'the average', f.cvar_95_1d_amount, 'is the average loss'], ['In a bad month', '1 in 20', f.var_95_21d_amount, 'you could lose more than this']].map(([a, b, v, t]) => (
            <div key={a} className="rounded-2xl bg-coral-50/70 p-5"><div className="flex items-center gap-2 text-sm font-semibold text-[#8f3526]"><span aria-hidden="true">▼</span>{a} <span className="font-normal text-stone-600">({b})</span></div><div className="text-3xl font-bold tabular-nums text-stone-900 mt-3">{inr(v)}</div><p className="text-sm text-stone-700 mt-1">{t}</p></div>))}
        </div>
        <p className="text-xs text-stone-500 mt-5">{cov ? `${cov[1]} of ${cov[2]} holdings use our AI risk model; the rest use historical data.` : f.coverage}{asOf && ` Prices as of ${asOf}.`}</p>
      </Card>}
    <AdvisorExtras r={r} />
    </div>
  );
};

export default Advisor;