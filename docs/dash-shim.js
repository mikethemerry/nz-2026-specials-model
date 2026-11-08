/*
 * Minimal stand-in for the dashboard runtime, so the page runs as a static site
 * (e.g. GitHub Pages). It implements the small part of the `dash` API that
 * app.js uses:
 *
 *   dash.data(id)        -> {status, data}; loads data/<id>.json on first use
 *   dash.draw(name, fn)  -> runs fn(el) on every [data-draw=name] element,
 *                           again whenever data arrives or the window resizes
 *   dash.colors          -> the series colours
 *
 * Every number on the page is drawn from data/*.json; nothing is hard-coded.
 */
(function () {
  const cache = {};
  const draws = {};
  let pending = false;

  const colors = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948'];

  function schedule() {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => { pending = false; run(); });
  }

  function data(id) {
    if (!cache[id]) {
      cache[id] = { status: 'loading', data: [] };
      fetch(`data/${id}.json`)
        .then((r) => { if (!r.ok) throw new Error(`${r.status} loading data/${id}.json`); return r.json(); })
        .then((d) => { cache[id] = { status: 'ok', data: d, columns: Array.isArray(d) && d.length ? Object.keys(d[0]) : [] }; schedule(); })
        .catch((e) => { cache[id] = { status: 'error', data: [], message: String(e) }; console.error(e); schedule(); });
    }
    return cache[id];
  }

  function stamp() {
    document.querySelectorAll('[data-source]').forEach((el) => {
      const ids = el.dataset.source.split(/\s+/);
      const st = ids.map((id) => (cache[id] || {}).status);
      el.dataset.dashSourceState = st.includes('error') ? 'error' : st.every((s) => s === 'ok') ? 'ok' : 'loading';
    });
  }

  function run() {
    for (const [name, fn] of Object.entries(draws)) {
      document.querySelectorAll(`[data-draw="${name}"]`).forEach((el) => {
        try { fn(el); } catch (e) { console.error(`draw ${name}`, e); }
      });
    }
    stamp();
  }

  function draw(name, fn) {
    draws[name] = typeof fn === 'function' ? fn : (fn && fn.update) || (() => {});
    schedule();
  }

  // start every dataset the page names loading straight away
  document.querySelectorAll('[data-source]').forEach((el) => el.dataset.source.split(/\s+/).forEach(data));
  window.addEventListener('resize', schedule);

  window.dash = { data, draw, colors, onData: (fn) => { fn(); }, params: () => ({}), setParams: () => {}, setLink: () => {} };
})();
