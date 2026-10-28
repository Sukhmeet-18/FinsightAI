// FinSight AI "How it works": a 45-second animation drawn as SVG.
// Nothing here plays by itself. render(t) draws the picture for second t,
// so the page can play, pause and scrub it, and a script can film it frame by frame.

export const DURATION = 45;
export const W = 1280;
export const H = 720;
export const SCENES = [
  { id: 'intro', a: 0, b: 5, title: 'The idea' },
  { id: 'collect', a: 5, b: 13, title: 'Collect the data' },
  { id: 'models', a: 13, b: 22, title: 'Models on the numbers' },
  { id: 'rag', a: 22, b: 31, title: 'Ask the reports' },
  { id: 'say', a: 31, b: 39, title: 'Say vs. Show' },
  { id: 'app', a: 39, b: 45, title: 'One dashboard' },
];

const NS = 'http://www.w3.org/2000/svg';
const C = {
  bg: '#F4EEE3', ink: '#1c1917', mute: '#57534e', dark: '#0E2A24', brand: '#0B5D45', brand2: '#0F7A5A',
  brandLt: '#D3EDE0', gold: '#E8A93A', goldLt: '#FCEBC4', coral: '#E4694F', coralLt: '#FADDD5', line: '#d6cfc2', white: '#ffffff',
};
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const ease = (x) => (x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2);
const prog = (t, a, b) => ease(clamp((t - a) / (b - a)));

function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function wrap(text, max) {
  const out = []; let line = '';
  for (const w of text.split(' ')) {
    if ((line + ' ' + w).trim().length > max) { out.push(line); line = w; } else line = (line + ' ' + w).trim();
  }
  if (line) out.push(line);
  return out;
}
function text(parent, { x, y, s, size = 20, weight = 500, fill = C.ink, anchor = 'start', max, lh = 1.25, serif = false }) {
  const t = el('text', { x, y, 'font-size': size, 'font-weight': weight, fill, 'text-anchor': anchor,
    'font-family': serif ? "'Instrument Serif',Georgia,serif" : "Inter,system-ui,'Segoe UI',Arial,sans-serif" }, parent);
  const lines = max ? wrap(s, max) : [s];
  lines.forEach((ln, i) => { const sp = el('tspan', { x, dy: i === 0 ? 0 : size * lh }, t); sp.textContent = ln; });
}
function length(pts) { let L = 0; for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); return L; }
function pointAt(pts, u) {
  const L = length(pts); let d = u * L;
  for (let i = 1; i < pts.length; i++) {
    const seg = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    if (d <= seg || i === pts.length - 1) { const k = seg ? clamp(d / seg) : 0; return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * k, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * k]; }
    d -= seg;
  }
  return pts[pts.length - 1];
}

export function createScene(svg) {
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = '';
  el('rect', { x: 0, y: 0, width: W, height: H, fill: C.bg }, svg);
  const ups = []; // every update(t) function

  // ---------- building blocks ----------
  const scene = (a, b, title, n) => {
    const g = el('g', {}, svg);
    if (title) {
      const hd = el('g', {}, g);
      el('circle', { cx: 78, cy: 62, r: 22, fill: C.dark }, hd);
      text(hd, { x: 78, y: 70, s: String(n), size: 22, weight: 700, fill: C.gold, anchor: 'middle' });
      text(hd, { x: 114, y: 72, s: title, size: 38, serif: true, fill: C.dark });
    }
    ups.push((t) => {
      const o = Math.min(clamp((t - a) / 0.5), clamp((b - t) / 0.5));
      g.setAttribute('opacity', o.toFixed(3));
      g.setAttribute('display', t >= a - 0.01 && t <= b + 0.01 ? 'inline' : 'none');
    });
    return g;
  };
  const appear = (g, t0, draw) => {
    const e = el('g', {}, g); draw(e);
    ups.push((t) => { const p = prog(t, t0, t0 + 0.6); e.setAttribute('opacity', p.toFixed(3)); e.setAttribute('transform', `translate(0 ${((1 - p) * 14).toFixed(1)})`); });
    return e;
  };
  const box = (g, { x, y, w, h, title, sub, fill = C.white, stroke = C.line, tc = C.dark, t0, size = 24 }) =>
    appear(g, t0, (e) => {
      el('rect', { x, y, width: w, height: h, rx: 16, fill, stroke, 'stroke-width': 2 }, e);
      text(e, { x: x + 18, y: y + (sub ? 38 : h / 2 + 9), s: title, size, weight: 700, fill: tc });
      if (sub) text(e, { x: x + 18, y: y + 70, s: sub, size: 18, weight: 500, fill: C.mute, max: Math.floor((w - 34) / 9.4) });
    });
  const chip = (g, { x, y, s, fill = C.goldLt, color = '#5E3A0A', t0, size = 16, anchor = 'start' }) =>
    appear(g, t0, (e) => {
      const w = s.length * size * 0.56 + 26; const x0 = anchor === 'middle' ? x - w / 2 : x;
      el('rect', { x: x0, y: y - size - 6, width: w, height: size + 18, rx: (size + 18) / 2, fill }, e);
      text(e, { x: x0 + 13, y: y + 1, s, size, weight: 600, fill: color });
    });
  const note = (g, o) => appear(g, o.t0, (e) => text(e, o));
  const arrow = (g, pts, { t0, t1, color = C.brand, dash = false, w = 3 }) => {
    const L = length(pts); const e = el('g', {}, g);
    const path = el('path', { d: 'M' + pts.map((p) => p.join(' ')).join(' L'), fill: 'none', stroke: color, 'stroke-width': w, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-dasharray': dash ? '8 8' : L }, e);
    const last = pts[pts.length - 1], prev = pts[pts.length - 2];
    const ang = Math.atan2(last[1] - prev[1], last[0] - prev[0]) * 180 / Math.PI;
    const head = el('path', { d: 'M-12 -8 L0 0 L-12 8 Z', fill: color, transform: `translate(${last[0]} ${last[1]}) rotate(${ang})` }, e);
    ups.push((t) => {
      const p = prog(t, t0, t1);
      if (!dash) path.setAttribute('stroke-dashoffset', (L * (1 - p)).toFixed(1)); else path.setAttribute('opacity', p.toFixed(3));
      head.setAttribute('opacity', p > 0.97 ? 1 : 0);
    });
  };
  const packets = (g, pts, { t0, t1, n = 3, period = 2.4, color = C.gold, r = 8 }) => {
    const dots = Array.from({ length: n }, () => el('circle', { r, fill: color, stroke: C.white, 'stroke-width': 2 }, g));
    ups.push((t) => dots.forEach((d, i) => {
      if (t < t0 || t > t1) { d.setAttribute('opacity', 0); return; }
      const u = (((t - t0) / period) + i / n) % 1; const [px, py] = pointAt(pts, u);
      d.setAttribute('cx', px.toFixed(1)); d.setAttribute('cy', py.toFixed(1));
      d.setAttribute('opacity', Math.min(1, clamp((t - t0) / 0.4), clamp((t1 - t) / 0.4), u < 0.06 ? u / 0.06 : 1, u > 0.94 ? (1 - u) / 0.06 : 1).toFixed(2));
    }));
  };

  // ---------- 1. the idea (0 to 5 s) ----------
  { const g = scene(0, 5);
    note(g, { t0: 0.1, x: 640, y: 190, s: 'How FinSight AI works', size: 76, serif: true, fill: C.dark, anchor: 'middle' });
    note(g, { t0: 0.7, x: 640, y: 238, s: 'Two kinds of information, one dashboard', size: 26, fill: C.mute, anchor: 'middle' });
    box(g, { x: 170, y: 340, w: 330, h: 130, title: 'Numbers', sub: 'Prices, ratios and yearly results', fill: C.brandLt, stroke: C.brand2, t0: 1.3 });
    box(g, { x: 780, y: 340, w: 330, h: 130, title: 'Words', sub: 'Long annual reports, page by page', fill: C.goldLt, stroke: C.gold, t0: 1.9 });
    arrow(g, [[500, 405], [638, 405]], { t0: 2.5, t1: 3.2 }); arrow(g, [[780, 405], [642, 405]], { t0: 2.5, t1: 3.2, color: C.gold });
    appear(g, 3.2, (e) => { el('circle', { cx: 640, cy: 405, r: 46, fill: C.dark }, e); text(e, { x: 640, y: 414, s: 'AI', size: 26, weight: 800, fill: C.gold, anchor: 'middle' }); });
    arrow(g, [[640, 452], [640, 530]], { t0: 3.7, t1: 4.2 });
    box(g, { x: 470, y: 540, w: 340, h: 70, title: 'One clear dashboard', fill: C.dark, stroke: C.dark, tc: C.white, t0: 4.0 });
  }

  // ---------- 2. collect (5 to 13 s) ----------
  { const g = scene(5, 13, 'Collect the data', 1);
    box(g, { x: 60, y: 150, w: 270, h: 120, title: 'Yahoo Finance', sub: 'Prices and yearly results', fill: C.brandLt, stroke: C.brand2, t0: 5.6 });
    box(g, { x: 470, y: 150, w: 300, h: 120, title: 'data/ files', sub: '150 NSE stocks, saved as CSV', t0: 6.6 });
    box(g, { x: 910, y: 150, w: 300, h: 120, title: 'Live price cards', sub: 'Refresh every 60 s, NSE hours', fill: C.goldLt, stroke: C.gold, t0: 7.6 });
    arrow(g, [[330, 210], [470, 210]], { t0: 6.3, t1: 6.9 }); packets(g, [[330, 210], [470, 210]], { t0: 6.9, t1: 13, n: 2, period: 1.8 });
    arrow(g, [[195, 150], [195, 120], [1060, 120], [1060, 150]], { t0: 7.2, t1: 8.2, dash: true, color: C.gold });
    packets(g, [[195, 150], [195, 120], [1060, 120], [1060, 150]], { t0: 8.3, t1: 13, n: 2, period: 3.2, r: 7 });
    box(g, { x: 60, y: 400, w: 270, h: 120, title: 'Annual report PDFs', sub: 'RELIANCE, TCS, HUL, MARUTI, ITC', fill: C.goldLt, stroke: C.gold, t0: 9.2 });
    box(g, { x: 470, y: 400, w: 300, h: 120, title: 'Read page by page', sub: 'Fix odd symbols, drop page headers', t0: 10.0 });
    box(g, { x: 910, y: 400, w: 300, h: 120, title: 'Clean text + page tags', sub: 'Every passage knows its page', fill: C.brandLt, stroke: C.brand2, t0: 10.8 });
    arrow(g, [[330, 460], [470, 460]], { t0: 9.8, t1: 10.4 }); arrow(g, [[770, 460], [910, 460]], { t0: 10.6, t1: 11.2 });
    packets(g, [[330, 460], [470, 460]], { t0: 10.4, t1: 13, n: 2, period: 1.8, color: C.brand2 });
    note(g, { t0: 11.6, x: 640, y: 580, s: 'Numbers come in as tables. Words come in as pages.', size: 22, fill: C.mute, anchor: 'middle' });
  }

  // ---------- 3. models (13 to 22 s) ----------
  { const g = scene(13, 22, 'Models on the numbers', 2);
    box(g, { x: 60, y: 275, w: 250, h: 120, title: 'data/ files', sub: 'Prices, growth, margin, ROE', fill: C.brandLt, stroke: C.brand2, t0: 13.6 });
    const rows = [[125, 'Risk engine', 'GJR-GARCH forecasts how bumpy a stock will be', 'One-day worst case (95%): about 1.5% for the sample portfolio', 14.4],
      [280, 'Buy / Hold / Sell view', 'Ranks about 150 stocks on growth, margin and ROE', 'Marked experimental: the signal was weak', 16.6],
      [435, 'Robo-advisor', 'Five quiz answers become a portfolio of whole shares', 'Crash replays and the odds of reaching a goal', 18.2]];
    rows.forEach(([y, t, s, out, t0]) => {
      box(g, { x: 430, y, w: 400, h: 120, title: t, sub: s, t0 });
      arrow(g, [[310, 335], [370, 335], [370, y + 60], [430, y + 60]], { t0: t0 - 0.4, t1: t0 + 0.3 });
      packets(g, [[310, 335], [370, 335], [370, y + 60], [430, y + 60]], { t0: t0 + 0.3, t1: 22, n: 2, period: 1.9, r: 7 });
      arrow(g, [[830, y + 60], [880, y + 60]], { t0: t0 + 0.9, t1: t0 + 1.3, color: C.gold });
      appear(g, t0 + 1.2, (e) => { el('rect', { x: 880, y: y + 5, width: 330, height: 110, rx: 14, fill: C.goldLt }, e); text(e, { x: 896, y: y + 40, s: out, size: 19, weight: 600, fill: '#5E3A0A', max: 30 }); });
    });
    note(g, { t0: 20.4, x: 640, y: 596, s: 'Each model was tested honestly, including the results that did not look good.', size: 20, fill: C.mute, anchor: 'middle' });
  }

  // ---------- 4. rag (22 to 31 s) ----------
  { const g = scene(22, 31, 'Ask the reports', 3);
    const X = [60, 356, 652, 948]; const wd = 240;
    chip(g, { x: 60, y: 122, s: 'Once, when a report is added', t0: 22.4 });
    [['PDF report', 'Pages of text', 22.6], ['Chunks', 'About 1,000 characters each', 23.4], ['Embeddings', 'Each chunk becomes a vector', 24.2], ['FAISS index', 'Saved on disk, one per company', 25.0]].forEach(([t, s, t0], i) => {
      box(g, { x: X[i], y: 140, w: wd, h: 110, title: t, sub: s, t0, fill: i === 3 ? C.brandLt : C.white, stroke: i === 3 ? C.brand2 : C.line });
      if (i < 3) { arrow(g, [[X[i] + wd, 195], [X[i + 1], 195]], { t0: t0 + 0.5, t1: t0 + 1.0 }); packets(g, [[X[i] + wd, 195], [X[i + 1], 195]], { t0: t0 + 1.0, t1: 31, n: 1, period: 1.6, r: 6 }); }
    });
    chip(g, { x: 60, y: 352, s: 'Every time you ask', t0: 26.0, fill: C.brandLt, color: C.brand });
    [['Your question', 'Typed on Ask a Report', 26.2], ['Closest 6 passages', 'Found by searching the index', 27.2], ['Language model', 'Groq, told to use only these', 28.2], ['Answer + pages', 'Cites [p. 42] after each claim', 29.2]].forEach(([t, s, t0], i) => {
      box(g, { x: X[i], y: 370, w: wd, h: 110, title: t, sub: s, t0, fill: i === 3 ? C.goldLt : C.white, stroke: i === 3 ? C.gold : C.line });
      if (i < 3) arrow(g, [[X[i] + wd, 425], [X[i + 1], 425]], { t0: t0 + 0.6, t1: t0 + 1.1 });
    });
    arrow(g, [[1068, 250], [1068, 310], [476, 310], [476, 370]], { t0: 27.0, t1: 28.0, dash: true, color: C.brand2 });
    packets(g, [[1068, 250], [1068, 310], [476, 310], [476, 370]], { t0: 28.0, t1: 31, n: 2, period: 2.2, r: 7, color: C.brand2 });
    note(g, { t0: 29.8, x: 640, y: 560, s: 'If the answer is not in the report, it says so instead of guessing.', size: 22, fill: C.mute, anchor: 'middle' });
  }

  // ---------- 5. say vs show (31 to 39 s) ----------
  { const g = scene(31, 39, 'Say vs. Show', 4);
    box(g, { x: 60, y: 110, w: 410, h: 84, title: 'What the report says', sub: 'FinBERT reads about 450 sentences', fill: C.goldLt, stroke: C.gold, t0: 31.6 });
    box(g, { x: 810, y: 110, w: 410, h: 84, title: 'What the numbers show', sub: 'Trend in growth, margin and ROE', fill: C.brandLt, stroke: C.brand2, t0: 32.2 });
    chip(g, { x: 560, y: 138, s: 'Words (tone)', fill: C.gold, color: C.dark, t0: 33.0 });
    chip(g, { x: 560, y: 176, s: 'Numbers (trend)', fill: C.brand2, color: C.white, t0: 33.0 });
    const names = ['HUL', 'ITC', 'Maruti', 'Reliance', 'TCS']; const tone = [1.11, -0.19, 1.16, -0.72, -1.37]; const tr = [-0.83, 1.26, 0.87, -1.40, 0.10];
    const gap = ['1.94', '-1.45', '0.29', '0.68', '-1.47']; const verdict = ['Says more than it shows', 'Shows more than it says', 'Consistent', 'Consistent', 'Shows more than it says'];
    const base = 392, sc = 72;
    appear(g, 33.2, (e) => { el('line', { x1: 150, x2: 1130, y1: base, y2: base, stroke: C.line, 'stroke-width': 2 }, e); text(e, { x: 142, y: base + 5, s: '0', size: 14, fill: C.mute, anchor: 'end' }); });
    const bars = [];
    names.forEach((n, i) => {
      const cx = 250 + i * 195;
      [[tone[i], cx - 52, C.gold], [tr[i], cx + 6, C.brand2]].forEach(([v, bx, col], k) => {
        const r = el('rect', { x: bx, y: base, width: 46, height: 0, rx: 4, fill: col }, g); bars.push([r, v, 34.0 + i * 0.35 + k * 0.1]);
      });
      appear(g, 34.0 + i * 0.35, (e) => text(e, { x: cx, y: 530, s: n, size: 20, weight: 700, fill: C.dark, anchor: 'middle' }));
      appear(g, 36.2 + i * 0.3, (e) => {
        const flag = verdict[i] !== 'Consistent'; el('rect', { x: cx - 88, y: 548, width: 176, height: 46, rx: 12, fill: flag ? C.coralLt : C.brandLt }, e);
        text(e, { x: cx, y: 566, s: 'gap ' + gap[i], size: 16, weight: 700, fill: flag ? '#8F3526' : C.brand, anchor: 'middle' });
        text(e, { x: cx, y: 585, s: verdict[i], size: 14, weight: 600, fill: flag ? '#8F3526' : C.brand, anchor: 'middle' });
      });
    });
    ups.push((t) => bars.forEach(([r, v, t0]) => { const p = prog(t, t0, t0 + 0.9); const hh = Math.abs(v) * sc * p; r.setAttribute('height', hh.toFixed(1)); r.setAttribute('y', (v >= 0 ? base - hh : base).toFixed(1)); }));
    note(g, { t0: 37.4, x: 640, y: 255, s: 'Compared across the five companies, so results are relative', size: 18, fill: C.mute, anchor: 'middle' });
  }

  // ---------- 6. one dashboard (39 to 45 s) ----------
  { const g = scene(39, 45, 'One dashboard', 5);
    appear(g, 39.5, (e) => { el('rect', { x: 480, y: 285, width: 320, height: 120, rx: 18, fill: C.dark }, e); text(e, { x: 640, y: 337, s: 'FastAPI backend', size: 28, weight: 700, fill: C.white, anchor: 'middle' }); text(e, { x: 640, y: 373, s: 'one server, every model', size: 18, fill: C.gold, anchor: 'middle' }); });
    [[60, 115, 'Companies', 'Live price, score, model view', 40.0], [880, 115, 'Portfolio Advisor', 'Portfolio, crash replays, goal odds', 40.4], [60, 450, 'Ask a Report', 'Answers with page citations', 40.8], [880, 450, 'Say vs. Show', 'Where words and numbers disagree', 41.2]].forEach(([x, y, t, s, t0], i) => {
      box(g, { x, y, w: 340, h: 120, title: t, sub: s, t0, fill: i % 2 ? C.goldLt : C.brandLt, stroke: i % 2 ? C.gold : C.brand2 });
      const left = x < 400, top = y < 300, ex = left ? 500 : 780, ey = top ? 175 : 510;
      const pts = [[ex, top ? 285 : 405], [ex, ey], [left ? 400 : 880, ey]];
      arrow(g, pts, { t0: t0 + 0.5, t1: t0 + 1.1, color: C.gold });
      packets(g, pts, { t0: t0 + 1.2, t1: 45, n: 1, period: 2.0, r: 7 });
    });
    note(g, { t0: 42.4, x: 640, y: 596, s: 'An educational tool, not investment advice.', size: 28, serif: true, fill: C.dark, anchor: 'middle' });
  }

  // ---------- captions and progress ----------
  const CAPS = [
    [0, 5, 'Investing needs two kinds of information: numbers and words. FinSight AI puts both in one place.'],
    [5, 9, 'First, data comes in. Prices and yearly results are pulled from Yahoo Finance for about 150 NSE stocks.'],
    [9, 13, 'Five annual report PDFs are read page by page, so every answer can point back to a page.'],
    [13, 17.5, 'The numbers feed three models. A risk engine forecasts how bumpy each stock is likely to be.'],
    [17.5, 22, 'A Buy, Hold or Sell view, marked experimental, and a robo-advisor that turns five quiz answers into a portfolio.'],
    [22, 26, 'For the words, each report is cut into chunks, turned into vectors and saved in a search index.'],
    [26, 31, 'A question finds its six closest passages. The language model answers only from them and cites the page.'],
    [31, 35, 'Say vs. Show reads the tone of each report with FinBERT and compares it with the trend in the numbers.'],
    [35, 39, 'A big gap flags a company whose words and numbers disagree. These flags are relative and not yet validated.'],
    [39, 45, 'One backend serves four screens. Everything is explained, and nothing here is investment advice.'],
  ];
  const cap = el('g', {}, svg);
  el('rect', { x: 60, y: 626, width: 1160, height: 70, rx: 16, fill: C.dark }, cap);
  const capText = el('text', { x: 90, y: 653, 'font-size': 22, 'font-weight': 500, fill: C.white, 'font-family': "Inter,system-ui,'Segoe UI',Arial,sans-serif" }, cap);
  el('rect', { x: 0, y: 714, width: W, height: 6, fill: C.line }, svg);
  const bar = el('rect', { x: 0, y: 714, width: 0, height: 6, fill: C.brand2 }, svg);
  let lastCap = -1;
  ups.push((t) => {
    const i = CAPS.findIndex(([a, b]) => t >= a && t < b + (b === DURATION ? 1 : 0)); const k = i < 0 ? CAPS.length - 1 : i;
    if (k !== lastCap) { lastCap = k; capText.innerHTML = ''; wrap(CAPS[k][2], Math.ceil(CAPS[k][2].length / Math.ceil(CAPS[k][2].length / 92)) + 6).forEach((ln, j) => { const sp = el('tspan', { x: 90, dy: j ? 28 : 0 }, capText); sp.textContent = ln; }); }
    const c = CAPS[k]; const o = Math.min(clamp((t - c[0]) / 0.3), clamp((c[1] - t) / 0.3));
    capText.setAttribute('opacity', o.toFixed(2)); bar.setAttribute('width', (W * clamp(t / DURATION)).toFixed(1));
  });

  return { render: (t) => ups.forEach((u) => u(t)) };
}
