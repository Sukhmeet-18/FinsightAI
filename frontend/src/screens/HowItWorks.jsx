import { useEffect, useRef, useState } from 'react';
import { createScene, DURATION, SCENES } from '../howitworks/scene';

const clock = (t) => '0:' + String(Math.min(DURATION, Math.floor(t))).padStart(2, '0');

const STEPS = [
  ['1', 'Collect the data', 'Prices and yearly results for about 150 NSE stocks come from Yahoo Finance and are saved as files. The five dashboard stocks are also fetched live, and the cards refresh every 60 seconds while the NSE is open. Five annual report PDFs are read page by page, with odd symbols repaired and page headers removed.', 'finsight_fetch_data.py, backend/rag/ingest.py'],
  ['2', 'Models on the numbers', 'A GJR-GARCH risk engine forecasts volatility, VaR and CVaR. A classifier ranks stocks into Buy, Hold or Sell, but its signal was weak and changed from year to year, so it is marked experimental. The robo-advisor turns five quiz answers into a portfolio of whole shares and explains it with crash replays and the odds of reaching a goal.', 'backend/risk_model, backend/classifier, backend/robo_advisor'],
  ['3', 'Ask the reports', 'Each report is cut into chunks of about 1,000 characters, turned into vectors and saved in a FAISS index. A question finds its six closest passages, and a language model (Groq) is told to answer only from them and to cite the page. If the answer is not there, it says so.', 'backend/rag'],
  ['4', 'Say vs. Show', 'FinBERT scores the tone of about 450 sentences from each report. That is compared with the trend in growth, margin and ROE. Both are converted to scores relative to the five companies, and a gap beyond 1.0 is flagged. There are no labelled examples yet, so this is an exploratory check and not a measured accuracy.', 'backend/detector'],
  ['5', 'One dashboard', 'A single FastAPI backend serves four screens: Companies, Portfolio Advisor, Ask a Report and Say vs. Show.', 'main.py'],
];

export default function HowItWorks() {
  const svgRef = useRef(null);
  const sceneRef = useRef(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(() => !(typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches));
  const [hasVideo, setHasVideo] = useState(false);

  useEffect(() => {
    sceneRef.current = createScene(svgRef.current);
    sceneRef.current.render(0);
  }, []);
  useEffect(() => { if (sceneRef.current) sceneRef.current.render(t); }, [t]);
  useEffect(() => {
    if (!playing) return undefined;
    let raf; let last = performance.now();
    const tick = (now) => {
      const dt = (now - last) / 1000; last = now;
      setT((p) => (p + dt >= DURATION ? 0 : p + dt));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing]);
  useEffect(() => {
    // The MP4 is optional: the button only shows if the file is in frontend/public.
    fetch('/how-it-works.mp4', { method: 'HEAD' })
      .then((r) => setHasVideo(r.ok && (r.headers.get('content-type') || '').includes('video')))
      .catch(() => setHasVideo(false));
  }, []);

  const current = SCENES.findLast ? SCENES.findLast((s) => t >= s.a) : SCENES[0];
  const jump = (s) => { setT(s.a + 0.05); };

  return (
    <div>
      <div className="max-w-3xl">
        <h1 className="text-3xl sm:text-4xl text-stone-900" style={{ fontFamily: 'var(--font-display)' }}>How it works</h1>
        <p className="mt-3 text-stone-700 leading-relaxed">A 45-second walk through how data moves through FinSight AI, from Yahoo Finance and annual reports to the four screens you use. Press play, drag the bar, or jump to a step.</p>
      </div>

      <div className="mt-6 rounded-2xl bg-white p-2 sm:p-3 ring-1 ring-stone-200">
        <svg ref={svgRef} role="img" aria-label="Animated diagram of how FinSight AI collects data, runs its models, answers questions from annual reports, compares tone with numbers and serves the dashboard" className="block w-full h-auto rounded-xl" />
        <div className="mt-3 flex flex-wrap items-center gap-3 px-1 pb-1">
          <button onClick={() => { if (t >= DURATION - 0.1) setT(0); setPlaying((p) => !p); }} className="min-h-[44px] rounded-full bg-[#0E2A24] px-5 text-sm font-semibold text-white hover:bg-brand-800" aria-label={playing ? 'Pause animation' : 'Play animation'}>{playing ? 'Pause' : 'Play'}</button>
          <input type="range" min="0" max={DURATION} step="0.05" value={t} onChange={(e) => { setPlaying(false); setT(Number(e.target.value)); }} aria-label="Position in the animation" aria-valuetext={clock(t) + ' of ' + clock(DURATION)} className="flex-1 min-w-[160px] accent-[#0B5D45]" />
          <span className="text-sm text-stone-600 tabular-nums w-20 text-right">{clock(t)} / {clock(DURATION)}</span>
          {hasVideo && <a href="/how-it-works.mp4" download className="min-h-[44px] inline-flex items-center rounded-full ring-1 ring-stone-300 px-4 text-sm font-semibold text-stone-800 hover:bg-stone-50">Download video</a>}
        </div>
        <div className="flex flex-wrap gap-2 px-1 pb-2">
          {SCENES.map((s) => <button key={s.id} onClick={() => jump(s)} aria-current={current && current.id === s.id ? 'step' : undefined} className={'rounded-full px-3 py-1.5 text-xs font-semibold transition ' + (current && current.id === s.id ? 'bg-brand-100 text-brand-800 ring-1 ring-brand-600' : 'bg-stone-100 text-stone-700 hover:bg-stone-200')}>{clock(s.a)} {s.title}</button>)}
        </div>
      </div>

      <h2 className="mt-10 text-2xl text-stone-900" style={{ fontFamily: 'var(--font-display)' }}>What happens at each step</h2>
      <ol className="mt-4 grid gap-4 md:grid-cols-2">
        {STEPS.map(([n, title, body, where]) => (
          <li key={n} className="rounded-2xl bg-white p-5 ring-1 ring-stone-200">
            <div className="flex items-center gap-3"><span className="h-8 w-8 rounded-full bg-[#0E2A24] text-gold-400 grid place-items-center text-sm font-bold" aria-hidden="true">{n}</span><h3 className="font-bold text-stone-900">{title}</h3></div>
            <p className="mt-3 text-sm leading-relaxed text-stone-700">{body}</p>
            <p className="mt-3 text-xs text-stone-500">In the code: <code className="rounded bg-stone-100 px-1.5 py-0.5">{where}</code></p>
          </li>
        ))}
      </ol>
      <p className="mt-6 text-xs text-stone-500 leading-relaxed max-w-3xl">The animation is a simplified picture. The numbers in it (the one-day worst case of about 1.5% and the Say vs. Show gaps) come from our own runs on the sample portfolio and the five reports, and they are not predictions.</p>
    </div>
  );
}
