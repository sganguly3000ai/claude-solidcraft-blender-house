// Dream It Design It: the v4 home as a deterministic SolidCraft script, built ONLY from the design data Claude wrote
// (design.json, the same building as its drawings). Same input -> same model, every time.
// What is modelled: every wall (openings cut through), glass in windows and glass doors, external door panels, slabs
// (stair wells cut), the three flat roofs, the street balcony with its glass balustrade, piers, the steel post, the
// entry cheek wall, both stairs, and the landscape (site base, plinths under the slabs, lawns, paving, gravel, the
// driveway ramp, raised beds, entry steps, trees and shrubs as simple low-poly shapes). Colours are view-only.
// Simplifications (logged in DESIGN_LOG.md): beds are solid blocks up to their edge top; plants stand on that top; the
// west front lawn's bank and the forecourt link's slope are flat; the cheek wall goes down to the site base; soffit
// lights, fascias and timber soffits are not separate bodies (the roofs' 400 mm thickness is the fascia).
// Writes home_v4_script.json + home_v4_expected.json. Then:
//   solidcraft-cli run home_v4_script.json --out home_v4.obj --save home_v4.solidcraft
// With an addition file (2026-10-25: node build_home.mjs addition.json) the same v4
// house is built, then the addition (build_addition.mjs) on top, written as the addition's model_name (home_v5).
// Without one, the output is the v4 script exactly as before.
import { readFileSync, writeFileSync } from "node:fs";
import { buildAddition } from "./build_addition.mjs";
import { buildGarden } from "./build_garden.mjs";
import { buildGround } from "./build_ground.mjs";

const P = (p) => new URL(p, import.meta.url);
const D = JSON.parse(readFileSync(P("./design.json"), "utf8"));
// data files on top of v4 (2026-10-25): each may list files it builds on ("includes", e.g. the garden includes the
// addition); the model is named after the last file given
const FILES = [];
const load = (f) => { const j = JSON.parse(readFileSync(f, "utf8")); for (const i of j.includes ?? []) load(new URL(`./${i}`, import.meta.url)); FILES.push(j); };
for (const f of process.argv.slice(2)) load(f);
const ADD = FILES.find((f) => f.top_boxes) ?? null, GARDEN_DATA = FILES.find((f) => f.beds) ?? null, GROUND_DATA = FILES.find((f) => f.pieces) ?? null;
const OUT = FILES.length ? FILES.at(-1).model_name : "home_v4";
const cmds = [], expected = {}, colours = {}, BB = {};   // BB: each new body's extents (for the clips' volumes)
const r = (v) => Math.round(v * 10) / 10;
const add = (command, params) => cmds.push({ command, params });
const id = (s) => s.replace(/[^A-Za-z0-9]+/g, "_");
const area = (pts) => Math.abs(pts.reduce((s, [x, y], i) => { const [u, v] = pts[(i + 1) % pts.length]; return s + x * v - u * y; }, 0)) / 2;
const paint = (name, colour, pieces = 0) => (colours[colour] ??= []).push(name, ...Array.from({ length: pieces }, (_, i) => `${name} (${i + 1})`));

// a box from extents (mm); new body, or a cut into targets. zExpr / hExpr: the bottom / height as SolidCraft
// expressions (used by the addition to follow a parameter); the numbers z0, z1 are their default values
function box(name, x0, x1, y0, y1, z0, z1, { cut, expect = true, zExpr, hExpr } = {}) {
  [x0, x1] = [Math.min(x0, x1), Math.max(x0, x1)]; [y0, y1] = [Math.min(y0, y1), Math.max(y0, y1)];
  add("solid.box", { corner: [r(x0), r(y0), zExpr ?? r(z0)], length: String(r(x1 - x0)), width: String(r(y1 - y0)), height: hExpr ?? String(r(z1 - z0)),
    ...(cut ? { operation: "cut", targets: cut } : { operation: "new", name, body_name: name }) });
  if (!cut && expect) expected[name] = (x1 - x0) * (y1 - y0) * (z1 - z0);
  if (!cut) BB[name] = { x0, x1, y0, y1, z0, z1 };
}
// a plan polygon extruded from z0 to z1; new body, or a cut into targets
let nSketch = 0;
function poly(name, pts, z0, z1, { cut, expect = true } = {}) {
  const sk = `Sk${++nSketch}`;
  add("sketch.create", { plane: { origin: [0, 0, z0], x_dir: [1, 0, 0], y_dir: [0, 1, 0] }, name: sk });
  add("sketch.line", { points: pts.map(([x, y]) => [r(x), r(y)]), closed: true });
  add("solid.extrude", { sketch: sk, distance: String(r(z1 - z0)), ...(cut ? { operation: "cut", targets: cut } : { operation: "new", name, body_name: name }) });
  if (!cut && expect) expected[name] = area(pts) * (z1 - z0);
  if (!cut) { const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]); BB[name] = { x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys), z0, z1 }; }
}
const octagon = ([cx, cy], d) => Array.from({ length: 8 }, (_, i) => [cx + (d / 2) * Math.cos((i + 0.5) * Math.PI / 4), cy + (d / 2) * Math.sin((i + 0.5) * Math.PI / 4)]);

// WALLS: centre line + thickness -> box; openings cut through the full thickness (+50 each side), glass and door panels in them
const WALL = {};
for (const f of D.floors) for (const w of f.walls) {
  const ax = w.start[1] === w.end[1] ? "x" : "y", t = w.thickness / 2, n = `W_${id(w.id)}`;
  const b = ax === "x" ? { x0: Math.min(w.start[0], w.end[0]), x1: Math.max(w.start[0], w.end[0]), y0: w.start[1] - t, y1: w.start[1] + t }
                       : { x0: w.start[0] - t, x1: w.start[0] + t, y0: Math.min(w.start[1], w.end[1]), y1: Math.max(w.start[1], w.end[1]) };
  Object.assign(b, { ax, z0: w.z_base, z1: w.z_base + w.height, w, n });
  box(n, b.x0, b.x1, b.y0, b.y1, b.z0, b.z1); WALL[w.id] = b;
  b.colour = { charcoal_panel: "#2b2d31", stone: "#a89f8f", interior: "#e6e1d8" }[w.material] ?? "#2b2d31"; b.splits = 0;
}
const PANE = 24, LEAF = 50;
for (const o of D.openings) {
  const b = WALL[o.wall], w = b.w, M = 50;
  const dir = (b.ax === "x" ? w.end[0] - w.start[0] : w.end[1] - w.start[1]) >= 0 ? 1 : -1;
  const s = (b.ax === "x" ? w.start[0] : w.start[1]) + dir * o.position, a0 = Math.min(s, s + dir * o.width), a1 = Math.max(s, s + dir * o.width);
  const z0 = Math.max(o.sill_z, b.z0), z1 = Math.min(o.head_z, b.z1);
  if (b.ax === "x") box(null, a0, a1, b.y0 - M, b.y1 + M, z0, z1, { cut: [b.n] }); else box(null, b.x0 - M, b.x1 + M, a0, a1, z0, z1, { cut: [b.n] });
  expected[b.n] -= (a1 - a0) * (b.ax === "x" ? b.y1 - b.y0 : b.x1 - b.x0) * (z1 - z0);
  if (z0 <= b.z0 && z1 >= b.z1) b.splits++;   // cut right through: SolidCraft keeps "W_X" and adds "W_X (1)"... for the pieces
  const glass = o.kind === "window" || /glass/i.test(o.name), external = w.material !== "interior";
  if (!glass && !external) continue;   // inside doors stay open
  const toDoor = ADD?.house_changes?.glass_to_door?.includes(o.id);   // addition: this glass becomes a glass door leaf
  const th = glass && !toDoor ? PANE : LEAF, n = `${glass && !toDoor ? "Glass" : "Door"}_${id(o.id)}`;
  const c = b.ax === "x" ? (b.y0 + b.y1) / 2 : (b.x0 + b.x1) / 2;
  if (b.ax === "x") box(n, a0, a1, c - th / 2, c + th / 2, z0, z1); else box(n, c - th / 2, c + th / 2, a0, a1, z0, z1);
  paint(n, glass ? "#9cc3d6" : "#1f2023");
}

// SLABS (stair wells cut), plinths under them down to the site base, ROOFS, BALCONY + glass balustrade
const BASE_TOP = -650;
for (const s of D.slabs) {
  const n = `S_${id(s.id)}`, z0 = s.top_z - s.thickness;
  poly(n, s.outline, z0, s.top_z); paint(n, "#c9c6bf");
  for (const h of s.openings ?? []) { poly(null, h, z0 - 50, s.top_z + 50, { cut: [n] }); expected[n] -= area(h) * s.thickness; }
  if (s.top_z <= 0) { const p = `Plinth_${id(s.id)}`; poly(p, s.outline, BASE_TOP, z0); paint(p, "#8d8a84"); }   // ground-bearing slabs
}
// a rectangular roof is a box (its height can then follow a parameter: a sketch plane's position cannot)
const rect = (o) => o.length === 4 && o.every(([x, y], i) => { const [u, v] = o[(i + 1) % 4]; return x === u || y === v; });
for (const f of D.roofs) {
  const n = `R_${id(f.id)}`, xs = f.outline.map((q) => q[0]), ys = f.outline.map((q) => q[1]);
  if (rect(f.outline)) box(n, Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys), f.underside_z, f.top_z);
  else poly(n, f.outline, f.underside_z, f.top_z);
  paint(n, "#3a3d42");
}
for (const b of D.balconies) { const n = `B_${id(b.id)}`; poly(n, b.outline, b.soffit_z, b.deck_z); paint(n, "#3a3d42"); }
for (const bl of D.balustrades) {
  const deck = D.balconies.find((b) => b.id === bl.on).deck_z, G = 20;
  bl.segments.forEach(([[x0, y0], [x1, y1]], i) => {
    const n = `Glass_${id(bl.id)}_${i + 1}`;
    // each pane stands on the deck just inside the balcony's outer edge; the side panes stop at the front pane
    if (y0 === y1) box(n, x0, x1, y0, y0 + G, deck, bl.top_z);
    else box(n, x0 === 0 ? 0 : x0 - G, x0 === 0 ? G : x0, Math.min(y0, y1) + G, Math.max(y0, y1), deck, bl.top_z);
    paint(n, "#9cc3d6");
  });
}
for (const p of D.piers_and_posts) {
  const n = `Pier_${id(p.id)}`;
  if (p.outline) poly(n, p.outline, p.z_base, p.top_z);
  else box(n, p.centre[0] - p.size[0] / 2, p.centre[0] + p.size[0] / 2, p.centre[1] - p.size[1] / 2, p.centre[1] + p.size[1] / 2, p.z_base, p.top_z);
  paint(n, p.material === "stone" ? "#a89f8f" : "#1f2023");
}
for (const w of D.feature_walls) {   // the cheek wall stands on the site base (its own base -150 would float over the forecourt)
  const n = `FW_${id(w.id)}`, t = w.thickness / 2;
  if (w.start[0] === w.end[0]) box(n, w.start[0] - t, w.start[0] + t, w.start[1], w.end[1], BASE_TOP, w.top_z);
  else box(n, w.start[0], w.end[0], w.start[1] - t, w.start[1] + t, BASE_TOP, w.top_z);
  paint(n, "#a89f8f");
}

// STAIRS: one solid block per tread, from the stair's bottom up to that tread (the last riser lands on the floor slab)
function stair(prefix, s, colour, zFloor = s.z_bottom) {
  for (let i = 0; i < s.goings; i++) {
    const n = `${prefix}_${i + 1}`, y0 = s.first_riser_y + i * s.going;
    box(n, s.x_from, s.x_to, y0, y0 + s.going, zFloor, s.z_bottom + (i + 1) * s.riser_height); paint(n, colour);
  }
}
for (const s of D.stairs) stair(`Stair_${id(s.id)}`, s, "#b08a5a");

// LANDSCAPE
const L = D.landscape;
box("Site_Base", -3000, 30000, -8000, 20000, BASE_TOP - 300, BASE_TOP); paint("Site_Base", "#668f44");   // ground: the plot outside the drawn lawns reads as grass
const FRONT = -600, GARDEN = -150;
for (const l of L.lawns) { const n = `Lawn_${id(l.id)}`; poly(n, l.outline, BASE_TOP, l.id === "L3" ? GARDEN : FRONT); paint(n, "#6f9a4a"); }
for (const p of L.paved_areas.filter((q) => q.outline)) {
  const n = `Pave_${id(p.id)}`, top = typeof p.z === "number" ? p.z : FRONT;   // the forecourt link's 1:30 rise is left flat
  poly(n, p.outline, BASE_TOP, top); paint(n, /gravel/.test(p.material) ? "#9a9a94" : "#b8b6ae");
}
{ // the driveway: a side profile (y, z) extruded east across its width: -600 at the street rising 1:11 to -150 at y = -2900
  const d = L.driveway, xs = d.outline.map((q) => q[0]), ys = d.outline.map((q) => q[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys), yRamp = -2900;
  const prof = [[y0, BASE_TOP], [y1, BASE_TOP], [y1, GARDEN], [yRamp, GARDEN], [y0, FRONT]];
  add("sketch.create", { plane: { origin: [x0, 0, 0], x_dir: [0, 1, 0], y_dir: [0, 0, 1] }, name: "SkDrive" });
  add("sketch.line", { points: prof, closed: true });
  add("solid.extrude", { sketch: "SkDrive", distance: String(x1 - x0), operation: "new", name: "Driveway", body_name: "Driveway" });
  expected.Driveway = area(prof) * (x1 - x0); paint("Driveway", "#55575a");
}
for (const b of L.planting_beds) { const n = `Bed_${id(b.id)}`; poly(n, b.outline, BASE_TOP, b.edge_top_z); paint(n, "#a89f8f"); }
for (const s of L.steps) stair(`Step_${id(s.id)}`, { ...s, goings: s.treads, z_bottom: s.z_bottom }, "#b8b6ae", BASE_TOP);
// plants stand on whatever is under them: a bed top (-150) or the lawn
const groundAt = ([x, y]) => {
  const inside = (pts) => pts.reduce((c, [ax, ay], i) => { const [bx, by] = pts[(i + 1) % pts.length]; return ((ay > y) !== (by > y)) && x < ((bx - ax) * (y - ay)) / (by - ay) + ax ? !c : c; }, false);
  if (L.planting_beds.some((b) => inside(b.outline))) return GARDEN;
  return L.lawns.find((l) => inside(l.outline))?.id === "L3" ? GARDEN : FRONT;
};
for (const t of L.trees) {
  const n = `Tree_${id(t.id)}`, z = groundAt(t.position), trunk = 0.4 * t.height, [x, y] = t.position;
  box(`${n}_Trunk`, x - 80, x + 80, y - 80, y + 80, z, z + trunk); paint(`${n}_Trunk`, "#5a4632");
  poly(`${n}_Crown`, octagon(t.position, t.spread), z + trunk, z + t.height); paint(`${n}_Crown`, "#557a3a");
}
for (const s of L.shrubs) { const n = `Shrub_${id(s.id)}`, z = groundAt(s.position); poly(n, octagon(s.position, s.spread), z, z + s.height); paint(n, /grass/.test(s.label) ? "#9aa35a" : "#4f7a3c"); }

// CLIPS: where the design data puts two parts in the same space, the lower-priority one gives way (keep_tools)
// (found by the first overlap check, 2026-10-23; each one is logged in DESIGN_LOG.md)
const CLIPS = [
  ["W_G_I1", "Stair_ST1_15"],   // the main stair's top tread runs through the hall wall's line (y 4880-5000): the wall opens for it
  ["W_F_STEP", "R_RF_1"],       // the roof-step wall (y 4790-5090) and the lower roof (to y 4940) share 150 mm: the roof runs on
  ["W_F_STEP", "W_F_W2"],       // ... and the step wall's ends sit inside the first-floor end walls: the end walls run on
  ["W_F_STEP", "W_F_E2"],
];
// expected volume: minus the overlap of the two extents (exact here: every tool is a box, or a polygon that covers the
// whole overlap; the clips' overlaps are disjoint)
const ovl = (a, b) => ["x", "y", "z"].reduce((v, k) => v * Math.max(0, Math.min(a[k + "1"], b[k + "1"]) - Math.max(a[k + "0"], b[k + "0"])), 1);
for (const [target, tool] of CLIPS) { add("solid.combine", { target, tools: [tool], operation: "cut", keep_tools: true }); expected[target] -= ovl(BB[target], BB[tool]); }
for (const b of Object.values(WALL)) paint(b.n, b.colour, b.splits);
if (ADD) buildAddition(ADD, { box, paint, expected, BB, BASE_TOP, ovl, area, D });
if (GARDEN_DATA) buildGarden(GARDEN_DATA, { box, poly, paint, expected, BB, BASE_TOP, area, D });
const REMOVED = GROUND_DATA ? buildGround(GROUND_DATA, { add, box, paint, expected, BB, BASE_TOP, area, ovl, D }) : [];   // bodies the ground removes (no colour)

// PARAMETERS (Sam 2026-10-23: only parts a viewer sees and understands at once). Wired into the commands as SolidCraft
// expressions, so changing one in the app's Parameters panel rebuilds every part that depends on it. At the default
// values (design.json's own) the geometry is exactly the same as without them.
//   upper_roof_top   (6900; >= 6800): the upper roof, the first-floor north and end walls under it, the roof-step wall
//   street_overhang  (1500; 0-3900): how far the lower roof reaches out over the street front of the house
//   terrace_depth    (3900; 1500-9000): the garden terrace's roof, paving slab and its plinth, the two stone piers, the
//                    steel post, and the garden lawn's edge round it
{
  const U = D.levels.upper_roof_top, RF1 = D.roofs.find((f) => f.id === "RF-1"), OV = -Math.min(...RF1.outline.map((q) => q[1]).filter((y) => y > -3000));
  const TE = D.slabs.find((s) => s.id === "SL-TE"), Y0 = TE.outline[0][1], DEPTH = Math.max(...TE.outline.map((q) => q[1])) - Y0;
  const wired = {}, w = (what) => (wired[what] = (wired[what] ?? 0) + 1);
  const boxOf = (n) => cmds.find((c) => c.command === "solid.box" && c.params.body_name === n)?.params;
  const lineOf = (n) => { const sk = cmds.find((c) => c.command === "solid.extrude" && c.params.body_name === n).params.sketch;
    return cmds[cmds.findIndex((c) => c.command === "sketch.create" && c.params.name === sk) + 1].params; };
  // upper roof: the roof box sits on the walls, the walls rise to its underside
  const RF2 = boxOf("R_RF_2"); RF2.corner[2] = "upper_roof_top - 400"; w("upper roof");
  for (const n of ["W_F_N", "W_F_W2", "W_F_E2"]) { const p = boxOf(n); p.height = `upper_roof_top - 400 - ${p.corner[2]}`; w("walls under the upper roof"); }
  { const p = boxOf("W_F_STEP"); p.height = `upper_roof_top - 400 - ${p.corner[2]}`; w("roof-step wall"); }
  // street overhang: the lower roof's street edge over the house
  for (const pt of lineOf("R_RF_1").points) if (pt[1] === -OV) { pt[1] = "-street_overhang"; w("lower roof street edge"); }
  // terrace depth: everything measured from the house's north wall line (y = Y0)
  const ty = (y) => (y - Y0 === DEPTH ? `${Y0} + terrace_depth` : `${Y0} + terrace_depth - ${r(Y0 + DEPTH - y)}`);
  for (const n of ["S_SL_TE", "Plinth_SL_TE", "Pier_PR_2", "Pier_PR_3", "Lawn_L3"])
    for (const pt of lineOf(n).points) if (pt[1] > Y0 && pt[1] <= Y0 + DEPTH) { pt[1] = ty(pt[1]); w(`terrace: ${n}`); }
  { const p = boxOf("R_RF_3"); p.width = "terrace_depth"; w("terrace roof"); }
  { const p = boxOf("Pier_PO_1"); p.corner[1] = ty(p.corner[1]); w("steel post"); }
  cmds.unshift(
    { command: "parameters.add", params: { name: "upper_roof_top", expression: String(U), unit: "mm", comment: "top of the upper (north) roof; >= 6800 (window heads 6400)" } },
    { command: "parameters.add", params: { name: "street_overhang", expression: String(OV), unit: "mm", comment: "lower roof overhang over the house's street front; 0-3900" } },
    { command: "parameters.add", params: { name: "terrace_depth", expression: String(DEPTH), unit: "mm", comment: "garden terrace depth from the house's north wall; 1500-9000" } });
  console.log("parameters wired:", JSON.stringify(wired));
}
for (const [colour, bodies] of Object.entries(colours)) add("appearance.assign", { bodies: bodies.filter((b) => !REMOVED.includes(b)), color: colour });

writeFileSync(P(`./${OUT}_script.json`), JSON.stringify({ commands: cmds }, null, 2));
writeFileSync(P(`./${OUT}_expected.json`), JSON.stringify({ bodies: Object.fromEntries(Object.entries(expected).map(([k, v]) => [k, Math.round(v)])), clipped: CLIPS }, null, 2));
console.log(cmds.length, "commands,", Object.keys(expected).length, "bodies");
