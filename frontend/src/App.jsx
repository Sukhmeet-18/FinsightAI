import { useState } from 'react';
import Companies from './screens/Companies';
import Advisor from './screens/Advisor';
import Ask from './screens/Ask';
import SayShow from './screens/SayShow';
import HowItWorks from './screens/HowItWorks';

const TABS = [['companies', 'Companies', '◔'], ['advisor', 'Portfolio Advisor', '◐'], ['ask', 'Ask a Report', '❡'], ['say', 'Say vs. Show', '≋'], ['how', 'How it works', '▶']];
const FinSightApp = () => {
  const [tab, setTab] = useState('companies');
  const [askCo, setAskCo] = useState(null);
  const go = (t) => { setTab(t); window.scrollTo(0, 0); };
  return (
    <div className="min-h-screen bg-[#F4EEE3] text-stone-900 antialiased pb-24 lg:pb-0" style={{ fontFamily: "'Inter',system-ui,sans-serif", fontVariantNumeric: 'tabular-nums' }}>
      <header className="sticky top-0 z-40 bg-[#F4EEE3]/90 backdrop-blur border-b border-stone-200/70">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5 font-bold text-lg"><span className="h-8 w-8 rounded-xl bg-[#0E2A24] text-gold-400 grid place-items-center text-sm" aria-hidden="true">F</span>FinSight <span className="text-brand-700 -ml-1.5">AI</span></div>
          <nav aria-label="Main" className="hidden lg:flex gap-1 rounded-full bg-white p-1 ring-1 ring-stone-200">{TABS.map(([k, l]) => <button key={k} onClick={() => go(k)} aria-current={tab === k ? 'page' : undefined} className={'whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-semibold transition ' + (tab === k ? 'bg-[#0E2A24] text-white' : 'text-stone-700 hover:bg-stone-100')}>{l}</button>)}</nav>
          <div className="flex items-center gap-3 text-xs"><span className="hidden sm:inline-flex whitespace-nowrap items-center gap-1.5 rounded-full bg-gold-100 text-gold-900 px-3 py-1.5 font-medium"><span aria-hidden="true">ⓘ</span><span className="hidden lg:inline">Educational tool, not financial advice</span><span className="lg:hidden">Not financial advice</span></span><span className="text-stone-600 hidden xl:inline whitespace-nowrap">Data as of 1 Oct 2026</span></div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        {tab === 'companies' && <Companies onAsk={(id) => { setAskCo(id); go('ask'); }} />}
        {tab === 'advisor' && <Advisor />}
        {tab === 'ask' && <Ask initial={askCo} />}
        {tab === 'say' && <SayShow />}
        {tab === 'how' && <HowItWorks />}
      </main>
      <footer className="max-w-6xl mx-auto px-4 sm:px-6 pb-10 text-xs text-stone-500 leading-relaxed border-t border-stone-200/70 pt-6">FinSight AI is an educational tool and does not give financial advice. Backtested results are not guarantees of future returns. AI answers can be wrong, so check the source before you act. Data as of 1 Oct 2026.</footer>
      <nav aria-label="Main" className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t border-stone-200 grid grid-cols-5 pb-[env(safe-area-inset-bottom)]">{TABS.map(([k, l, i]) => <button key={k} onClick={() => go(k)} aria-current={tab === k ? 'page' : undefined} className={'min-h-[60px] flex flex-col items-center justify-center gap-0.5 text-[11px] font-semibold ' + (tab === k ? 'text-brand-800' : 'text-stone-600')}><span aria-hidden="true" className={'text-lg leading-none px-4 py-1 rounded-full ' + (tab === k ? 'bg-brand-100' : '')}>{i}</span>{l.replace('Portfolio ', '').replace('How it works', 'How')}</button>)}</nav>
    </div>
  );
};

export default FinSightApp;