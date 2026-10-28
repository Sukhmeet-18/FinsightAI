import { COMPANIES } from './data';

export const API = 'http://127.0.0.1:8000';

// Takes the live numbers from the backend and puts them into the design's company cards.
// Text like "why this score" and the risk tags are still sample content.
export async function fetchCompanies() {
  const res = await fetch(`${API}/companies/overview`);
  if (!res.ok) throw new Error('Backend returned ' + res.status);
  const live = await res.json();
  return COMPANIES.map((c) => {
    const l = live.find((x) => x.ticker === c.ticker + '.NS');
    if (!l) return c;
    return {
      ...c,
      price: l.current_price,
      rev: l.revenue_growth * 100,
      margin: l.profit_margin * 100,
      roe: l.roe * 100,
      score: l.score,
      label: l.label,
      mv: l.model,
      fetchedAt: l.fetched_at
    };
  }).sort((a, b) => b.score - a.score);
}

// Sends the 5 quiz answers (each 1-4) and the amount; returns the built portfolio.
export async function buildPortfolio(answers, capital, goal) {
  let res;
  try {
    res = await fetch(`${API}/portfolio/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ capital, risk_answers: answers, ...(goal || {}) }),
    });
  } catch {
    throw new Error("Can't reach the backend. Is uvicorn running on port 8000?");
  }
  if (!res.ok) {
    let msg = 'The backend returned an error (' + res.status + ').';
    try {
      const j = await res.json();
      if (typeof j.detail === 'string') msg = j.detail;
      else if (Array.isArray(j.detail)) msg = 'Some of your inputs were not accepted. Please check them and try again.';
    } catch { /* plain-text error, keep default */ }
    throw new Error(msg);
  }
  return res.json();
}

// Say vs. Show results for every company (computed offline by scripts/run_detector.py).
export async function fetchDetector() {
  let res;
  try {
    res = await fetch(`${API}/detector/summary`);
  } catch {
    throw new Error("Can't reach the backend. Is uvicorn running on port 8000?");
  }
  if (!res.ok) {
    let msg = 'The backend returned an error (' + res.status + ').';
    try {
      const j = await res.json();
      if (typeof j.detail === 'string') msg = j.detail;
    } catch { /* plain-text error, keep default */ }
    throw new Error(msg);
  }
  return res.json();
}

// Ask a question about one company's annual report. Returns { answer, found, sources, unverified_pages, ... }.
export async function askReport(ticker, question) {
  let res;
  try {
    res = await fetch(`${API}/rag/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticker, question }),
    });
  } catch {
    throw new Error("Can't reach the backend. Is uvicorn running on port 8000?");
  }
  if (!res.ok) {
    let msg = 'The backend returned an error (' + res.status + ').';
    try {
      const j = await res.json();
      if (typeof j.detail === 'string') msg = j.detail;
      else if (Array.isArray(j.detail)) msg = 'Please type a question and pick a company.';
    } catch { /* plain-text error, keep default */ }
    throw new Error(msg);
  }
  return res.json();
}