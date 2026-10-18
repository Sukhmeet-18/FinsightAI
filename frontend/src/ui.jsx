export const inr = (n) => '₹' + Math.round(n).toLocaleString('en-IN');
export const pct = (n) => (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(1) + '%';
export const EM = '#0B5D45', AMBER = '#B7791F', CORAL = '#C2503D';
export const LABEL = {
  'Strong Buy': { cls: 'bg-brand-100 text-brand-900', icon: '▲▲', col: EM },
  Buy: { cls: 'bg-brand-50 text-brand-800', icon: '▲', col: EM },
  Hold: { cls: 'bg-gold-100 text-gold-900', icon: '■', col: AMBER },
  Sell: { cls: 'bg-coral-100 text-coral-900', icon: '▼', col: CORAL },
};
export const LEVEL = { Low: ['bg-brand-50 text-brand-800', '✓'], Medium: ['bg-gold-100 text-gold-900', '!'], High: ['bg-coral-100 text-coral-900', '▼'] };

/* ---------- primitives ---------- */
export const Card = ({ className = '', children, ...p }) => <div className={'bg-white rounded-2xl shadow-[0_1px_2px_rgba(60,50,30,.05),0_8px_24px_-12px_rgba(60,50,30,.12)] ' + className} {...p}>{children}</div>;
export const Skel = ({ className = '' }) => <div className={'animate-pulse bg-stone-200/70 ' + (/rounded/.test(className) ? '' : 'rounded-lg ') + className} />;
export const Tip = ({ term, tip }) => (
  <span className="relative group inline-block">
    <button type="button" className="underline decoration-dotted underline-offset-4 decoration-stone-400 cursor-help focus:outline-none focus-visible:ring-2 ring-brand-600 rounded">{term}</button>
    <span role="tooltip" className="pointer-events-none absolute z-30 left-1/2 -translate-x-1/2 bottom-full mb-2 w-52 rounded-xl bg-stone-900 text-white text-xs leading-snug px-3 py-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition">{tip}</span>
  </span>
);
export const LabelChip = ({ label }) => { const l = LABEL[label]; return <span className={'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ' + l.cls}><span aria-hidden="true" className="text-[9px]">{l.icon}</span>{label}</span>; };
export const Ring = ({ score, label, size = 64 }) => {
  const r = size / 2 - 5, c = 2 * Math.PI * r, col = LABEL[label].col;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={`FinSight Score ${score} out of 100`}>
      <svg width={size} height={size} className="-rotate-90"><circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#efeae0" strokeWidth="6" /><circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={col} strokeWidth="6" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)} /></svg>
      <div className="absolute inset-0 grid place-items-center tabular-nums font-bold text-stone-900" style={{ fontSize: size * 0.32 }}>{score}</div>
    </div>
  );
};
export const MiniBar = ({ name, value, max, tip, dark }) => {
  const neg = value < 0;
  return (
    <div>
      <div className={'flex justify-between text-xs mb-1 ' + (dark ? 'text-stone-300' : 'text-stone-600')}><span>{tip ? <Tip term={name} tip={tip} /> : name}</span><span className={'tabular-nums font-semibold ' + (neg ? (dark ? 'text-[#ffb4a5]' : 'text-[#b8402e]') : (dark ? 'text-white' : 'text-stone-900'))}>{neg && <span aria-hidden="true">▼ </span>}{pct(value)}</span></div>
      <div className={'h-2 rounded-full overflow-hidden ' + (dark ? 'bg-white/15' : 'bg-stone-100')}><div className="h-full rounded-full" style={{ width: Math.min(100, Math.abs(value) / max * 100) + '%', background: neg ? '#e8907f' : dark ? '#6fd3a8' : EM }} /></div>
    </div>
  );
};
export const Btn = ({ kind = 'primary', className = '', ...p }) => <button {...p} className={'rounded-full px-5 py-2.5 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 ring-offset-2 ring-brand-600 disabled:opacity-40 ' + (kind === 'primary' ? 'bg-brand-700 text-white hover:bg-brand-800 ' : 'bg-white text-stone-800 ring-1 ring-stone-200 hover:bg-stone-50 ') + className} />;