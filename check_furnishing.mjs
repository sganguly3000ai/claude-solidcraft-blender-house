// Checks for a furnishing design (furnishing.json from a Claude run) against the house data, by numbers:
// (1) every item inside its room and below the ceiling, none in an open-plan neighbour (the kitchen for living + dining); (2) items do not overlap each other (a rug
// under furniture, a lamp on a table and anything hung above 1.5 m are allowed); (3) a clear 900 x 900 mm square on
// the room side of every door; (4) the walkways MEASURED: the narrowest point of the widest route between each pair of
// doors / sliders / open neighbours, on a 25 mm grid; (4b) the clear depth in front of each fixture (--front-min N), (not taken from the reply); (5) SolidCraft's inspect.interference of
// every item (as its box) against the whole house model, with a control box through a wall that MUST be reported.
// Also writes a plan drawing (SVG) of the rooms, doors and items.
// Run: node check_furnishing.mjs furnishing_<rooms>.json [model] [--front-min mm]   (default model home_v7)
//   -> furnishing_<rooms>_checks.json, furnishing_<rooms>_plan.svg; SolidCraft test files in your system's temp folder
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { join, dirname, basename, resolve } from "node:path";

const CLI = process.env.SOLIDCRAFT_CLI ?? "solidcraft-cli";   // set SOLIDCRAFT_CLI to the full path if it is not on your PATH
const root = fileURLToPath(new URL(".", import.meta.url));
const argv = process.argv.slice(2), opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv.splice(i, 2)[1] : d; };
const FRONT_MIN = +opt("--front-min", 0);   // clear depth in front of fixtures (kitchen aisles 1000, bathroom 700); 0 = not checked
// one folder: furnishing_<rooms>.json goes with rooms_<rooms>.json (and existing_for_<rooms>.json, if there is one)
const [file, MODEL = "home_v7"] = argv;
const dir = dirname(resolve(file)), SUF = basename(file).replace(/^furnishing_|\.json$/g, "");
const F = JSON.parse(readFileSync(resolve(file), "utf8"));
const roomsFile = `rooms_${SUF}.json`;
const R = JSON.parse(readFileSync(join(dir, roomsFile), "utf8"));
const FZ = R.floor_z ?? 0;   // heights below are relative to this floor
// furniture already placed next door (existing_*.json, e.g. the dining for the kitchen): obstacles only, not checked here
const existing = [`existing_for_${SUF}.json`].filter((f) => existsSync(join(dir, f))).flatMap((f) => JSON.parse(readFileSync(join(dir, f), "utf8")).items);
const out = { model: MODEL, rooms_file: roomsFile, items: F.items.length, lights: (F.lights ?? []).length, existing_items: existing.length };

const inside = (p, poly) => {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > p[1]) !== (yj > p[1]) && p[0] < (xj - xi) * (p[1] - yi) / (yj - yi) + xi) c = !c;
  }
  return c;
};
const boxIn = (it, poly, tol = 2) => [[it.x[0] + tol, it.y[0] + tol], [it.x[1] - tol, it.y[0] + tol], [it.x[1] - tol, it.y[1] - tol], [it.x[0] + tol, it.y[1] - tol],
  [(it.x[0] + it.x[1]) / 2, (it.y[0] + it.y[1]) / 2]].every((p) => inside(p, poly));
const ov1 = (a, b) => Math.min(a[1], b[1]) - Math.max(a[0], b[0]);
const top = (it) => it.z_base + it.height;
const openNb = R.neighbours.filter((n) => /open/i.test(n.name));   // open-plan neighbours: walkable, but no items of this run in them
const roomOf = Object.fromEntries(R.rooms.map((r) => [r.name, r.outline]));

// (1) placement
const ids = F.items.map((i) => i.id);
out.placement = { duplicate_ids: ids.filter((v, i) => ids.indexOf(v) !== i), unknown_room: [], outside_room: [], above_ceiling: [], in_open_neighbour: [], bad_box: [] };
for (const it of F.items) {
  if (!(it.x?.[0] < it.x?.[1] && it.y?.[0] < it.y?.[1] && it.height > 0 && it.z_base >= FZ - 1)) { out.placement.bad_box.push(it.id); continue; }
  const poly = roomOf[it.room];
  if (!poly) out.placement.unknown_room.push(it.id);
  else if (!boxIn(it, poly) && !R.rooms.some((r) => boxIn(it, r.outline))) out.placement.outside_room.push(it.id);   // an item may straddle the open living/dining line
  if (top(it) > R.ceiling_z + 1) out.placement.above_ceiling.push({ id: it.id, top: top(it) });
  if (openNb.some((nb) => [[it.x[0] + 2, it.y[0] + 2], [it.x[1] - 2, it.y[1] - 2], [it.x[0] + 2, it.y[1] - 2], [it.x[1] - 2, it.y[0] + 2]].some((p) => inside(p, nb.outline)))) out.placement.in_open_neighbour.push(it.id);
}
// an item outside both outlines but inside their union (straddling the open edge between living and dining) is fine
out.placement.outside_room = out.placement.outside_room.filter((id) => {
  const it = F.items.find((i) => i.id === id); const N = 8;
  for (let a = 0; a <= N; a++) for (let b = 0; b <= N; b++) {
    const p = [it.x[0] + 2 + (it.x[1] - it.x[0] - 4) * a / N, it.y[0] + 2 + (it.y[1] - it.y[0] - 4) * b / N];
    if (!R.rooms.some((r) => inside(p, r.outline))) return true;
  }
  return false;
});
const P = out.placement;
P.pass = !P.duplicate_ids.length && !P.unknown_room.length && !P.outside_room.length && !P.above_ceiling.length && !P.in_open_neighbour.length && !P.bad_box.length;

// (2) item vs item overlaps (allowed: rugs <= 40 mm under things, one item standing on another, items hung above 1.5 m over floor items)
const flat = (it) => it.height <= 40 && it.z_base <= FZ + 5;
out.overlaps = [];
for (let i = 0; i < F.items.length; i++) for (let j = i + 1; j < F.items.length; j++) {
  const a = F.items[i], b = F.items[j];
  const dx = ov1(a.x, b.x), dy = ov1(a.y, b.y), dz = ov1([a.z_base, top(a)], [b.z_base, top(b)]);
  if (dx <= 1 || dy <= 1 || dz <= 1) continue;
  if (flat(a) || flat(b)) continue;
  out.overlaps.push({ a: a.id, b: b.id, mm: [Math.round(dx), Math.round(dy), Math.round(dz)] });
}
out.overlaps_pass = !out.overlaps.length;

// obstacles for walking: floor items taller than a rug, starting below 1.5 m. Curtains and blinds are drawn as boxes
// across their glass (closed); for walking they are taken as drawn back, and listed so the assumption is visible.
const soft = (it) => /curtain|blind|drape/i.test(it.kind + " " + (it.name ?? ""));
out.assumed_drawn_open = F.items.filter(soft).map((it) => it.id);
const blocks = [...F.items, ...existing].filter((it) => !flat(it) && it.z_base < FZ + 1500 && !soft(it));

// (3) door clear squares (900 x 900 on the room side, centred on the door)
const AREAS = [...R.rooms.map((r) => r.outline), ...openNb.map((n) => n.outline)];
const sideIn = (o) => { const cx = (o.x[0] + o.x[1]) / 2, cy = (o.y[0] + o.y[1]) / 2, wx = o.x[1] - o.x[0] < o.y[1] - o.y[0];
  return [1, -1].some((s) => AREAS.some((pl) => inside(wx ? [s > 0 ? o.x[1] + 100 : o.x[0] - 100, cy] : [cx, s > 0 ? o.y[1] + 100 : o.y[0] - 100], pl))); };
const doors = R.openings_touching_these_rooms.filter((o) => o.kind === "door" && sideIn(o));
const roomSide = (o) => {   // the opening rectangle sits in a wall: find which side is inside a room
  const cx = (o.x[0] + o.x[1]) / 2, cy = (o.y[0] + o.y[1]) / 2, wx = o.x[1] - o.x[0] < o.y[1] - o.y[0];
  const probe = (s) => wx ? [s > 0 ? o.x[1] + 100 : o.x[0] - 100, cy] : [cx, s > 0 ? o.y[1] + 100 : o.y[0] - 100];
  const s = AREAS.some((pl) => inside(probe(1), pl)) ? 1 : -1;
  return { wx, s, cx, cy };
};
out.door_squares = doors.map((o) => {
  const { wx, s, cx, cy } = roomSide(o);
  const sq = wx ? { x: s > 0 ? [o.x[1], o.x[1] + 900] : [o.x[0] - 900, o.x[0]], y: [cy - 450, cy + 450] }
                : { x: [cx - 450, cx + 450], y: s > 0 ? [o.y[1], o.y[1] + 900] : [o.y[0] - 900, o.y[0]] };
  const hit = blocks.filter((it) => ov1(it.x, sq.x) > 1 && ov1(it.y, sq.y) > 1).map((it) => it.id);
  return { door: o.id, square: sq, blocked_by: hit, pass: !hit.length };
});
out.door_squares_pass = out.door_squares.every((d) => d.pass);

// (4) walkways: free floor = the rooms + open-plan neighbours' floor + each doorway (and 500 mm beyond it), minus obstacles;
// distance to the nearest blocked cell (exact Euclidean transform), then the widest route between each pair
const G = 25, polys = AREAS;
const xs = polys.flat().map((p) => p[0]), ys = polys.flat().map((p) => p[1]);
const X0 = Math.min(...xs) - 600, Y0 = Math.min(...ys) - 600, NX = Math.ceil((Math.max(...xs) + 600 - X0) / G), NY = Math.ceil((Math.max(...ys) + 600 - Y0) / G);
const free = new Uint8Array(NX * NY), roomCell = new Uint8Array(NX * NY);
const stubs = doors.map((o) => {
  const { wx, s } = roomSide(o);
  return wx ? { x: s > 0 ? [o.x[0] - 500, o.x[1]] : [o.x[0], o.x[1] + 500], y: o.y } : { x: o.x, y: s > 0 ? [o.y[0] - 500, o.y[1]] : [o.y[0], o.y[1] + 500] };
});
for (let j = 0; j < NY; j++) for (let i = 0; i < NX; i++) {
  const p = [X0 + (i + 0.5) * G, Y0 + (j + 0.5) * G], k = j * NX + i;
  const inRoom = polys.some((pl) => inside(p, pl));
  const inStub = stubs.some((b) => p[0] > b.x[0] && p[0] < b.x[1] && p[1] > b.y[0] && p[1] < b.y[1]);
  const blocked = blocks.some((it) => p[0] > it.x[0] && p[0] < it.x[1] && p[1] > it.y[0] && p[1] < it.y[1]);
  free[k] = (inRoom || inStub) && !blocked ? 1 : 0; roomCell[k] = inRoom ? 1 : 0;
}
function edt1(f, n) {   // Felzenszwalb squared distance, 1-D
  const d = new Float64Array(n), v = new Int32Array(n), z = new Float64Array(n + 1); let k = 0; v[0] = 0; z[0] = -Infinity; z[1] = Infinity;
  for (let q = 1; q < n; q++) {
    let s; do { const r = v[k]; s = ((f[q] + q * q) - (f[r] + r * r)) / (2 * q - 2 * r); if (s <= z[k]) k--; else break; } while (k >= 0);
    k++; v[k] = q; z[k] = s; z[k + 1] = Infinity;
  }
  k = 0; for (let q = 0; q < n; q++) { while (z[k + 1] < q) k++; d[q] = (q - v[k]) ** 2 + f[v[k]]; } return d;
}
const INF = 1e12, D2 = new Float64Array(NX * NY);
for (let k = 0; k < NX * NY; k++) D2[k] = free[k] ? INF : 0;
for (let i = 0; i < NX; i++) { const col = new Float64Array(NY); for (let j = 0; j < NY; j++) col[j] = D2[j * NX + i]; const r = edt1(col, NY); for (let j = 0; j < NY; j++) D2[j * NX + i] = r[j]; }
for (let j = 0; j < NY; j++) { const r = edt1(D2.subarray(j * NX, (j + 1) * NX), NX); for (let i = 0; i < NX; i++) D2[j * NX + i] = r[i]; }
const clear = (k) => Math.sqrt(D2[k]) * G * 2;   // free width (mm) centred on the cell, approximately
const cell = (p) => Math.floor((p[1] - Y0) / G) * NX + Math.floor((p[0] - X0) / G);
const targets = Object.fromEntries(doors.map((o) => [o.id, [(o.x[0] + o.x[1]) / 2, (o.y[0] + o.y[1]) / 2]]));
for (const nb of openNb) {   // an open neighbour: its middle if that is clear floor, else its most open free cell
  const kx = nb.outline.map((p) => p[0]), ky = nb.outline.map((p) => p[1]); let p = [(Math.min(...kx) + Math.max(...kx)) / 2, (Math.min(...ky) + Math.max(...ky)) / 2];
  if (!free[cell(p)] || clear(cell(p)) < 900) { let best = null; for (let k = 0; k < NX * NY; k++) if (free[k] && inside([X0 + (k % NX + 0.5) * G, Y0 + (Math.floor(k / NX) + 0.5) * G], nb.outline)) {
    if (!best || clear(k) > best[0]) best = [clear(k), [X0 + (k % NX + 0.5) * G, Y0 + (Math.floor(k / NX) + 0.5) * G]]; } if (best) p = best[1]; }
  targets[nb.name.split(" ")[0]] = p;
}
function widest(a, b) {   // maximin route; the width counts only cells in the rooms (a doorway's own width is not the walkway)
  const best = new Float64Array(NX * NY).fill(-1), from = new Int32Array(NX * NY).fill(-1), s = cell(a), t = cell(b);
  const w = (k) => (roomCell[k] ? clear(k) : 1e9);
  const heap = [[w(s), s]]; best[s] = w(s);
  const push = (e) => { heap.push(e); let i = heap.length - 1; while (i > 0) { const p = (i - 1) >> 1; if (heap[p][0] >= heap[i][0]) break; [heap[p], heap[i]] = [heap[i], heap[p]]; i = p; } };
  const pop = () => { const r = heap[0], l = heap.pop(); if (heap.length) { heap[0] = l; let i = 0; for (;;) { const a2 = 2 * i + 1, b2 = a2 + 1; let m = i; if (a2 < heap.length && heap[a2][0] > heap[m][0]) m = a2; if (b2 < heap.length && heap[b2][0] > heap[m][0]) m = b2; if (m === i) break; [heap[m], heap[i]] = [heap[i], heap[m]]; i = m; } } return r; };
  while (heap.length) {
    const [v, k] = pop(); if (v < best[k]) continue; if (k === t) break;
    const i = k % NX, j = (k - i) / NX;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const ni = i + di, nj = j + dj; if (ni < 0 || nj < 0 || ni >= NX || nj >= NY) continue;
      const n = nj * NX + ni; if (!free[n]) continue;
      const nv = Math.min(v, w(n)); if (nv > best[n]) { best[n] = nv; from[n] = k; push([nv, n]); }
    }
  }
  if (best[t] < 0) return { narrowest_mm: 0, connected: false };
  let k = t, worst = Infinity, at = null;
  while (k !== s && k >= 0) { if (roomCell[k] && clear(k) < worst) { worst = clear(k); at = [X0 + (k % NX + 0.5) * G, Y0 + (Math.floor(k / NX) + 0.5) * G]; } k = from[k]; }
  return { narrowest_mm: Math.round(worst), at: at && at.map(Math.round), connected: true };
}
const names = Object.keys(targets);
out.walkways = [];
for (let i = 0; i < names.length; i++) for (let j = i + 1; j < names.length; j++) out.walkways.push({ between: [names[i], names[j]], ...widest(targets[names[i]], targets[names[j]]) });
const MIN = 900 - G;   // one grid step of rounding
out.walkways_min_mm = MIN + G;
out.walkways_pass = out.walkways.every((w) => w.connected && w.narrowest_mm >= MIN);
out.walkways_claimed = F.walkways ?? [];

// (4b) clear depth in front of each fixture that stands on (or hangs low over) the floor: walk from the middle and the
// quarter points of its front face straight out until a blocked cell; the smallest of the three
const FIX = /sink|hob|cooktop|oven|fridge|freezer|dishwasher|wc|toilet|basin|vanity|shower|bath|island|base cabinet|tall cabinet|tall unit/i;
const N4 = { north: [0, 1], south: [0, -1], east: [1, 0], west: [-1, 0] };
const onOther = (it) => F.items.some((o) => o !== it && o.x[0] <= it.x[0] && o.x[1] >= it.x[1] && o.y[0] <= it.y[0] && o.y[1] >= it.y[1] && o.z_base + o.height <= it.z_base + 1);
out.front_min_mm = FRONT_MIN;
out.front_clearances = F.items.filter((it) => FIX.test(it.kind) && N4[(it.faces ?? "").toLowerCase()] && it.z_base < FZ + 700 && !onOther(it)).map((it) => {
  const [dx, dy] = N4[it.faces.toLowerCase()];
  const starts = dx ? [0.25, 0.5, 0.75].map((t) => [dx > 0 ? it.x[1] + G / 2 : it.x[0] - G / 2, it.y[0] + (it.y[1] - it.y[0]) * t])
                    : [0.25, 0.5, 0.75].map((t) => [it.x[0] + (it.x[1] - it.x[0]) * t, dy > 0 ? it.y[1] + G / 2 : it.y[0] - G / 2]);
  const depth = Math.min(...starts.map((p) => { let d = 0; for (;;) { const q = [p[0] + dx * d, p[1] + dy * d], i = Math.floor((q[0] - X0) / G), j = Math.floor((q[1] - Y0) / G);
    if (i < 0 || j < 0 || i >= NX || j >= NY || !free[j * NX + i] || !roomCell[j * NX + i]) return d; d += G; } }));
  const corner = /corner/i.test(it.kind + " " + (it.name ?? ""));   // a corner unit's far end sits behind the next run by design
  return { id: it.id, kind: it.kind, faces: it.faces, clear_mm: depth, ...(corner ? { corner: true } : {}), pass: !FRONT_MIN || corner || depth >= FRONT_MIN - G };
});
out.front_pass = out.front_clearances.every((c) => c.pass);

// (5) SolidCraft: every item as a box in the house model, inspect.interference over all pairs, + a control box
const tmp = join(tmpdir(), "dream-it-checks", "furnishing"); mkdirSync(tmp, { recursive: true });
const base = JSON.parse(readFileSync(join(root, `${MODEL}_script.json`), "utf8")).commands;
const itemBoxes = F.items.map((it) => ({ command: "solid.box", params: { corner: [it.x[0], it.y[0], it.z_base], length: String(it.x[1] - it.x[0]), width: String(it.y[1] - it.y[0]), height: String(it.height), operation: "new", name: "F_" + it.id, body_name: "F_" + it.id } }));
function interference(extra, tag) {
  const f = join(tmp, `${tag}.json`), o = join(tmp, `${tag}_res.json`);
  writeFileSync(f, JSON.stringify({ commands: [...base, ...itemBoxes, ...extra, { command: "inspect.interference", params: {} }] }));
  execFileSync(CLI, ["run", f, "--results", "--quiet", "--json-out", o], { stdio: "ignore", maxBuffer: 1 << 26 });
  const res = JSON.parse(readFileSync(o, "utf8")), list = res.results ?? res;
  const r = (Array.isArray(list) ? list : Object.values(list)).at(-1); return r.result ?? r;
}
const pairs = (x) => x.interferences.map((i) => ({ a: i.a, b: i.b, m3: +((i.volume ?? i.volume_mm3) / 1e9).toFixed(6) }));
const wn = R.openings_touching_these_rooms.find((o) => o.id === "W07");   // control: a 300 mm cube half into the west wall beside W07
const probe = { command: "solid.box", params: { center: [300, (wn ? wn.y[0] : 6300) - 400, 1000], length: "300", width: "300", height: "300", operation: "new", name: "Probe", body_name: "Probe" } };
const main = interference([], "interf_furnished"), ctrl = interference([probe], "interf_furnished_control");
const isF = (n) => /^F_/.test(n);
const found = pairs(main).filter((p) => isF(p.a) || isF(p.b));
const hits = pairs(ctrl).filter((p) => p.a === "Probe" || p.b === "Probe");
const stack = (p) => isF(p.a) && isF(p.b);   // item on item: judged by check (2), not here
out.solidcraft = { tool: "SolidCraft inspect.interference", bodies_checked: main.checked, pairs_intersected: main.pairs_intersected, unchecked: main.unchecked,
  control: { hits, ok: hits.length > 0 },
  item_vs_house_over_1_litre: found.filter((p) => !stack(p) && p.m3 >= 0.001), item_vs_house_contact: found.filter((p) => !stack(p) && p.m3 < 0.001).length,
  item_vs_item: found.filter(stack) };
out.solidcraft.pass = out.solidcraft.control.ok && !out.solidcraft.item_vs_house_over_1_litre.length && !main.unchecked.length;

out.pass = P.pass && out.overlaps_pass && out.door_squares_pass && out.walkways_pass && out.front_pass && out.solidcraft.pass;
writeFileSync(join(dir, `furnishing_${SUF}_checks.json`), JSON.stringify(out, null, 2) + "\n");

// plan drawing: rooms, walls' inside faces, openings, door squares, items (rugs pale), lights, the narrowest points
const S = 0.1, W = (Math.max(...xs) - Math.min(...xs) + 1200) * S, H = (Math.max(...ys) - Math.min(...ys) + 1200) * S;
const X = (x) => ((x - (Math.min(...xs) - 600)) * S).toFixed(1), Y = (y) => (H - (y - (Math.min(...ys) - 600)) * S).toFixed(1);
const rect = (b, st) => `<rect x="${X(b.x[0])}" y="${Y(b.y[1])}" width="${((b.x[1] - b.x[0]) * S).toFixed(1)}" height="${((b.y[1] - b.y[0]) * S).toFixed(1)}" ${st}/>`;
const svg = [`<svg xmlns="http://www.w3.org/2000/svg" width="${W.toFixed(0)}" height="${H.toFixed(0)}" viewBox="0 0 ${W.toFixed(0)} ${H.toFixed(0)}" font-family="Arial" font-size="9">`,
  `<rect width="100%" height="100%" fill="#ffffff"/>`,
  ...polys.map((pl, i) => `<polygon points="${pl.map((p) => X(p[0]) + "," + Y(p[1])).join(" ")}" fill="${i < R.rooms.length ? "#f4efe6" : "#eeeeee"}" stroke="#222" stroke-width="2"/>`),
  ...R.openings_touching_these_rooms.map((o) => rect(o, `fill="${o.kind === "door" ? "#ffffff" : "#bfe3ff"}" stroke="#2a6fb0" stroke-width="1"`)),
  ...out.door_squares.map((d) => rect(d.square, `fill="none" stroke="${d.pass ? "#3a9a3a" : "#d02020"}" stroke-dasharray="3,2" stroke-width="0.8"`)),
  ...F.items.slice().sort((a, b) => (flat(b) ? 1 : 0) - (flat(a) ? 1 : 0)).map((it) => rect(it, `fill="${it.colour ?? "#999"}" fill-opacity="${flat(it) ? 0.35 : it.z_base >= 1500 ? 0.15 : 0.85}" stroke="#333" stroke-width="0.6"`) +
    `<text x="${X((it.x[0] + it.x[1]) / 2)}" y="${Y((it.y[0] + it.y[1]) / 2)}" text-anchor="middle" fill="#000">${it.id}</text>`),
  ...(F.lights ?? []).map((l) => `<circle cx="${X(l.x)}" cy="${Y(l.y)}" r="3" fill="#f0b000" stroke="#805000" stroke-width="0.5"/>`),
  ...out.walkways.filter((w) => w.at).map((w) => `<circle cx="${X(w.at[0])}" cy="${Y(w.at[1])}" r="${(w.narrowest_mm / 2 * S).toFixed(1)}" fill="none" stroke="${w.narrowest_mm >= MIN ? "#3a9a3a" : "#d02020"}" stroke-width="0.6"/>`),
  ...R.openings_touching_these_rooms.map((o) => `<text x="${X((o.x[0] + o.x[1]) / 2)}" y="${Y((o.y[0] + o.y[1]) / 2) - 3}" text-anchor="middle" fill="#2a6fb0">${o.id}</text>`),
  `<text x="8" y="14" font-size="12">${out.pass ? "ALL CHECKS PASS" : "CHECKS: SEE furnishing_checks.json"} (plan, 1 px = 10 mm; north up)</text>`, `</svg>`];
writeFileSync(join(dir, `furnishing_${SUF}_plan.svg`), svg.join("\n"));

console.log(`placement ${P.pass} | overlaps ${out.overlaps.length} | door squares ${out.door_squares.filter((d) => !d.pass).map((d) => d.door).join(",") || "all clear"} | ` +
  `walkways narrowest ${out.walkways.length ? Math.min(...out.walkways.map((w) => w.narrowest_mm)) : "-"} mm (${out.walkways.filter((w) => w.narrowest_mm < MIN).length} under ${MIN + G}) | ` +
  `fronts ${FRONT_MIN ? (out.front_clearances.filter((c) => !c.pass).map((c) => c.id + " " + c.clear_mm).join(",") || "all >= " + FRONT_MIN) : "not set"} (min ${out.front_clearances.length ? Math.min(...out.front_clearances.map((c) => c.clear_mm)) : "-"} mm) | SolidCraft ${main.checked} bodies, item-house overlaps ${out.solidcraft.item_vs_house_over_1_litre.length}, contact ${out.solidcraft.item_vs_house_contact}, control ${out.solidcraft.control.ok} | PASS ${out.pass}`);
