// Ground edge audit: samples the model's ground surface on a grid and lists every place where two neighbouring cells
// differ by >= MIN mm: who is high, who is low, how long the step runs and how high it is; plus every patch where
// the bare site base shows. The surface is the top of every body that stands on the ground (bottom below 0), capped
// at +500 mm (a wall counts as a tall built thing; roofs and floors above do not hide the ground); plants and trees
// are left out. Outside the plot = Blender's filler ground (Site_Base top - 4 mm).
// v2 (2026-10-25, before the Stage 4 build): v1 skipped wall faces above +500, so the ground under a wall's foot
// showed as bare base (a false 1.8 m2 "patch" round the tower); now the wall itself is the surface there.
// Usage: node ground_edges.mjs <model.obj> [out.json] [cell mm] [min step mm]
import fs from "fs";
import { fileURLToPath } from "node:url";

export function groundEdges(objPath, { cell = 100, min = 100, zmax = 500 } = {}) {
  const SKIP = /Shrub|Tree|Plant|Grass|Trunk|Canopy/i;
  const v = [], faces = []; let cur = null;
  for (const line of fs.readFileSync(objPath, "utf8").split(/\r?\n/)) {
    if (line.startsWith("v ")) v.push(line.slice(2).trim().split(/\s+/).map(Number));
    else if (line.startsWith("o ") || line.startsWith("g ")) cur = line.slice(2).trim();
    else if (line.startsWith("f ") && cur && !SKIP.test(cur))
      faces.push({ name: cur.replace(/ \(\d+\)$/, ""), idx: line.slice(2).trim().split(/\s+/).map((t) => { const i = parseInt(t.split("/")[0]); return i < 0 ? v.length + i : i - 1; }) });
  }
  const bottom = {};
  for (const f of faces) for (const i of f.idx) bottom[f.name] = Math.min(bottom[f.name] ?? Infinity, v[i][2]);
  const tris = [];
  for (const f of faces) {
    if (bottom[f.name] >= 0) continue;   // not standing on the ground
    for (let k = 1; k + 1 < f.idx.length; k++) tris.push({ p: [v[f.idx[0]], v[f.idx[k]], v[f.idx[k + 1]]], name: f.name });
  }
  const zAt = (t, x, y) => {   // z of a triangle at (x, y), or null
    const [a, b, c] = t.p, d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1]);
    if (Math.abs(d) < 1e-9) return null;   // vertical face
    const l1 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / d, l2 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / d, l3 = 1 - l1 - l2, e = -1e-9;
    return l1 < e || l2 < e || l3 < e ? null : Math.min(zmax, l1 * a[2] + l2 * b[2] + l3 * c[2]);
  };
  const site = tris.filter((t) => t.name === "Site_Base").flatMap((t) => t.p);
  const X0 = Math.min(...site.map((q) => q[0])) - 2 * cell, X1 = Math.max(...site.map((q) => q[0])) + 2 * cell;
  const Y0 = Math.min(...site.map((q) => q[1])) - 2 * cell, Y1 = Math.max(...site.map((q) => q[1])) + 2 * cell;
  const OUTSIDE_Z = Math.max(...site.map((q) => q[2])) - 4, NX = Math.round((X1 - X0) / cell), NY = Math.round((Y1 - Y0) / cell);
  const buckets = Array.from({ length: NX }, () => []);
  for (const t of tris) {
    const xs = t.p.map((q) => q[0]);
    for (let i = Math.max(0, Math.floor((Math.min(...xs) - X0) / cell)); i <= Math.min(NX - 1, Math.floor((Math.max(...xs) - X0) / cell)); i++) buckets[i].push(t);
  }
  const Z = new Float64Array(NX * NY), N = new Array(NX * NY);
  for (let i = 0; i < NX; i++) for (let j = 0; j < NY; j++) {
    const x = X0 + (i + 0.5) * cell, y = Y0 + (j + 0.5) * cell;
    let best = OUTSIDE_Z, who = "Outside (Blender filler)";
    for (const t of buckets[i]) { const z = zAt(t, x, y); if (z !== null && z > best + 0.5) { best = z; who = t.name; } }
    Z[i * NY + j] = best; N[i * NY + j] = who;
  }
  // steps between neighbours, grouped by (high part, low part)
  const groups = new Map();
  const add = (a, b, x, y) => {
    const dz = Z[a] - Z[b]; if (Math.abs(dz) < min) return;
    const [hi, lo] = dz > 0 ? [a, b] : [b, a], key = N[hi] + " | " + N[lo], s = Math.abs(dz);
    const g = groups.get(key) ?? { high: N[hi], low: N[lo], cells: 0, maxStep: 0, minStep: 1e9, x: [1e9, -1e9], y: [1e9, -1e9] };
    g.cells++; g.maxStep = Math.max(g.maxStep, s); g.minStep = Math.min(g.minStep, s);
    g.x = [Math.min(g.x[0], x), Math.max(g.x[1], x)]; g.y = [Math.min(g.y[0], y), Math.max(g.y[1], y)]; groups.set(key, g);
  };
  for (let i = 0; i < NX; i++) for (let j = 0; j < NY; j++) {
    if (i + 1 < NX) add(i * NY + j, (i + 1) * NY + j, X0 + (i + 1) * cell, Y0 + (j + 0.5) * cell);
    if (j + 1 < NY) add(i * NY + j, i * NY + j + 1, X0 + (i + 0.5) * cell, Y0 + (j + 1) * cell);
  }
  const edges = [...groups.values()].map((g) => ({ high: g.high, low: g.low, length_m: +(g.cells * cell / 1000).toFixed(1), minStep: Math.round(g.minStep), maxStep: Math.round(g.maxStep), x: g.x.map(Math.round), y: g.y.map(Math.round) }))
    .sort((a, b) => b.length_m * b.maxStep - a.length_m * a.maxStep);
  // bare patches: connected cells where the top surface is the site base itself
  const seen = new Uint8Array(NX * NY), bare_patches = [];
  for (let s = 0; s < NX * NY; s++) {
    if (seen[s] || N[s] !== "Site_Base") continue;
    const st = [s]; seen[s] = 1; let n = 0, xi = [1e9, -1e9], yj = [1e9, -1e9];
    while (st.length) {
      const c = st.pop(), i = Math.floor(c / NY), j = c % NY; n++;
      xi = [Math.min(xi[0], i), Math.max(xi[1], i)]; yj = [Math.min(yj[0], j), Math.max(yj[1], j)];
      for (const [a, b] of [[i + 1, j], [i - 1, j], [i, j + 1], [i, j - 1]]) {
        const k = a * NY + b; if (a >= 0 && b >= 0 && a < NX && b < NY && !seen[k] && N[k] === "Site_Base") { seen[k] = 1; st.push(k); }
      }
    }
    bare_patches.push({ area_m2: +(n * cell * cell / 1e6).toFixed(2), x: [X0 + xi[0] * cell, X0 + (xi[1] + 1) * cell], y: [Y0 + yj[0] * cell, Y0 + (yj[1] + 1) * cell] });
  }
  bare_patches.sort((a, b) => b.area_m2 - a.area_m2);
  return { model: objPath.replace(/\\/g, "/"), cell_mm: cell, min_step_mm: min, outside_z: OUTSIDE_Z, edges, bare_patches };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const [, , objPath, outPath, cell = "100", min = "100"] = process.argv;
  const r = groundEdges(objPath, { cell: +cell, min: +min });
  for (const e of r.edges) console.log(`${e.high.padEnd(26)} above ${e.low.padEnd(26)} ${String(e.length_m).padStart(6)} m  step ${e.minStep}-${e.maxStep} mm  x ${e.x[0]}..${e.x[1]}  y ${e.y[0]}..${e.y[1]}`);
  console.log("\nBARE SITE BASE PATCHES (nothing on them):");
  for (const p of r.bare_patches) console.log(`  ${String(p.area_m2).padStart(7)} m2  x ${p.x[0]}..${p.x[1]}  y ${p.y[0]}..${p.y[1]}`);
  if (outPath) fs.writeFileSync(outPath, JSON.stringify(r, null, 1));
}
