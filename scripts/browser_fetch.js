// Download every 2008-2023 voting-place CSV, and the 2023 split-vote statistics, as one zip, from inside a browser.
//
// The Commission's archive blocks scripted downloads (curl, Python) but not a
// browser. To use:
//   1. Open https://archive.electionresults.govt.nz/ in a browser.
//   2. Open the developer console (Cmd-Option-J in Chrome, Cmd-Option-C in Safari).
//   3. Paste this whole file and press Enter. Wait for "Done" (about 12 minutes:
//      it deliberately goes slowly because the archive throttles fast requests).
//   4. Unzip history.zip into data/raw/ so you get data/raw/history/<year>/...
//   5. Run: python scripts/fetch_raw.py manifest && make check-calibration check-flows
(async () => {
  const YEARS = ["2008", "2011", "2014", "2017", "2020", "2023"];
  const url = (y, kind, n) => +y >= 2017
    ? `/electionresults_${y}/statistics/csv/${kind}-votes-by-voting-place-${n}.csv`
    : `/electionresults_${y}/e9/csv/e9_part8_${kind === "candidate" ? "cand" : "party"}_${n}.csv`;

  // Electorates per election (general + Māori). The archive throttles quick
  // requests, so go slowly and retry; never treat a refusal as "no more files".
  const SEATS = { 2008: 70, 2011: 70, 2014: 71, 2017: 71, 2020: 72, 2023: 72 };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const files = [], failed = [];
  for (const y of YEARS) for (const kind of ["candidate", "party"]) {
    let got = 0;
    for (let n = 1; n <= SEATS[y]; n++) {
      let ok = false;
      for (let attempt = 0; attempt < 7 && !ok; attempt++) {
        if (attempt) await sleep(2000 * 2 ** (attempt - 1));   // 2, 4, 8 ... 64 s
        try {
          const r = await fetch(url(y, kind, n), { cache: "no-store" });
          if (!r.ok) continue;
          const b = new Uint8Array(await r.arrayBuffer());
          if (/^\s*<(!doctype|html)/i.test(new TextDecoder().decode(b.slice(0, 64)))) continue;
          files.push([`history/${y}/${kind}/${n}.csv`, b]);
          ok = true; got++;
        } catch (e) { /* network error: retry */ }
      }
      if (!ok) failed.push(url(y, kind, n));
      await sleep(700);
    }
    console.log(y, kind, got, "of", SEATS[y]);
  }
  // 2023 split-vote statistics (party vote x electorate vote), one file per electorate
  let sv = 0;
  for (let n = 1; n <= 72; n++) {
    const u = `/electionresults_2023/statistics/csv/split-votes-electorate-${n}.csv`;
    let ok = false;
    for (let attempt = 0; attempt < 7 && !ok; attempt++) {
      if (attempt) await sleep(2000 * 2 ** (attempt - 1));
      try {
        const r = await fetch(u, { cache: "no-store" });
        if (!r.ok) continue;
        files.push([`splitvotes/2023/${n}.csv`, new Uint8Array(await r.arrayBuffer())]);
        ok = true; sv++;
      } catch (e) { /* retry */ }
    }
    if (!ok) failed.push(u);
    await sleep(700);
  }
  console.log("2023 split votes", sv, "of 72");
  if (failed.length) console.warn(failed.length, "files failed:", failed);

  // Minimal uncompressed ("stored") zip writer
  const crcT = new Uint32Array(256).map((_, i) => { let c = i; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc = b => { let c = ~0; for (const x of b) c = crcT[(c ^ x) & 255] ^ (c >>> 8); return ~c >>> 0; };
  const parts = [], central = []; let off = 0;
  const hdr = (n) => new DataView(new ArrayBuffer(n));
  const now = new Date();
  const dosT = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1);
  const dosD = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
  for (const [name, data] of files) {
    const nm = new TextEncoder().encode(name), c = crc(data), L = hdr(30);
    [[0, 0x04034b50, 4], [4, 20, 2], [10, dosT, 2], [12, dosD, 2], [14, c, 4], [18, data.length, 4], [22, data.length, 4], [26, nm.length, 2]]
      .forEach(([p, v, s]) => s === 4 ? L.setUint32(p, v, true) : L.setUint16(p, v, true));
    parts.push(L, nm, data);
    const C = hdr(46);
    [[0, 0x02014b50, 4], [4, 20, 2], [6, 20, 2], [12, dosT, 2], [14, dosD, 2], [16, c, 4], [20, data.length, 4], [24, data.length, 4], [28, nm.length, 2], [42, off, 4]]
      .forEach(([p, v, s]) => s === 4 ? C.setUint32(p, v, true) : C.setUint16(p, v, true));
    central.push(C, nm);
    off += 30 + nm.length + data.length;
  }
  const cdSize = central.reduce((s, p) => s + p.byteLength, 0), E = hdr(22);
  [[0, 0x06054b50, 4], [8, files.length, 2], [10, files.length, 2], [12, cdSize, 4], [16, off, 4]]
    .forEach(([p, v, s]) => s === 4 ? E.setUint32(p, v, true) : E.setUint16(p, v, true));
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([...parts, ...central, E], { type: "application/zip" }));
  a.download = "history.zip"; document.body.appendChild(a); a.click();
  console.log("Done:", files.length, "files in history.zip");
})();
