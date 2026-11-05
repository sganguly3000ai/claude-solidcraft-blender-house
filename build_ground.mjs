// Ground v1 (2026-10-25, STAGE 4): builds ground.json into the same SolidCraft script (called by
// build_home.mjs after the garden). New bodies are named "Gr_..."; changes to existing parts are the cuts and the
// removal listed under house_changes. The sloped-ground builder: a piece's top is the lower of two side profiles,
// made in SolidCraft as a profile_y extruded east across the piece, intersected with a profile_x extruded south
// across it; pieces sharing a "join" are joined into one body (its top: the higher of the pieces).
import { clipArea } from "./build_addition.mjs";

export function buildGround(G, { add, box, paint, expected, BB, BASE_TOP, area, ovl, D }) {
  const C = { lawn: "#6f9a4a", stone: "#a89f8f", paving: "#b8b6ae" };

  // CUTS into existing parts (exact volumes: a design outline clipped to the cut, or a box's overlap with it)
  const outlines = Object.fromEntries([...D.landscape.lawns.map((l) => [`Lawn_${l.id}`, l.outline]),
    ...D.landscape.paved_areas.filter((p) => p.outline).map((p) => [`Pave_${p.id}`, p.outline])]);
  const done = {};   // two cuts into one part may overlap (Lawn_L2): subtract the overlap once
  for (const c of G.house_changes.landscape_cuts) {
    const cut = { x0: c.x[0], x1: c.x[1], y0: c.y[0], y1: c.y[1], z0: BASE_TOP - 50, z1: 0 };
    box(null, cut.x0, cut.x1, cut.y0, cut.y1, cut.z0, cut.z1, { cut: c.parts });
    for (const n of c.parts) {
      const b = BB[n], h = b.z1 - b.z0;
      const vol = (r) => (outlines[n] ? clipArea(outlines[n], r.x0, r.x1, r.y0, r.y1, area) * h : ovl(b, { ...r, z0: b.z0, z1: b.z1 }));
      expected[n] -= vol(cut);
      for (const p of done[n] ?? []) {
        const o = { x0: Math.max(p.x0, cut.x0), x1: Math.min(p.x1, cut.x1), y0: Math.max(p.y0, cut.y0), y1: Math.min(p.y1, cut.y1) };
        if (o.x1 > o.x0 && o.y1 > o.y0) expected[n] += vol(o);
      }
      (done[n] ??= []).push(cut);
    }
  }
  for (const r of G.house_changes.removed) { add("solid.remove", { bodies: r.parts }); for (const n of r.parts) delete expected[n]; }

  // PIECES
  const at = (prof, s) => {   // a profile's height at s (straight lines between its points)
    for (let i = 1; i < prof.length; i++) { const [a, za] = prof[i - 1], [b, zb] = prof[i]; if (s <= b) return za + (zb - za) * (s - a) / (b - a); }
    return prof.at(-1)[1];
  };
  const clip = (prof, s0, s1) => [[s0, at(prof, s0)], ...prof.filter(([s]) => s > s0 && s < s1), [s1, at(prof, s1)]];
  const topOf = (p) => (x, y) => Math.min(p.top ?? Infinity, p.profile_x ? at(p.profile_x, x) : Infinity, p.profile_y ? at(p.profile_y, y) : Infinity);
  const joins = {};
  for (const p of G.pieces) {
    const [x0, x1] = p.x, [y0, y1] = p.y, n = p.id;
    if (p.top != null && !p.profile_x && !p.profile_y) box(n, x0, x1, y0, y1, BASE_TOP, p.top, { expect: false });
    else {
      // profile_y (or flat) extruded east from x0; then profile_x extruded south from y1, intersected with it
      const py = p.profile_y ? clip(p.profile_y, y0, y1) : [[y0, p.top ?? 0], [y1, p.top ?? 0]];
      const px = p.profile_x ? clip(p.profile_x, x0, x1) : null;
      const yPts = [[y0, BASE_TOP], [y1, BASE_TOP], ...py.slice().reverse()];
      add("sketch.create", { plane: { origin: [x0, 0, 0], x_dir: [0, 1, 0], y_dir: [0, 0, 1] }, name: `Sk${n}_Y` });
      add("sketch.line", { points: yPts, closed: true });
      add("solid.extrude", { sketch: `Sk${n}_Y`, distance: String(x1 - x0), operation: "new", name: n, body_name: n });
      if (px) {
        const xPts = [[x0, BASE_TOP], [x1, BASE_TOP], ...px.slice().reverse()];
        add("sketch.create", { plane: { origin: [0, y1, 0], x_dir: [1, 0, 0], y_dir: [0, 0, 1] }, name: `Sk${n}_X` });   // normal -y
        add("sketch.line", { points: xPts, closed: true });
        add("solid.extrude", { sketch: `Sk${n}_X`, distance: String(y1 - y0), operation: "intersect", targets: [n] });
      }
      BB[n] = { x0, x1, y0, y1, z0: BASE_TOP, z1: Math.max(...py.map((q) => q[1])) };
    }
    if (p.join) (joins[p.join] ??= []).push(p); else { expected[n] = vol([p]); paint(n, C[p.kind]); }
  }
  for (const [name, ps] of Object.entries(joins)) {
    const [first, ...rest] = ps.map((p) => p.id);
    add("solid.combine", { target: first, tools: rest, operation: "join" });
    add("body.rename", { body: first, name });
    expected[name] = vol(ps); paint(name, C[ps[0].kind]);
  }
  return G.house_changes.removed.flatMap((r) => r.parts);

  // volume of one piece, or of joined pieces (top = the highest piece over each point): 10 mm midpoint grid; the
  // tops are straight between profile points, so only the cells on a crease carry any error (far below 0.1%)
  function vol(ps) {
    const S = 10, X0 = Math.min(...ps.map((p) => p.x[0])), X1 = Math.max(...ps.map((p) => p.x[1]));
    const Y0 = Math.min(...ps.map((p) => p.y[0])), Y1 = Math.max(...ps.map((p) => p.y[1])), tops = ps.map(topOf);
    let v = 0;
    for (let x = X0 + S / 2; x < X1; x += S) for (let y = Y0 + S / 2; y < Y1; y += S) {
      let z = -Infinity;
      ps.forEach((p, i) => { if (x > p.x[0] && x < p.x[1] && y > p.y[0] && y < p.y[1]) z = Math.max(z, tops[i](x, y)); });
      if (z > BASE_TOP) v += (z - BASE_TOP) * S * S;
    }
    return v;
  }
}
