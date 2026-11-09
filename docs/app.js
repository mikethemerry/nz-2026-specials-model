window.NZ = (() => {
  const C = dash.colors;
  // Party colours, used throughout: scenarios take the colour of the party they turn on.
  const PARTY = {NAT: '#2a78d6', LAB: '#e34948', GP: '#008300', ACT: '#eda100', NZF: '#444441', OPP: '#7f3fbf', TPM: '#8a2b4a', OTH: '#888780', IND: '#888780'};
  const PNAME = {NAT: 'National', LAB: 'Labour', GP: 'Green', ACT: 'ACT', NZF: 'NZ First', OPP: 'Opportunity', TPM: 'Te Pāti Māori'};
  const sc = {alone: PARTY.NAT, nat_needs_opp: PARTY.OPP, labour: PARTY.LAB};
  const scName = {alone: 'Coalition alone', nat_needs_opp: 'National needs Opportunity', labour: 'Labour could form a government'};
  const scLong = {alone: 'Coalition governs alone', nat_needs_opp: 'National needs Opportunity', labour: 'Labour could form a government'};
  const fmt = {
    pct0: (v) => (v > 0 && v < 0.5 ? '<1' : d3.format('.0f')(v)) + '%',
    pct1: (v) => d3.format('.1f')(v) + '%',
    pct2: (v) => d3.format('.2f')(v) + '%',
    int: d3.format(','),
    pp: (v) => (v > 0 ? '+' : v < 0 ? '−' : '') + d3.format('.2f')(Math.abs(v)) + ' pts',
    k: (v) => d3.format('.0f')(v * 100) + '%',
    pp1: (v) => (v > 0 ? '+' : v < 0 ? '−' : '') + d3.format('.1f')(Math.abs(v)) + ' pts',
    pts1: (v) => d3.format('.1f')(v) + ' pts',
    raw: (v) => String(v)
  };
  // Whole-number shares that add up: largest-remainder rounding of a group of
  // percentages to integers summing to round(total). A share that is above zero
  // but rounds to 0 shows as "<1%".
  const lr0 = (vals) => {
    const tot = Math.round(vals.reduce((a, b) => a + (b || 0), 0));
    const fl = vals.map((v) => Math.floor((v || 0) + 1e-9));
    let left = tot - fl.reduce((a, b) => a + b, 0);
    vals.map((v, i) => [(v || 0) - fl[i], i]).sort((a, b) => b[0] - a[0] || a[1] - b[1])
      .forEach(([, i]) => { if (left > 0) { fl[i] += 1; left -= 1; } });
    return fl;
  };
  const show0 = (orig, v) => (orig > 0 && v === 0 ? '<1' : String(v)) + '%';
  const SK = ['alone', 'nat_needs_opp', 'labour'];
  // Integer scenario shares for a row holding alone / nat_needs_opp / labour (+ opp_pivotal = the other two)
  const trip = (r) => { const w = lr0(SK.map((k) => r[k])); const o = {}; SK.forEach((k, i) => { o[k] = w[i]; }); o.opp_pivotal = w[1] + w[2]; return o; };
  const w = (r, k) => show0(r[k], trip(r)[k]);
  const tip = (box) => {
    let t = box.querySelector(':scope > .tip');
    if (!t) { t = document.createElement('div'); t.className = 'tip'; t.hidden = true; box.appendChild(t); }
    return {
      show(ev, head, lines) {
        t.replaceChildren();
        const h = document.createElement('div'); h.className = 'h'; h.textContent = head; t.appendChild(h);
        lines.forEach(([c, s]) => { const d = document.createElement('div'); if (c) { const i = document.createElement('i'); i.className = 'sw'; i.style.background = c; i.style.marginRight = '6px'; d.appendChild(i); } d.appendChild(document.createTextNode(s)); t.appendChild(d); });
        t.hidden = false;
        const r = box.getBoundingClientRect();
        let x = ev.clientX - r.left + 12; const y = ev.clientY - r.top + 12;
        const w = t.offsetWidth; if (x + w > r.width) x = Math.max(0, ev.clientX - r.left - w - 12);
        t.style.left = x + 'px'; t.style.top = y + 'px';
      },
      hide() { t.hidden = true; }
    };
  };
  const ok = (...ids) => ids.every((id) => dash.data(id).status === 'ok');
  const muted = getComputedStyle(document.documentElement).getPropertyValue('--cds-chart-muted').trim() || '#b4b2a9';
  const svgIn = (el, h) => {
    const w = Math.max(280, el.clientWidth || 600);
    el.querySelectorAll('svg').forEach((s) => s.remove());
    const svg = d3.select(el).insert('svg', ':first-child').attr('width', '100%').attr('viewBox', `0 0 ${w} ${h}`).attr('font-family', 'var(--font-anthropic-sans)').attr('font-size', 12);
    return [svg, w];
  };
  const clear = (el) => el.querySelectorAll('svg').forEach((s) => s.remove());
  const rowsTable = (tb, id, cols) => {
    tb.replaceChildren();
    if (!ok(id)) return;
    dash.data(id).data.forEach((r) => {
      const tr = document.createElement('tr');
      if (r.id !== undefined) tr.dataset.key = r.id;
      cols.forEach(([f, cls]) => { const td = document.createElement('td'); if (cls) td.className = cls; const v = f(r); if (v instanceof Node) td.appendChild(v); else td.textContent = v; tr.appendChild(td); });
      tb.appendChild(tr);
    });
  };
  const barCell = (v, max, col) => {
    const s = document.createElement('span');
    const b = document.createElement('span'); b.className = 'bar'; b.style.width = Math.max(2, (v / max) * 70) + 'px'; b.style.background = col; s.appendChild(b);
    s.appendChild(document.createTextNode(fmt.pct0(v)));
    return s;
  };
  return {sc, scName, scLong, fmt, tip, ok, muted, svgIn, clear, rowsTable, barCell, lr0, show0, trip, w, SK, PARTY, PNAME};
})();
document.querySelectorAll('[data-sc]').forEach((e) => { e.style.background = NZ.sc[e.dataset.sc]; });
document.querySelectorAll('[data-c]').forEach((e) => { e.style.background = e.dataset.c === 'muted' ? NZ.muted : dash.colors[0]; });

dash.draw('v', (el) => {
  const d = dash.data(el.dataset.source);
  if (d.status !== 'ok') { el.textContent = '—'; return; }
  let row;
  if (el.dataset.where) {
    const conds = el.dataset.where.split('&').map((p) => p.split('=').map(decodeURIComponent));
    row = d.data.find((r) => conds.every(([k, v]) => String(r[k]) === v));
  } else row = d.data[+(el.dataset.row || 0)];
  const f = el.dataset.field;
  const v = row ? row[f] : undefined;
  if (v !== undefined && v !== null && el.dataset.fmt === 'pct0') {
    // Shares shown together must add to 100: round the whole group, not each figure alone.
    if (el.dataset.source === 'scenarios' && NZ.SK.concat('opp_pivotal').includes(row.scenario)) {
      const all = {}; d.data.forEach((r) => { all[r.scenario] = r.pct; });
      el.textContent = NZ.show0(v, NZ.trip(all)[row.scenario]); return;
    }
    if (NZ.SK.concat('opp_pivotal').includes(f) && NZ.SK.every((k) => typeof row[k] === 'number')) {
      el.textContent = NZ.show0(v, NZ.trip(row)[f]); return;
    }
  }
  el.textContent = v === undefined || v === null ? '—' : NZ.fmt[el.dataset.fmt || 'raw'](v);
});

dash.draw('grid', (el) => {
  el.replaceChildren();
  if (!NZ.ok('grid')) return;
  const rows = dash.data('grid').data; const cols = [12, 11]; const keys = ['alone', 'nat_needs_opp', 'labour'];
  const rlab = [...new Map(rows.map((r) => [r.seat_order, r.seats])).entries()].sort((a, b) => a[0] - b[0]);
  const pw = NZ.lr0(rows.map((r) => r.p_runs)); const pRun = new Map(rows.map((r, i) => [r, NZ.show0(r.p_runs, pw[i])]));
  const g = document.createElement('div'); g.className = 'sg';
  const add = (cls, t) => { const d = document.createElement('div'); d.className = cls; if (t) d.textContent = t; g.appendChild(d); return d; };
  add('sg-h', ''); cols.forEach((z) => { const r = rows.find((x) => x.nzf_seats === z); add('sg-h', r ? r.nzf : ''); });
  rlab.forEach(([o, lab]) => {
    add('sg-r', lab);
    cols.forEach((z) => {
      const r = rows.find((x) => x.seat_order === o && x.nzf_seats === z); const c = add('sg-c'); if (!r) return;
      const p = document.createElement('div'); p.className = 'sg-p'; p.textContent = pRun.get(r);
      const s = document.createElement('small'); s.textContent = 'of runs'; p.appendChild(s); c.appendChild(p);
      const b = document.createElement('div'); b.className = 'sg-b';
      keys.forEach((k) => { if (r[k] <= 0) return; const sp = document.createElement('span'); sp.style.flex = String(r[k]); sp.style.background = NZ.sc[k]; b.appendChild(sp); });
      c.appendChild(b);
      const l = document.createElement('div'); l.className = 'sg-l';
      keys.forEach((k) => { if (r[k] <= 0) return; const ln = document.createElement('div'); const i = document.createElement('i'); i.className = 'sw'; i.style.background = NZ.sc[k]; ln.appendChild(i); ln.appendChild(document.createTextNode(`${NZ.scName[k]} ${NZ.w(r, k)}`)); l.appendChild(ln); });
      c.appendChild(l);
    });
  });
  el.appendChild(g);
});

dash.draw('keyseats', (tb) => NZ.rowsTable(tb, 'key_seats', [
  [(r) => r.seat], [(r) => r.leader], [(r) => d3.format(',')(r.margin), 'n'], [(r) => r.flips_to],
  [(r) => NZ.barCell(r.flip_pct, 100, dash.colors[0])], [(r) => NZ.fmt.pct0(r.flip_pct_he8000), 'n'], [(r) => r.effect]]));

dash.draw('paths', (el) => {
  el.replaceChildren();
  if (!NZ.ok('paths', 'scenarios')) return;
  const rows = dash.data('paths').data;
  const tot = new Map(dash.data('scenarios').data.map((r) => [r.scenario, r.pct]));
  const mx = d3.max(rows, (r) => r.pct);
  ['alone', 'nat_needs_opp', 'labour'].forEach((k) => {
    const g = document.createElement('div'); g.className = 'pg';
    const h = document.createElement('div'); h.className = 'pg-h';
    const sw = document.createElement('i'); sw.className = 'sw'; sw.style.background = NZ.sc[k]; sw.style.marginRight = '6px'; h.appendChild(sw);
    h.appendChild(document.createTextNode(`${NZ.scLong[k]}: ${NZ.fmt.pct1(tot.get(k))} of runs`)); g.appendChild(h);
    rows.filter((r) => r.scenario === k).forEach((r) => {
      const row = document.createElement('div'); row.className = 'pg-r';
      const lab = document.createElement('div'); lab.className = 'pg-l';
      lab.textContent = r.path; if (r.coalition != null) { const s = document.createElement('span'); s.className = 'def'; s.textContent = `  ${r.coalition} of ${r.house}`; lab.appendChild(s); }
      const bw = document.createElement('div'); bw.className = 'pg-bw';
      const b = document.createElement('span'); b.className = 'pg-b'; b.style.width = (r.pct / mx) * 100 + '%'; b.style.background = NZ.sc[k]; bw.appendChild(b);
      const v = document.createElement('div'); v.className = 'pg-v'; v.textContent = NZ.fmt.pct1(r.pct);
      row.append(lab, bw, v); g.appendChild(row);
    });
    el.appendChild(g);
  });
});

dash.draw('swt', (tb) => { const sg = (v) => (v > 0 ? '+' + v : v < 0 ? '−' + Math.abs(v) : '0'); NZ.rowsTable(tb, 'switches', [[(r) => r.switch], [(r) => sg(r.coalition_change), 'n'], [(r) => sg(r.house_change), 'n'], [(r) => NZ.fmt.pct0(r.p), 'n']]); });

dash.draw('oppnat', (tb) => {
  const d = dash.data('opp_by_nat'); const rows = d.status === 'ok' ? d.data : [];
  const pw = NZ.lr0(rows.map((r) => r.p_runs)); const pRun = new Map(rows.map((r, i) => [r, NZ.show0(r.p_runs, pw[i])]));
  NZ.rowsTable(tb, 'opp_by_nat', [[(r) => r.band], [(r) => pRun.get(r) || NZ.fmt.pct0(r.p_runs), 'n'], [(r) => NZ.barCell(r.opp_pivotal, 100, NZ.sc.nat_needs_opp)], [(r) => NZ.fmt.pct0(r.ent_drop), 'n']]);
});

dash.draw('enrol', (el) => {
  if (!NZ.ok('enrolment')) { NZ.clear(el); return; }
  const rows = dash.data('enrolment').data.map((r) => ({...r, d: new Date(r.date)}));
  const h = 230, lm = 40, rm = 54, top = 14, bm = 26;
  const [svg, w] = NZ.svgIn(el, h);
  const x = d3.scaleUtc(d3.extent(rows, (r) => r.d), [lm, w - rm]);
  const y = d3.scaleLinear([60, 76], [h - bm, top]);
  [60, 64, 68, 72, 76].forEach((t) => { svg.append('line').attr('x1', lm).attr('x2', w - rm).attr('y1', y(t)).attr('y2', y(t)).attr('stroke', 'var(--cds-chart-grid)'); svg.append('text').attr('x', lm - 6).attr('y', y(t) + 4).attr('text-anchor', 'end').attr('fill', 'var(--color-fg-muted)').attr('font-size', 11).text(t + '%'); });
  const snap = rows.filter((r) => r.series === 'snapshot'); const first = rows.find((r) => r.series === 'monthly');
  const dl = new Date('2026-10-25');
  svg.append('line').attr('x1', x(dl)).attr('x2', x(dl)).attr('y1', top).attr('y2', h - bm).attr('stroke', 'var(--cds-chart-reference)').attr('stroke-dasharray', '4 3');
  svg.append('text').attr('x', x(dl) - 4).attr('y', top + 10).attr('text-anchor', 'end').attr('fill', 'var(--color-fg-muted)').attr('font-size', 11).text('Enrolment closed');
  if (first) svg.append('line').attr('x1', x(first.d)).attr('y1', y(first.rate_18_24)).attr('x2', x(snap[0].d)).attr('y2', y(snap[0].rate_18_24)).attr('stroke', dash.colors[0]).attr('stroke-width', 2).attr('stroke-dasharray', '3 4');
  svg.append('path').attr('d', d3.line().x((r) => x(r.d)).y((r) => y(r.rate_18_24))(snap)).attr('fill', 'none').attr('stroke', dash.colors[0]).attr('stroke-width', 2).attr('stroke-linejoin', 'round').attr('stroke-linecap', 'round');
  const tp = NZ.tip(el);
  rows.forEach((r) => svg.append('circle').attr('cx', x(r.d)).attr('cy', y(r.rate_18_24)).attr('r', 4.5).attr('fill', r.series === 'monthly' ? 'var(--color-panel)' : dash.colors[0]).attr('stroke', dash.colors[0]).attr('stroke-width', 2)
    .on('mousemove', (ev) => tp.show(ev, r.label + (r.series === 'monthly' ? ' (monthly statistics)' : ' (daily snapshot)'), [[dash.colors[0], `18-24 enrolled: ${NZ.fmt.pct1(r.rate_18_24)}`], [null, `All electors: ${d3.format(',')(r.total_electors)}`]])).on('mouseleave', () => tp.hide()));
  const last = snap[snap.length - 1];
  svg.append('text').attr('x', x(last.d) + 8).attr('y', y(last.rate_18_24) + 4).attr('fill', 'var(--color-fg)').attr('font-weight', 500).text(NZ.fmt.pct1(last.rate_18_24));
  if (first) svg.append('text').attr('x', x(first.d)).attr('y', y(first.rate_18_24) + 18).attr('fill', 'var(--color-fg)').attr('font-weight', 500).text(NZ.fmt.pct2(first.rate_18_24));
  [first, last].filter(Boolean).forEach((r, i) => svg.append('text').attr('x', x(r.d)).attr('y', h - 6).attr('text-anchor', i ? 'end' : 'start').attr('fill', 'var(--color-fg-muted)').attr('font-size', 11).text(r.label));
});

dash.draw('heat', (el) => {
  if (!NZ.ok('outcomes')) { NZ.clear(el); return; }
  const rows = dash.data('outcomes').data.filter((r) => r.pct >= 0.1);
  const houses = [...new Set(rows.map((r) => r.house))].sort(d3.ascending);
  const cols = d3.range(d3.min(rows, (r) => r.coalition), d3.max(rows, (r) => r.coalition) + 1);
  const lw = 130, top = 26, ch = 38; const h = top + houses.length * ch + 4;
  const [svg, w] = NZ.svgIn(el, h);
  const x = d3.scaleBand(cols, [lw, w]).padding(0.06); const y = d3.scaleBand(houses, [top, h - 4]).padding(0.08);
  const mx = d3.max(rows, (r) => r.pct); const tp = NZ.tip(el);
  svg.append('text').attr('x', lw).attr('y', 11).attr('fill', 'var(--color-fg-muted)').text('Coalition seats →');
  cols.forEach((c) => svg.append('text').attr('x', x(c) + x.bandwidth() / 2).attr('y', 24).attr('text-anchor', 'middle').attr('fill', 'var(--color-fg-muted)').text(c));
  houses.forEach((hh) => svg.append('text').attr('x', 0).attr('y', y(hh) + y.bandwidth() / 2 + 4).attr('fill', 'var(--color-fg)').text(`House of ${hh} (maj. ${Math.floor(hh / 2) + 1})`));
  rows.forEach((r) => {
    svg.append('rect').attr('x', x(r.coalition)).attr('y', y(r.house)).attr('width', x.bandwidth()).attr('height', y.bandwidth()).attr('rx', 3).attr('fill', NZ.sc[r.scenario]).attr('fill-opacity', 0.18 + 0.82 * Math.sqrt(r.pct / mx))
      .on('mousemove', (ev) => tp.show(ev, `${r.coalition} of ${r.house} seats`, [[NZ.sc[r.scenario], NZ.scName[r.scenario]], [null, `${d3.format('.1f')(r.pct)}% of runs`]])).on('mouseleave', () => tp.hide());
    svg.append('text').attr('x', x(r.coalition) + x.bandwidth() / 2).attr('y', y(r.house) + y.bandwidth() / 2 + 4).attr('text-anchor', 'middle').attr('pointer-events', 'none').attr('fill', r.pct / mx > 0.35 ? '#fff' : 'var(--color-fg)').attr('font-weight', 500).text(NZ.fmt.pct0(r.pct));
  });
});

dash.draw('chg', (el) => {
  if (!NZ.ok('parties', 'compare_2023')) { NZ.clear(el); return; }
  const c = new Map(dash.data('compare_2023').data.map((r) => [r.party, r.change_2023]));
  const rows = dash.data('parties').data.map((r) => ({party: r.party, a: c.get(r.party), b: r.share_change}));
  const lw = 100, rh = 34, h = rows.length * rh + 24;
  const [svg, w] = NZ.svgIn(el, h);
  const ext = d3.max(rows, (r) => Math.max(Math.abs(r.a ?? 0), Math.abs(r.b))) * 1.25;
  const x = d3.scaleLinear([-ext, ext], [lw, w - 8]);
  svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', 0).attr('y2', h - 18).attr('stroke', 'var(--cds-chart-axis)');
  [-ext * 0.8, 0, ext * 0.8].forEach((t) => svg.append('text').attr('x', x(t)).attr('y', h - 4).attr('text-anchor', 'middle').attr('fill', 'var(--color-fg-muted)').attr('font-size', 11).text((t > 0 ? '+' : t < 0 ? '−' : '') + d3.format('.1f')(Math.abs(t))));
  const tp = NZ.tip(el);
  rows.forEach((r, i) => {
    const y0 = i * rh + 4;
    svg.append('text').attr('x', 0).attr('y', y0 + 15).attr('fill', 'var(--color-fg)').text(r.party);
    [[r.a, NZ.muted, '2023 actual', 0], [r.b, dash.colors[0], '2026 projected', 12]].forEach(([v, col, lab, off]) => {
      if (v === undefined || v === null) return;
      svg.append('rect').attr('x', Math.min(x(0), x(v))).attr('y', y0 + off).attr('width', Math.max(1, Math.abs(x(v) - x(0)))).attr('height', 10).attr('rx', 2).attr('fill', col)
        .on('mousemove', (ev) => tp.show(ev, r.party, [[col, `${lab}: ${NZ.fmt.pp(v)}`]])).on('mouseleave', () => tp.hide());
    });
  });
});

dash.draw('ptable', (tb) => NZ.rowsTable(tb, 'parties', [
  [(r) => r.party], [(r) => d3.format('.2f')(r.prelim_pct), 'n'],
  [(r) => { const s = document.createElement('span'); s.textContent = d3.format('.2f')(r.final_pct_median); const d = document.createElement('div'); d.className = 'def'; d.textContent = `${d3.format('.1f')(r.final_pct_p10)}-${d3.format('.1f')(r.final_pct_p90)}`; s.appendChild(d); return s; }, 'n'],
  [(r) => String(r.prelim_seats), 'n'], [(r) => d3.format('.1f')(r.mean_seats), 'n'], [(r) => NZ.fmt.pct0(r.p_up), 'n'], [(r) => NZ.fmt.pct0(r.p_down), 'n']]));

dash.draw('sens', (el) => {
  if (!NZ.ok('sensitivity')) { NZ.clear(el); return; }
  const rows = dash.data('sensitivity').data;
  const h = 250, bt = 36, top = 8;
  const [svg, w] = NZ.svgIn(el, h);
  const x = d3.scaleBand(rows.map((r) => r.k), [36, w]).padding(0.3); const y = d3.scaleLinear([0, 100], [h - bt, top]);
  [0, 50, 100].forEach((t) => { svg.append('line').attr('x1', 36).attr('x2', w).attr('y1', y(t)).attr('y2', y(t)).attr('stroke', 'var(--cds-chart-grid)'); svg.append('text').attr('x', 0).attr('y', y(t) + 4).attr('fill', 'var(--color-fg-muted)').attr('font-size', 11).text(t + '%'); });
  const tp = NZ.tip(el);
  rows.forEach((r) => {
    let acc = 0;
    ['alone', 'nat_needs_opp', 'labour'].forEach((k) => {
      const v = r[k]; const y1 = y(acc); acc += v; const y2 = y(acc);
      svg.append('rect').attr('x', x(r.k)).attr('y', y2 + 1).attr('width', x.bandwidth()).attr('height', Math.max(0, y1 - y2 - 2)).attr('rx', 2).attr('fill', NZ.sc[k])
        .on('mousemove', (ev) => tp.show(ev, `Lean at ${NZ.fmt.k(r.k)} of history`, [[NZ.sc[k], `${NZ.scName[k]}: ${d3.format('.1f')(v)}%`]])).on('mouseleave', () => tp.hide());
      if (y1 - y2 > 16) svg.append('text').attr('x', x(r.k) + x.bandwidth() / 2).attr('y', (y1 + y2) / 2 + 4).attr('text-anchor', 'middle').attr('fill', '#fff').attr('font-weight', 500).attr('pointer-events', 'none').text(String(NZ.trip(r)[k]));
    });
    svg.append('text').attr('x', x(r.k) + x.bandwidth() / 2).attr('y', h - bt + 16).attr('text-anchor', 'middle').attr('fill', 'var(--color-fg-muted)').attr('font-size', 11).text(NZ.fmt.k(r.k));
    if (Math.abs(r.k - 0.85) < 1e-9) svg.append('text').attr('x', x(r.k) + x.bandwidth() / 2).attr('y', h - bt + 30).attr('text-anchor', 'middle').attr('fill', 'var(--color-fg)').attr('font-size', 11).text('central');
  });
});

dash.draw('vtable', (tb) => {
  NZ.rowsTable(tb, 'variants', [[(r) => r.variant], [(r) => NZ.w(r, 'alone'), 'n'], [(r) => NZ.w(r, 'nat_needs_opp'), 'n'], [(r) => NZ.w(r, 'labour'), 'n'], [(r) => NZ.w(r, 'opp_pivotal'), 'n'], [(r) => NZ.fmt.pct0(r.wai), 'n'], [(r) => NZ.fmt.pct0(r.he), 'n']]);
  tb.querySelectorAll('tr').forEach((tr) => { if (tr.dataset.key === 'central') tr.className = 'hl'; });
});

dash.draw('ytable', (tb) => NZ.rowsTable(tb, 'template_years', [[(r) => String(r.year)], [(r) => r.weight + '%', 'n'], [(r) => NZ.w(r, 'alone'), 'n'], [(r) => NZ.w(r, 'nat_needs_opp'), 'n'], [(r) => NZ.w(r, 'labour'), 'n'], [(r) => NZ.w(r, 'opp_pivotal'), 'n']]));

dash.draw('hist', (el) => {
  if (!NZ.ok('history_party')) { NZ.clear(el); return; }
  const rows = dash.data('history_party').data;
  const series = [['NAT', 'National', NZ.PARTY.NAT], ['LAB', 'Labour', NZ.PARTY.LAB], ['GP', 'Green', NZ.PARTY.GP], ['NZF', 'NZ First', NZ.PARTY.NZF]];
  const h = 250, lm = 34, rm = 70, top = 10, bm = 24;
  const [svg, w] = NZ.svgIn(el, h);
  const x = d3.scalePoint(rows.map((r) => r.year), [lm, w - rm]);
  const vals = rows.flatMap((r) => series.map(([k]) => r[k]));
  const y = d3.scaleLinear([Math.floor(d3.min(vals)) - 1, Math.ceil(d3.max(vals)) + 1], [h - bm, top]).nice();
  y.ticks(5).forEach((t) => { svg.append('line').attr('x1', lm).attr('x2', w - rm).attr('y1', y(t)).attr('y2', y(t)).attr('stroke', t === 0 ? 'var(--cds-chart-axis)' : 'var(--cds-chart-grid)'); svg.append('text').attr('x', lm - 6).attr('y', y(t) + 4).attr('text-anchor', 'end').attr('fill', 'var(--color-fg-muted)').attr('font-size', 11).text(t > 0 ? '+' + t : t); });
  rows.forEach((r) => svg.append('text').attr('x', x(r.year)).attr('y', h - 6).attr('text-anchor', 'middle').attr('fill', 'var(--color-fg-muted)').attr('font-size', 11).text(r.year));
  const ends = [];
  series.forEach(([k, name, col]) => { svg.append('path').attr('d', d3.line().x((r) => x(r.year)).y((r) => y(r[k]))(rows)).attr('fill', 'none').attr('stroke', col).attr('stroke-width', 2).attr('stroke-linejoin', 'round').attr('stroke-linecap', 'round'); ends.push({name, col, y: y(rows[rows.length - 1][k])}); });
  ends.sort((a, b) => a.y - b.y); for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 13) ends[i].y = ends[i - 1].y + 13;
  ends.forEach((e) => svg.append('text').attr('x', w - rm + 6).attr('y', e.y + 4).attr('fill', e.col).attr('font-size', 11).attr('font-weight', 500).text(e.name));
  const tp = NZ.tip(el);
  rows.forEach((r) => svg.append('rect').attr('x', x(r.year) - 14).attr('y', top).attr('width', 28).attr('height', h - bm - top).attr('fill', 'transparent')
    .on('mousemove', (ev) => tp.show(ev, `${r.year} (specials ${d3.format('.1f')(r.special_share)}% of vote)`, series.map(([k, n, c]) => [c, `${n}: ${NZ.fmt.pp(r[k])}`]))).on('mouseleave', () => tp.hide()));
});

dash.draw('hseats', (el) => {
  if (!NZ.ok('history_seats')) { NZ.clear(el); return; }
  const rows = dash.data('history_seats').data;
  const seats = [...new Set(rows.map((r) => r.seat))]; const years = [...new Set(rows.map((r) => r.year))];
  const h = 250, top = 24, bm = 22, lm = 40;
  const [svg, w] = NZ.svgIn(el, h);
  const pw = (w - lm) / seats.length; const ext = d3.max(rows, (r) => Math.abs(r.labour_net));
  const y = d3.scaleLinear([-ext, ext], [h - bm, top]).nice();
  y.ticks(4).forEach((t) => { svg.append('line').attr('x1', lm).attr('x2', w).attr('y1', y(t)).attr('y2', y(t)).attr('stroke', t === 0 ? 'var(--cds-chart-axis)' : 'var(--cds-chart-grid)'); svg.append('text').attr('x', lm - 6).attr('y', y(t) + 4).attr('text-anchor', 'end').attr('fill', 'var(--color-fg-muted)').attr('font-size', 11).text(d3.format('~s')(t)); });
  const tp = NZ.tip(el); const lab = NZ.PARTY.LAB;
  seats.forEach((s, i) => {
    const x = d3.scaleBand(years, [lm + i * pw + 6, lm + (i + 1) * pw - 6]).padding(0.2);
    svg.append('text').attr('x', lm + i * pw + pw / 2).attr('y', 12).attr('text-anchor', 'middle').attr('fill', 'var(--color-fg)').attr('font-weight', 500).text(s);
    rows.filter((r) => r.seat === s).forEach((r) => {
      svg.append('rect').attr('x', x(r.year)).attr('y', Math.min(y(0), y(r.labour_net))).attr('width', x.bandwidth()).attr('height', Math.max(1, Math.abs(y(r.labour_net) - y(0)))).attr('rx', 2).attr('fill', r.labour_net >= 0 ? lab : NZ.PARTY.NAT)
        .on('mousemove', (ev) => tp.show(ev, `${s}, ${r.year}`, [[null, `${r.labour_net >= 0 ? 'Labour' : 'National'} +${d3.format(',')(Math.abs(r.labour_net))} on specials`]])).on('mouseleave', () => tp.hide());
    });
    svg.append('text').attr('x', x(years[0])).attr('y', h - 6).attr('fill', 'var(--color-fg-muted)').attr('font-size', 10).text(String(years[0]));
    svg.append('text').attr('x', x(years[years.length - 1]) + x.bandwidth()).attr('y', h - 6).attr('text-anchor', 'end').attr('fill', 'var(--color-fg-muted)').attr('font-size', 10).text(String(years[years.length - 1]));
  });
});

dash.draw('atable', (tb) => NZ.rowsTable(tb, 'assumptions', [[(r) => r.assumption], [(r) => r.value], [(r) => r.basis], [(r) => r.if_wrong]]));

// Battleground seats: each candidate's chance and the distribution of the final margin, centred on
// zero, with the more left-leaning party always on the left.
dash.draw('bground', (el) => {
  el.replaceChildren();
  if (!NZ.ok('battleground')) return;
  const rows = dash.data('battleground').data.slice().sort((a, b) => a.order - b.order);
  const ns = 'http://www.w3.org/2000/svg', P = NZ.PARTY, N = NZ.PNAME;
  const last = (n) => n.split(' ').slice(-1)[0];
  const num = (v) => Math.abs(Math.round(v)).toLocaleString('en-NZ');
  rows.forEach((r) => {
    const box = document.createElement('div'); box.className = 'bg-seat';
    const head = document.createElement('div'); head.className = 'bg-head';
    const t = document.createElement('h3'); t.textContent = r.seat; head.appendChild(t);
    const sub = document.createElement('p'); sub.className = 'note';
    const ahead = r.prelim_x >= 0 ? r.right_name : r.left_name, ap = r.prelim_x >= 0 ? r.right_party : r.left_party;
    sub.textContent = `Preliminary count: ${last(ahead)} (${N[ap]}) ahead by ${num(r.prelim_margin)}`; head.appendChild(sub);
    box.appendChild(head);
    const odds = document.createElement('div'); odds.className = 'bg-odds';
    [[r.left_name, r.left_party, r.left_win, 'l'], [r.right_name, r.right_party, r.right_win, 'r']].forEach(([n, p, v, side]) => {
      const d = document.createElement('div'); d.className = 'bg-side ' + side;
      const a = document.createElement('div'); a.className = 'note'; a.textContent = `${n} (${N[p]})`;
      const b = document.createElement('div'); b.className = 'bg-pct'; b.textContent = NZ.show0(v, NZ.lr0([r.left_win, r.right_win])[side === 'l' ? 0 : 1]);
      d.append(a, b); odds.appendChild(d);
    });
    box.appendChild(odds);
    const bar = document.createElement('div'); bar.className = 'bg-bar';
    [[r.left_win, r.left_party], [r.right_win, r.right_party]].forEach(([v, p]) => { const s = document.createElement('span'); s.style.flex = v; s.style.background = P[p]; bar.appendChild(s); });
    box.appendChild(bar);
    const W = 600, H = 120, top = 8, bot = 24, xl = 4, xr = W - 4, n = r.counts.length;
    const ext = -r.bin_start, sx = (v) => xl + (v + ext) / (2 * ext) * (xr - xl), mx = Math.max(...r.counts), tot = r.counts.reduce((a, b) => a + b, 0);
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', '100%'); svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', `${r.seat}: ${r.left_name} ${r.left_win}%, ${r.right_name} ${r.right_win}% of runs.`);
    const add = (tag, at) => { const e = document.createElementNS(ns, tag); Object.entries(at).forEach(([k, v]) => e.setAttribute(k, v)); svg.appendChild(e); return e; };
    add('rect', {x: sx(r.p10_x), width: sx(r.p90_x) - sx(r.p10_x), y: top, height: H - top - bot, fill: 'var(--color-panel)'});
    r.counts.forEach((v, i) => {
      const a = r.bin_start + i * r.bin_width, b = a + r.bin_width, left = b <= 0, bh = (v / mx) * (H - top - bot);
      const rect = add('rect', {x: sx(a) + 0.5, width: Math.max(0.8, sx(b) - sx(a) - 1), y: H - bot - bh, height: bh, rx: 1,
        fill: P[left ? r.left_party : r.right_party], opacity: (i === 0 || i === n - 1) ? 0.35 : 0.85});
      const who = last(left ? r.left_name : r.right_name), lo = Math.min(Math.abs(a), Math.abs(b)), hi = Math.max(Math.abs(a), Math.abs(b));
      const tt = document.createElementNS(ns, 'title');
      tt.textContent = ((i === 0 || i === n - 1) ? `${who} by ${num(lo)} or more` : `${who} by ${num(lo)} to ${num(hi)}`) + `: ${(v / tot * 100).toFixed(1)}% of runs`;
      rect.appendChild(tt);
    });
    add('line', {x1: xl, x2: xr, y1: H - bot, y2: H - bot, stroke: 'var(--cds-chart-axis)'});
    add('line', {x1: sx(0), x2: sx(0), y1: top - 4, y2: H - bot + 4, stroke: 'var(--color-fg)', 'stroke-width': 1.5});
    add('line', {x1: sx(r.prelim_x), x2: sx(r.prelim_x), y1: top, y2: H - bot, stroke: 'var(--color-fg-muted)', 'stroke-dasharray': '3 3'});
    const lab = (x, s, c) => { const e = add('text', {x, y: H - 7, 'font-size': 12, 'text-anchor': 'middle', fill: c || 'var(--color-fg-muted)'}); e.textContent = s; };
    const step = [100, 200, 250, 500, 1000, 2000].find((s) => 2 * ext / s <= 8) || 2000;
    for (let v = step; v <= ext * 0.95; v += step) { lab(sx(v), num(v)); lab(sx(-v), num(v)); }
    lab(sx(0), '0', 'var(--color-fg)');
    box.appendChild(svg);
    const foot = document.createElement('div'); foot.className = 'bg-foot';
    foot.innerHTML = '';
    [[`← ${last(r.left_name)} ahead`, `If ${last(r.left_name)} wins: ${r.if_left_wins}`, 'l'], [`${last(r.right_name)} ahead →`, `If ${last(r.right_name)} wins: ${r.if_right_wins}`, 'r']].forEach(([a, b, side]) => {
      const d = document.createElement('div'); d.className = 'bg-side ' + side;
      const x = document.createElement('div'); x.textContent = a; const y = document.createElement('div'); y.className = 'note'; y.textContent = b;
      d.append(x, y); foot.appendChild(d);
    });
    box.appendChild(foot);
    el.appendChild(box);
  });
});

// Who gains, who pays: list-seat changes from the preliminary allocation.
dash.draw('lmatrix', (el) => {
  el.replaceChildren();
  if (!NZ.ok('list_matrix', 'list_matrix_rows', 'list_matrix_cols')) return;
  const cells = dash.data('list_matrix').data, rows = dash.data('list_matrix_rows').data.slice().sort((a, b) => a.order - b.order);
  const cols = dash.data('list_matrix_cols').data.slice().sort((a, b) => a.order - b.order), P = NZ.PARTY;
  const get = (r, c) => (cells.find((x) => x.row === r && x.col === c) || {pct: 0}).pct;
  const chips = (ps) => { const s = document.createElement('span'); s.className = 'mx-chips'; ps.forEach((p) => { const i = document.createElement('i'); i.style.background = P[p]; s.appendChild(i); }); return s; };
  const div = (cls, txt) => { const d = document.createElement('div'); if (cls) d.className = cls; if (txt !== undefined) d.textContent = txt; return d; };
  const allPct = cells.map((x) => x.pct), whole = NZ.lr0(allPct), W = new Map(cells.map((x, i) => [x.row + '|' + x.col, NZ.show0(x.pct, whole[i])]));
  const g = div('mx');
  g.style.gridTemplateColumns = `minmax(5.5rem,auto) repeat(${cols.length}, minmax(0,1fr))`;
  g.appendChild(div('mx-corner', 'Gains ↓   Pays →'));
  cols.forEach((c) => { const d = div('mx-ch'); d.appendChild(chips(c.parties)); d.appendChild(div('', c.label)); g.appendChild(d); });
  rows.forEach((r) => {
    const h = div('mx-rh'); h.appendChild(chips(r.parties)); h.appendChild(div('', r.label)); h.appendChild(div('note', NZ.fmt.pct0(r.pct))); g.appendChild(h);
    cols.forEach((c) => {
      const v = get(r.row, c.col), t = Math.min(1, v / 40), d = div('mx-c' + (v > 0 ? '' : ' empty'), v > 0 ? W.get(r.row + '|' + c.col) : '·');
      if (v > 0) { d.style.background = `rgba(136,135,128,${0.12 + 0.62 * t})`; if (t > 0.55) d.style.color = '#fff'; }
      d.title = `${r.label} while ${c.label}: ${v.toFixed(1)}% of runs`;
      g.appendChild(d);
    });
  });
  g.appendChild(div('mx-rh note', 'All'));
  cols.forEach((c) => g.appendChild(div('mx-tot', NZ.fmt.pct0(c.pct))));
  g.appendChild(div('mx-rh note', 'Effect'));
  cols.forEach((c) => g.appendChild(div('mx-eff', c.effect)));
  g.appendChild(div('mx-rh note', 'Outcome'));
  cols.forEach((c) => {
    const b = div('mx-out'), tw = NZ.trip(c);
    b.title = NZ.SK.map((k) => `${NZ.scLong[k]} ${tw[k]}%`).join(', ');
    ['labour', 'nat_needs_opp', 'alone'].forEach((k) => { if (c[k] > 0) { const s = document.createElement('span'); s.style.flex = c[k]; s.style.background = NZ.sc[k]; b.appendChild(s); } });
    g.appendChild(b);
  });
  el.appendChild(g);
  const key = div('mx-key');
  ['labour', 'nat_needs_opp', 'alone'].forEach((k) => { const s = document.createElement('span'); const i = document.createElement('i'); i.className = 'sw'; i.style.background = NZ.sc[k]; s.append(i, document.createTextNode(NZ.scLong[k])); key.appendChild(s); });
  el.appendChild(key);
});
