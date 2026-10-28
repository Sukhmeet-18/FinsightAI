import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip as RTooltip, ComposedChart, Area, ReferenceLine } from 'recharts';
import { inr, EM, CORAL, Card } from '../ui';

const lakh = (v) => '₹' + (v / 100000).toFixed(1) + ' lakh';
const pc = (v) => (v < 0 ? '−' : '') + Math.abs(v * 100).toFixed(1) + '%';

// optional goal inputs, shown on the amount step
export const GoalFields = ({ goal, setGoal }) => {
  const num = (k) => (e) => setGoal({ ...goal, [k]: Number(e.target.value.replace(/\D/g, '')) || 0 });
  const fields = [['amount', 'Goal amount (₹)', goal.amount.toLocaleString('en-IN')], ['years', 'In how many years', String(goal.years)], ['sip', 'Monthly top-up (₹)', goal.sip.toLocaleString('en-IN')]];
  return (
    <div className="mt-6 pt-5 border-t border-stone-100">
      <label className="flex items-center gap-3 cursor-pointer">
        <input type="checkbox" checked={goal.on} onChange={(e) => setGoal({ ...goal, on: e.target.checked })} className="h-5 w-5 accent-brand-700" />
        <span className="font-semibold">I have a goal in mind <span className="font-normal text-stone-500">(optional)</span></span>
      </label>
      {goal.on && <div className="grid gap-4 sm:grid-cols-3 mt-4">
        {fields.map(([k, l, v]) => (
          <label key={k} className="grid gap-1 text-sm text-stone-600">{l}
            <input inputMode="numeric" value={v} onChange={num(k)} className="rounded-xl bg-[#F4EEE3] px-4 py-3 text-lg font-semibold tabular-nums text-stone-900 outline-none focus:ring-2 ring-brand-600" />
          </label>))}
      </div>}
    </div>
  );
};

const GoalCard = ({ r }) => {
  const g = r.goal_projection;
  if (!g) return null;
  const fan = [{ year: 0, low: r.capital, a: 0, b: 0, c: 0, p5: r.capital, p50: r.capital, p95: r.capital },
    ...g.fan_chart.map((x) => ({ year: x.year, low: x.p5, a: x.p25 - x.p5, b: x.p75 - x.p25, c: x.p95 - x.p75, p5: x.p5, p50: x.p50, p95: x.p95 }))];
  const need = g.monthly_needed_for_75pct;
  return (
    <Card className="p-6 sm:p-8">
      <h2 className="text-xl font-bold">Your goal</h2>
      <div className="grid gap-6 md:grid-cols-5 mt-4">
        <div className="md:col-span-2">
          <div className="font-display text-7xl tracking-tight text-brand-800 tabular-nums">{Math.round(g.probability_of_goal * 100)}%</div>
          <p className="text-stone-700 mt-1">chance of reaching {inr(g.goal_amount)} in {g.years} {g.years === 1 ? 'year' : 'years'}, if you put in {inr(g.total_invested)} in total.</p>
          <ul className="mt-4 grid gap-1.5 text-sm text-stone-700">
            <li>Middle half of outcomes: <b className="tabular-nums">{lakh(g.final_value.p25)}</b> to <b className="tabular-nums">{lakh(g.final_value.p75)}</b></li>
            <li>A bad 1-in-20 case: <b className="tabular-nums">{lakh(g.final_value.p5)}</b> or less</li>
            <li>{need === null ? 'A 75% chance is not reachable with these inputs.' : need === 0 ? 'You are already above a 75% chance.' : <>For a 75% chance you would need about <b className="tabular-nums">{inr(need)}</b> a month.</>}</li>
          </ul>
        </div>
        <div className="md:col-span-3">
          <div className="h-56" role="img" aria-label="Range of possible portfolio values over the years">
            <ResponsiveContainer>
              <ComposedChart data={fan} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                <XAxis dataKey="year" tickLine={false} axisLine={false} fontSize={12} tickFormatter={(y) => (y === 0 ? 'Now' : 'Yr ' + y)} />
                <YAxis hide domain={[0, 'dataMax']} />
                <RTooltip content={({ active, payload }) => (active && payload && payload[0] ? (
                  <div className="rounded-xl bg-white px-3 py-2 text-xs shadow ring-1 ring-stone-200">
                    <div className="font-semibold mb-1">{payload[0].payload.year === 0 ? 'Today' : 'After ' + payload[0].payload.year + ' yr'}</div>
                    <div>Bad case (1 in 20): {lakh(payload[0].payload.p5)}</div>
                    <div>Middle: {lakh(payload[0].payload.p50)}</div>
                    <div>Good case (1 in 20): {lakh(payload[0].payload.p95)}</div>
                  </div>) : null)} />
                <Area dataKey="low" stackId="s" stroke="none" fill="none" isAnimationActive={false} />
                <Area dataKey="a" stackId="s" stroke="none" fill={EM} fillOpacity={0.14} isAnimationActive={false} />
                <Area dataKey="b" stackId="s" stroke="none" fill={EM} fillOpacity={0.3} isAnimationActive={false} />
                <Area dataKey="c" stackId="s" stroke="none" fill={EM} fillOpacity={0.14} isAnimationActive={false} />
                <Line dataKey="p50" stroke={EM} strokeWidth={2.5} dot={false} isAnimationActive={false} />
                <ReferenceLine y={g.goal_amount} stroke={CORAL} strokeDasharray="5 5" ifOverflow="extendDomain" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-stone-500 mt-1">Dashed line: your goal. Dark band: the middle half of outcomes. Light band: 9 in 10 outcomes.</p>
        </div>
      </div>
      <p className="text-xs text-stone-500 mt-5">This assumes the portfolio grows {pc(r.metrics.exp_return)} a year, which is an assumption and not a forecast. With a lower return the chances fall quickly. It also assumes you keep the top-up going every month.</p>
    </Card>
  );
};

const StressTests = ({ r }) => {
  const rows = (r.stress_test || []).filter((s) => s.status === 'ok');
  if (!rows.length) return null;
  const max = Math.max(...rows.map((s) => Math.max(Math.abs(s.portfolio_return), Math.abs(s.nifty_return))));
  return (
    <Card className="p-6 sm:p-8">
      <h2 className="text-xl font-bold">In past crashes</h2>
      <p className="text-stone-600 mt-1 mb-5">What today's holdings would have done in four real market falls, compared with the Nifty 50.</p>
      <div className="grid gap-5 md:grid-cols-2">
        {rows.map((s) => (
          <div key={s.event} className="rounded-2xl bg-[#F4EEE3] p-5">
            <div className="font-semibold text-stone-900">{s.event}</div>
            <div className="text-xs text-stone-500 mb-3">{s.start.slice(0, 4)} to {s.end.slice(0, 4)}</div>
            {[['This portfolio', s.portfolio_return, CORAL], ['Nifty 50', s.nifty_return, '#a8a29e']].map(([n, v, c]) => (
              <div key={n} className="mb-2">
                <div className="flex justify-between text-sm"><span className="text-stone-700">{n}</span><span className="font-semibold tabular-nums">{pc(v)}</span></div>
                <div className="h-2 rounded-full bg-white overflow-hidden"><div className="h-full rounded-full" style={{ width: (Math.abs(v) / max) * 100 + '%', background: c }} /></div>
              </div>))}
            <p className="text-sm text-stone-700 mt-3">On {inr(r.capital)} that is about <b className="tabular-nums">{inr(Math.abs(s.estimated_amount_change))}</b> lost, back to its starting value about {s.days_to_recover} days after the low.</p>
            {s.coverage < 0.99 && <p className="text-xs text-stone-500 mt-1">Based on the {Math.round(s.coverage * 100)}% of today's holdings that already existed then.</p>}
          </div>))}
      </div>
      <p className="text-xs text-stone-500 mt-5">This replays today's holdings, which are all companies that survived. Companies that did not survive are missing, so a real crash could hurt more.</p>
    </Card>
  );
};

const PastRecord = ({ r }) => {
  const h = r.historical;
  if (!h || !r.growth_chart) return null;
  return (
    <Card className="p-6 sm:p-8">
      <div className="flex flex-wrap items-baseline justify-between gap-2"><h2 className="text-xl font-bold">The last 3 years</h2><span className="rounded-full bg-gold-100 text-gold-900 px-3 py-1 text-xs font-semibold">Not a forecast</span></div>
      <p className="text-stone-600 mt-1 mb-4">₹100 put into these exact weights in {h.period_start.slice(0, 4)}, against the Nifty 50.</p>
      <div className="h-52" role="img" aria-label="Growth of 100 rupees: portfolio against Nifty 50">
        <ResponsiveContainer>
          <LineChart data={r.growth_chart} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <XAxis dataKey="date" tickLine={false} axisLine={false} fontSize={12} minTickGap={50} tickFormatter={(d) => d.slice(0, 4)} />
            <YAxis hide domain={['dataMin', 'dataMax']} />
            <RTooltip formatter={(v, n) => ['₹' + Number(v).toFixed(0), n === 'portfolio' ? 'Portfolio' : 'Nifty 50']} />
            <Line dataKey="portfolio" stroke={EM} strokeWidth={2.5} dot={false} isAnimationActive={false} />
            <Line dataKey="nifty" stroke="#a8a29e" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="grid gap-3 sm:grid-cols-3 mt-4 text-center">
        {[['Yearly growth', pc(h.cagr), 'Nifty ' + pc(h.nifty_cagr)], ['Worst fall', pc(h.max_drawdown), 'Nifty ' + pc(h.nifty_max_drawdown)], ['Moves with the market', h.beta.toFixed(2), '1.00 = same as the Nifty']].map(([k, v, n]) => (
          <div key={k} className="rounded-xl bg-[#F4EEE3] py-3"><div className="text-xs text-stone-500">{k}</div><div className="text-xl font-bold tabular-nums">{v}</div><div className="text-xs text-stone-500">{n}</div></div>))}
      </div>
      <p className="text-xs text-stone-500 mt-4">These weights were chosen using this same period, which flatters them. It describes the past and says little about the future.</p>
    </Card>
  );
};

export const AdvisorExtras = ({ r }) => (
  <>
    {r.cash_left != null && <p className="text-sm text-stone-600 rounded-xl bg-brand-50 px-4 py-2.5">Buying whole shares costs {inr(r.invested_in_whole_shares)}. The remaining {inr(r.cash_left)} stays as cash.</p>}
    <GoalCard r={r} />
    <StressTests r={r} />
    <PastRecord r={r} />
  </>
);