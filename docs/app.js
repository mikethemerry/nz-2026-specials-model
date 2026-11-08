window.NZ = (() => {
  const C = dash.colors;
  const sc = {alone: C[0], nat_needs_opp: C[3] || C[1], labour: C[7] || C[2]};
  const scName = {alone: 'Coalition alone', nat_needs_opp: 'National needs Opportunity', labour: 'Labour could form a government'};
  const scLong = {alone: 'Coalition governs alone', nat_needs_opp: 'National needs Opportunity', labour: 'Labour could form a government'};
  const fmt = {
    pct0: (v) => (v > 0 && v < 0.5 ? '<1' : d3.format('.0f')(v)) + '%',
    pct1: (v) => d3.format('.1f')(v) + '%',
    pct2: (v) => d3.format('.2f')(v) + '%',
    int: d3.format(','),
    pp: (v) => (v > 0 ? '+' : v < 0 ? '−' : '') + d3.format('.2f')(Math.abs(v)) + ' pts',
    k: (v) => d3.format('.0f')(v * 100) + '%',
    raw: (v) => String(v)
  };
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
  return {sc, scName, scLong, fmt, tip, ok, muted, svgIn, clear, rowsTable, barCell};
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
  const v = row ? row[el.dataset.field] : undefined;
  el.textContent = v === undefined || v === null ? '—' : NZ.fmt[el.dataset.fmt || 'raw'](v);
});

dash.draw('grid', (el) => {
  el.replaceChildren();
  if (!NZ.ok('grid')) return;
  const rows = dash.data('grid').data; const cols = [12, 11]; const keys = ['alone', 'nat_needs_opp', 'labour'];
  const rlab = [...new Map(rows.map((r) => [r.seat_order, r.seats])).entries()].sort((a, b) => a[0] - b[0]);
  const g = document.createElement('div'); g.className = 'sg';
  const add = (cls, t) => { const d = document.createElement('div'); d.className = cls; if (t) d.textContent = t; g.appendChild(d); return d; };
  add('sg-h', ''); cols.forEach((z) => { const r = rows.find((x) => x.nzf_seats === z); add('sg-h', r ? r.nzf : ''); });
  rlab.forEach(([o, lab]) => {
    add('sg-r', lab);
    cols.forEach((z) => {
      const r = rows.find((x) => x.seat_order === o && x.nzf_seats === z); const c = add('sg-c'); if (!r) return;
      const p = document.createElement('div'); p.className = 'sg-p'; p.textContent = NZ.fmt.pct0(r.p_runs);
      const s = document.createElement('small'); s.textContent = 'of runs'; p.appendChild(s); c.appendChild(p);
      const b = document.createElement('div'); b.className = 'sg-b';
      keys.forEach((k) => { if (r[k] <= 0) return; const sp = document.createElement('span'); sp.style.flex = String(r[k]); sp.style.background = NZ.sc[k]; b.appendChild(sp); });
      c.appendChild(b);
      const l = document.createElement('div'); l.className = 'sg-l';
      keys.forEach((k) => { if (r[k] <= 0) return; const ln = document.createElement('div'); const i = document.createElement('i'); i.className = 'sw'; i.style.background = NZ.sc[k]; ln.appendChild(i); ln.appendChild(document.createTextNode(`${NZ.scName[k]} ${NZ.fmt.pct0(r[k])}`)); l.appendChild(ln); });
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

dash.draw('oppnat', (tb) => NZ.rowsTable(tb, 'opp_by_nat', [[(r) => r.band], [(r) => NZ.fmt.pct0(r.p_runs), 'n'], [(r) => NZ.barCell(r.opp_pivotal, 100, NZ.sc.nat_needs_opp)], [(r) => NZ.fmt.pct0(r.ent_drop), 'n']]));

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
      if (y1 - y2 > 16) svg.append('text').attr('x', x(r.k) + x.bandwidth() / 2).attr('y', (y1 + y2) / 2 + 4).attr('text-anchor', 'middle').attr('fill', '#fff').attr('font-weight', 500).attr('pointer-events', 'none').text(d3.format('.0f')(v));
    });
    svg.append('text').attr('x', x(r.k) + x.bandwidth() / 2).attr('y', h - bt + 16).attr('text-anchor', 'middle').attr('fill', 'var(--color-fg-muted)').attr('font-size', 11).text(NZ.fmt.k(r.k));
    if (Math.abs(r.k - 0.85) < 1e-9) svg.append('text').attr('x', x(r.k) + x.bandwidth() / 2).attr('y', h - bt + 30).attr('text-anchor', 'middle').attr('fill', 'var(--color-fg)').attr('font-size', 11).text('central');
  });
});

dash.draw('vtable', (tb) => {
  NZ.rowsTable(tb, 'variants', [[(r) => r.variant], [(r) => NZ.fmt.pct0(r.alone), 'n'], [(r) => NZ.fmt.pct0(r.nat_needs_opp), 'n'], [(r) => NZ.fmt.pct0(r.labour), 'n'], [(r) => NZ.fmt.pct0(r.opp_pivotal), 'n'], [(r) => NZ.fmt.pct0(r.wai), 'n'], [(r) => NZ.fmt.pct0(r.he), 'n']]);
  tb.querySelectorAll('tr').forEach((tr) => { if (tr.dataset.key === 'central') tr.className = 'hl'; });
});

dash.draw('ytable', (tb) => NZ.rowsTable(tb, 'template_years', [[(r) => String(r.year)], [(r) => r.weight + '%', 'n'], [(r) => NZ.fmt.pct0(r.alone), 'n'], [(r) => NZ.fmt.pct0(r.nat_needs_opp), 'n'], [(r) => NZ.fmt.pct0(r.labour), 'n'], [(r) => NZ.fmt.pct0(r.opp_pivotal), 'n']]));

dash.draw('hist', (el) => {
  if (!NZ.ok('history_party')) { NZ.clear(el); return; }
  const rows = dash.data('history_party').data;
  const series = [['NAT', 'National', dash.colors[0]], ['LAB', 'Labour', dash.colors[7] || dash.colors[1]], ['GP', 'Green', dash.colors[5] || dash.colors[2]], ['NZF', 'NZ First', NZ.muted]];
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
  const tp = NZ.tip(el); const lab = dash.colors[7] || dash.colors[1];
  seats.forEach((s, i) => {
    const x = d3.scaleBand(years, [lm + i * pw + 6, lm + (i + 1) * pw - 6]).padding(0.2);
    svg.append('text').attr('x', lm + i * pw + pw / 2).attr('y', 12).attr('text-anchor', 'middle').attr('fill', 'var(--color-fg)').attr('font-weight', 500).text(s);
    rows.filter((r) => r.seat === s).forEach((r) => {
      svg.append('rect').attr('x', x(r.year)).attr('y', Math.min(y(0), y(r.labour_net))).attr('width', x.bandwidth()).attr('height', Math.max(1, Math.abs(y(r.labour_net) - y(0)))).attr('rx', 2).attr('fill', r.labour_net >= 0 ? lab : dash.colors[0])
        .on('mousemove', (ev) => tp.show(ev, `${s}, ${r.year}`, [[null, `${r.labour_net >= 0 ? 'Labour' : 'National'} +${d3.format(',')(Math.abs(r.labour_net))} on specials`]])).on('mouseleave', () => tp.hide());
    });
    svg.append('text').attr('x', x(years[0])).attr('y', h - 6).attr('fill', 'var(--color-fg-muted)').attr('font-size', 10).text(String(years[0]));
    svg.append('text').attr('x', x(years[years.length - 1]) + x.bandwidth()).attr('y', h - 6).attr('text-anchor', 'end').attr('fill', 'var(--color-fg-muted)').attr('font-size', 10).text(String(years[years.length - 1]));
  });
});

dash.draw('atable', (tb) => NZ.rowsTable(tb, 'assumptions', [[(r) => r.assumption], [(r) => r.value], [(r) => r.basis], [(r) => r.if_wrong]]));
