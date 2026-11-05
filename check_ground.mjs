// Check (6), the ground (Sam 2026-10-25: "we do not want any landscaped area that look unreal - the lawns with grasses
// should all blend into their srroundings"): no SOFT ground (lawn, bed soil, the bare site base) may stand 100 mm or
// more above what is next to it, and no bare site base may show inside the plot. Built things (stone edges, steps,
// paving, the driveway, slabs, plinths, walls) may have a vertical face. Uses ground_edges.mjs.
// Run: node check_ground.mjs [model]  -> <model>_ground.json (default home_v4). Models before
// home_v7 are expected to FAIL: they are the "before".
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { groundEdges } from "./ground_edges.mjs";

const NAME = process.argv[2] ?? "home_v4", MIN = 100;
const root = fileURLToPath(new URL(".", import.meta.url));
const SOFT = /^(Lawn_|G_Lawn_|Gr_Lawn_|Gr_Bank_|Site_Base$)|_Soil$/;
// allowed on purpose (each with its reason; reported, not counted)
const ALLOWED = [{ high: "Lawn_L3", low: "G_Step_1", maxStep: 150, why: "the top riser of the garden steps (Stage 3): one normal 150 mm step from the upper lawn" }];
const r = groundEdges(join(root, `${NAME}.obj`), { min: MIN });
const allowed = (e) => ALLOWED.find((a) => a.high === e.high && a.low === e.low && e.maxStep <= a.maxStep);
const cliffs = r.edges.filter((e) => SOFT.test(e.high) && !allowed(e));
const out = { model: NAME, rule: `no soft ground ${MIN} mm or more above its neighbour; no bare site base`, soft: String(SOFT),
  cliffs, cliff_length_m: +cliffs.reduce((s, e) => s + e.length_m, 0).toFixed(1), bare_patches: r.bare_patches,
  bare_m2: +r.bare_patches.reduce((s, p) => s + p.area_m2, 0).toFixed(2), built_edges: r.edges.filter((e) => !SOFT.test(e.high)).length,
  allowed: r.edges.filter(allowed).map((e) => ({ ...e, why: allowed(e).why })) };
out.pass = !cliffs.length && !r.bare_patches.length;
writeFileSync(join(root, `${NAME}_ground.json`), JSON.stringify(out, null, 1));
for (const e of cliffs) console.log(`  CLIFF ${e.high} above ${e.low}: ${e.length_m} m, ${e.minStep}-${e.maxStep} mm (x ${e.x.join("..")}, y ${e.y.join("..")})`);
for (const p of r.bare_patches) console.log(`  BARE ${p.area_m2} m2 (x ${p.x.join("..")}, y ${p.y.join("..")})`);
console.log(`ground ${NAME}: soft-ground cliffs ${cliffs.length} (${out.cliff_length_m} m), bare base ${out.bare_m2} m2, built edges ${out.built_edges} | PASS ${out.pass}`);
