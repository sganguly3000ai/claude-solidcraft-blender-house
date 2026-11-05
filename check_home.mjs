// Checks for the v4 home model (the Robie checks, one script): (1) every body's volume against the value computed from
// design.json (a wall cut right through by a floor-to-ceiling opening becomes several bodies "W_X (1)"...: summed);
// (2) SolidCraft's own inspect.interference over all pairs, plus a control probe that MUST be reported; (3) support:
// nothing floats (bounding boxes); (4) two runs of the same script, same file name, identical SHA-256; (5) the saved
// model next to this script is the current build and holds the parameters.
// Run: node check_home.mjs [model]  -> <model>_checks.json (default home_v4; test files go to your system's temp folder)
import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { tmpdir } from "node:os";

const CLI = process.env.SOLIDCRAFT_CLI ?? "solidcraft-cli";   // set SOLIDCRAFT_CLI to the full path if it is not on your PATH
const TAR = process.platform === "win32" ? "C:/Windows/System32/tar.exe" : "tar";   // Windows bsdtar reads zip (Git's GNU tar does not)
const NAME = process.argv[2] ?? "home_v4";
const root = fileURLToPath(new URL(".", import.meta.url)), tmp = join(tmpdir(), "dream-it-checks", NAME);
const script = join(root, `${NAME}_script.json`);
const base = JSON.parse(readFileSync(script, "utf8")).commands;
const expected = JSON.parse(readFileSync(join(root, `${NAME}_expected.json`), "utf8")).bodies;
mkdirSync(tmp, { recursive: true });
const run = (args) => execFileSync(CLI, args, { stdio: "ignore", maxBuffer: 1 << 26 });
const out = {};

// (1) volumes
run(["eval", script, "--json-out", join(tmp, "measure.json")]);
const M = JSON.parse(readFileSync(join(tmp, "measure.json"), "utf8")).bodies;
const sum = {};
for (const b of M) { const k = b.name.replace(/ \(\d+\)$/, ""); sum[k] = (sum[k] ?? 0) + b.volume_mm3; }
const TOL = 1e-3;   // relative: the low-poly plant octagons round their corners to 0.1 mm (~0.02%)
out.volumes = { bodies: M.length, expected: Object.keys(expected).length, worst_rel: 0, mismatches: [], missing: [], extra: [] };
for (const [k, v] of Object.entries(expected)) {
  if (sum[k] == null) { out.volumes.missing.push(k); continue; }
  const d = Math.abs(sum[k] - v) / v; out.volumes.worst_rel = Math.max(out.volumes.worst_rel, d);
  if (d > TOL) out.volumes.mismatches.push({ body: k, expected_m3: v / 1e9, got_m3: +(sum[k] / 1e9).toFixed(6) });
}
out.volumes.extra = Object.keys(sum).filter((k) => !(k in expected));
out.volumes.pass = !out.volumes.mismatches.length && !out.volumes.missing.length && !out.volumes.extra.length;

// (2) interference, all pairs, with a control probe (1 m cube through the street balcony)
function interference(extra, tag) {
  const f = join(tmp, `${tag}.json`), o = join(tmp, `${tag}_res.json`);
  writeFileSync(f, JSON.stringify({ commands: [...base, ...extra, { command: "inspect.interference", params: {} }] }));
  run(["run", f, "--results", "--quiet", "--json-out", o]);
  const res = JSON.parse(readFileSync(o, "utf8")), list = res.results ?? res;
  const r = (Array.isArray(list) ? list : Object.values(list)).at(-1);
  return r.result ?? r;
}
const pairs = (x) => x.interferences.map((i) => ({ a: i.a, b: i.b, m3: +((i.volume ?? i.volume_mm3) / 1e9).toFixed(6) }));
const main = interference([], "interf_model");
const ctrl = interference([{ command: "solid.box", params: { center: [3000, -1000, 3000], length: "1000", width: "1000", height: "1000", operation: "new", name: "Probe", body_name: "Probe" } }], "interf_control");
const found = pairs(main), hits = pairs(ctrl).filter((p) => p.a === "Probe" || p.b === "Probe");
out.interference = { tool: "SolidCraft inspect.interference", bodies_checked: main.checked, pairs_intersected: main.pairs_intersected,
  unchecked: main.unchecked, control: { hits, ok: hits.length > 0 },
  overlaps: found.filter((p) => p.m3 >= 0.001), contact_under_1_litre: found.filter((p) => p.m3 < 0.001) };
out.interference.pass = out.interference.control.ok && !out.interference.overlaps.length && !main.unchecked.length;

// (3) support: a body whose bottom is above the site base's bottom with nothing directly under it (2 mm tolerance)
const SPANS = /^(Glass_BL_1_.*|R_.*|B_.*|S_SL_FF|S_SL_RR|W_F_STEP.*|Door_.*|Glass_.*|A_.*_Roof|A_Link_(FF|ROOF)|A_Stair_.*|A_LiftCar_.*)$/;   // roofs, slabs, the balcony, step wall: carried by walls/piers at their edges; addition: roofs, link slabs, stair treads/landings (carried by the tower walls), the lift car (hangs in the shaft)
const ov = (a, b) => Math.min(a.max[0], b.max[0]) - Math.max(a.min[0], b.min[0]) > 2 && Math.min(a.max[1], b.max[1]) - Math.max(a.min[1], b.min[1]) > 2;
const zMin = Math.min(...M.map((b) => b.bbox.min[2]));
out.support = { unsupported: [], spans: [] };
for (const a of M) {
  const z0 = a.bbox.min[2]; if (z0 <= zMin + 2) continue;
  const under = M.filter((b) => b !== a && ov(a.bbox, b.bbox) && b.bbox.max[2] >= z0 - 2 && b.bbox.min[2] < z0 - 2);
  if (!under.length) (SPANS.test(a.name) ? out.support.spans : out.support.unsupported).push({ body: a.name, bottom: Math.round(z0) });
}
out.support.pass = !out.support.unsupported.length;

// (4) twin runs: same script, same output file name, two folders. The OBJ and STEP must be byte-identical; the
// .solidcraft save is a zip whose cache/model.json records how many ms each step took, so it is unpacked and compared
// with those timing fields blanked (everything else must match byte for byte)
const hash = (b) => createHash("sha256").update(b).digest("hex");
const h = [];
for (const k of ["A", "B"]) {
  const d = join(tmp, "twin", k); mkdirSync(join(d, "unz"), { recursive: true });
  execFileSync(CLI, ["run", script, "--out", `${NAME}.obj`, "--out", `${NAME}.step`, "--save", `${NAME}.solidcraft`], { cwd: d, stdio: "ignore" });
  execFileSync(TAR, ["-xf", join(d, `${NAME}.solidcraft`), "-C", join(d, "unz")], { stdio: "ignore" });
  const inner = execFileSync(TAR, ["-tf", join(d, `${NAME}.solidcraft`)], { encoding: "utf8" }).split(/\r?\n/).filter((f) => f && !f.endsWith("/")).sort();
  const save = inner.map((f) => f + ":" + hash(readFileSync(join(d, "unz", f), "utf8").replace(/"ms":[0-9.e+-]+/g, '"ms":0'))).join("|");
  h.push({ [`${NAME}.obj`]: hash(readFileSync(join(d, `${NAME}.obj`))), [`${NAME}.step`]: hash(readFileSync(join(d, `${NAME}.step`))), [`${NAME}.solidcraft (timings blanked)`]: hash(save) });
}
out.twin = { A: h[0], B: h[1], pass: JSON.stringify(h[0]) === JSON.stringify(h[1]) };

// (5) the saved model next to this script (the file opened in the app) is the current build and carries the parameters: on
// 2026-10-23 it was older than the parameters, which a default build cannot show (same OBJ)
const savedDir = join(tmp, "saved_unz"); mkdirSync(savedDir, { recursive: true });
const saved = join(root, `${NAME}.solidcraft`);
execFileSync(TAR, ["-xf", saved, "-C", savedDir], { stdio: "ignore" });
const savedInner = execFileSync(TAR, ["-tf", saved], { encoding: "utf8" }).split(/\r?\n/).filter((f) => f && !f.endsWith("/")).sort();
const savedHash = hash(savedInner.map((f) => f + ":" + hash(readFileSync(join(savedDir, f), "utf8").replace(/"ms":[0-9.e+-]+/g, '"ms":0'))).join("|"));
const wantParams = base.filter((c) => c.command === "parameters.add").map((c) => c.params.name);
const gotParams = JSON.parse(readFileSync(join(savedDir, "document.json"), "utf8")).params.map((p) => p.name);
out.saved = { file: `${NAME}.solidcraft`, matches_build: savedHash === h[0][`${NAME}.solidcraft (timings blanked)`],
  parameters: gotParams, missing_parameters: wantParams.filter((n) => !gotParams.includes(n)) };
out.saved.pass = out.saved.matches_build && !out.saved.missing_parameters.length;

out.pass = out.volumes.pass && out.interference.pass && out.support.pass && out.twin.pass && out.saved.pass;
writeFileSync(join(root, `${NAME}_checks.json`), JSON.stringify(out, null, 2));
console.log(`volumes: ${M.length} bodies, worst ${(out.volumes.worst_rel * 100).toFixed(3)}%, mismatches ${out.volumes.mismatches.length}, missing ${out.volumes.missing.length}, extra ${out.volumes.extra.length} | PASS ${out.volumes.pass}`);
console.log(`interference: ${main.checked} bodies, ${main.pairs_intersected} pairs; control ${hits.map((p) => (p.a === "Probe" ? p.b : p.a) + " " + p.m3).join(", ")}; overlaps >= 1 L: ${out.interference.overlaps.map((p) => `${p.a} x ${p.b} ${p.m3}`).join("; ") || "none"}; contact ${out.interference.contact_under_1_litre.length}; unchecked ${main.unchecked.length} | PASS ${out.interference.pass}`);
console.log(`support: unsupported ${out.support.unsupported.map((u) => u.body).join(", ") || "none"}; spans ${out.support.spans.length} | PASS ${out.support.pass}`);
console.log(`twin runs identical: ${out.twin.pass} (obj ${h[0][`${NAME}.obj`].slice(0, 12)}...)`);
console.log(`saved model: matches build ${out.saved.matches_build}; parameters ${gotParams.join(", ") || "none"} | PASS ${out.saved.pass}`);
console.log("ALL PASS:", out.pass);
