// Save a dated snapshot of the 2026 results pages (party vote, electorate status and every
// electorate's candidates) as one zip, from inside a browser.
//
// electionresults.govt.nz shows the preliminary count until the official result on
// 27 November 2026, at the same URLs. To use:
//   1. Open https://electionresults.govt.nz/ge2026/ in a browser.
//   2. Open the developer console, paste this whole file and press Enter.
//   3. Unzip ge2026-YYYY-MM-DD.zip into data/raw/ (it contains ge2026/YYYY-MM-DD/...).
//   4. Run: python scripts/fetch_raw.py manifest && make check-prelim
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const day = new Date().toISOString().slice(0, 10);
  const pages = ["index.html", "electorate-status.html"].concat([...Array(71)].map((_, i) => `electorate-details-${String(i + 1).padStart(2, "0")}.html`));
  const files = [], failed = [];
  for (const p of pages) {
    let ok = false;
    for (let a = 0; a < 6 && !ok; a++) {
      if (a) await sleep(1500 * 2 ** (a - 1));
      try { const r = await fetch(`/ge2026/${p}`, { cache: "no-store" }); if (!r.ok) continue; files.push([`ge2026/${day}/${p}`, new Uint8Array(await r.arrayBuffer())]); ok = true; } catch (e) {}
    }
    if (!ok) failed.push(p);
    await sleep(400);
  }
  // stored (uncompressed) zip, as in browser_fetch.js
  const crcT = new Uint32Array(256).map((_, i) => { let c = i; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc = b => { let c = ~0; for (const x of b) c = crcT[(c ^ x) & 255] ^ (c >>> 8); return ~c >>> 0; };
  const now = new Date(), dosT = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1), dosD = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
  const parts = [], central = []; let off = 0;
  const put = (dv, fields) => fields.forEach(([p, v, s]) => s === 4 ? dv.setUint32(p, v, true) : dv.setUint16(p, v, true));
  for (const [name, data] of files) {
    const nm = new TextEncoder().encode(name), c = crc(data), L = new DataView(new ArrayBuffer(30)), C = new DataView(new ArrayBuffer(46));
    put(L, [[0, 0x04034b50, 4], [4, 20, 2], [10, dosT, 2], [12, dosD, 2], [14, c, 4], [18, data.length, 4], [22, data.length, 4], [26, nm.length, 2]]);
    put(C, [[0, 0x02014b50, 4], [4, 20, 2], [6, 20, 2], [12, dosT, 2], [14, dosD, 2], [16, c, 4], [20, data.length, 4], [24, data.length, 4], [28, nm.length, 2], [42, off, 4]]);
    parts.push(L, nm, data); central.push(C, nm); off += 30 + nm.length + data.length;
  }
  const cd = central.reduce((s, p) => s + p.byteLength, 0), E = new DataView(new ArrayBuffer(22));
  put(E, [[0, 0x06054b50, 4], [8, files.length, 2], [10, files.length, 2], [12, cd, 4], [16, off, 4]]);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([...parts, ...central, E], { type: "application/zip" }));
  a.download = `ge2026-${day}.zip`; document.body.appendChild(a); a.click();
  console.log("Done:", files.length, "pages", failed.length ? "failed: " + failed.join(", ") : "");
})();
