// Addition v1 (2026-10-25): builds addition.json on top of the v4 house, inside the same
// SolidCraft script (called by build_home.mjs). Everything here is NEW bodies (named "A_..." or "Glass_A_..." /
// "Door_A_..."), except the changes the data lists under house_changes: the cuts into the upper roof (lift shaft) and
// into the garden lawn and side path (where the link and tower stand). W21's glass -> door is done in build_home.mjs.
// Heights written "roof", "roof+N", "roof-N" follow the parameter upper_roof_top, so raising the upper roof carries the
// whole addition (top boxes, portico, terrace, walkway, lift top, tower top, the stair's top storey) with it.
// the area of a plan polygon inside a rectangle (Sutherland-Hodgman clip): exact volumes for cuts into lawns and paths
export function clipArea(pts, x0, x1, y0, y1, area) {
  let p = pts;
  for (const [inside, hit] of [[(q) => q[0] >= x0, (a, b) => [x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0])]],
                               [(q) => q[0] <= x1, (a, b) => [x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0])]],
                               [(q) => q[1] >= y0, (a, b) => [a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0]],
                               [(q) => q[1] <= y1, (a, b) => [a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1]]]) {
    const o = []; p.forEach((a, i) => { const b = p[(i + 1) % p.length];
      if (inside(a)) { o.push(a); if (!inside(b)) o.push(hit(a, b)); } else if (inside(b)) o.push(hit(a, b)); });
    p = o; if (!p.length) break;
  }
  return p.length ? area(p) : 0;
}

export function buildAddition(A, { box, paint, expected, BB, BASE_TOP, ovl, area, D }) {
  const ROOF = A.roof_level;
  const outlines = Object.fromEntries([...D.landscape.lawns.map((l) => [`Lawn_${l.id}`, l.outline]),
                                       ...D.landscape.paved_areas.filter((p) => p.outline).map((p) => [`Pave_${p.id}`, p.outline])]);
  const isRoof = (v) => typeof v === "string" && v.startsWith("roof");
  const val = (v) => (v === "base" ? BASE_TOP : isRoof(v) ? ROOF + Number(v.slice(4) || 0) : v);
  const ex = (v) => { const n = Number(v.slice(4) || 0); return n ? `upper_roof_top ${n > 0 ? "+" : "-"} ${Math.abs(n)}` : "upper_roof_top"; };
  // a box whose bottom / top may follow the roof parameter
  function B(name, [x0, x1], [y0, y1], [za, zb], colour, opts = {}) {
    const z0 = val(za), z1 = val(zb), o = { ...opts };
    if (isRoof(za)) o.zExpr = ex(za);
    if (isRoof(zb) && !isRoof(za)) { const n = Number(zb.slice(4) || 0) - z0; o.hExpr = `upper_roof_top ${n >= 0 ? "+" : "-"} ${Math.abs(n)}`; }
    box(name, x0, x1, y0, y1, z0, z1, o);
    if (name && colour) paint(name, colour);
    return { x0, x1, y0, y1, z0, z1 };
  }
  // a cut through new bodies (box targets): the expected volumes lose exactly the overlap
  function cut(targets, xs, ys, zs) {
    const t = B(null, xs, ys, zs, null, { cut: targets });
    for (const n of targets) expected[n] -= ovl(BB[n], t);
  }
  const C = { panel: "#2b2d31", stone: "#a89f8f", roof: "#3a3d42", glass: "#9cc3d6", dark: "#1f2023", slab: "#c9c6bf",
              pave: "#b8b6ae", timber: "#b08a5a" };
  const PANE = 24, LEAF = 50, M = 50;

  // HOUSE CHANGES: the notch in the upper roof for the lift shaft
  for (const n of A.house_changes.roof_notches) cut([`R_${n.roof.replace(/[^A-Za-z0-9]+/g, "_")}`], n.x, n.y, n.z);

  // LANDSCAPE CUTS: the lawn and the side path make room for the link and the tower (exact overlap: polygon clipped)
  const clip = (pts, x0, x1, y0, y1) => clipArea(pts, x0, x1, y0, y1, area);
  for (const c of A.house_changes.landscape_cuts) {
    B(null, c.x, c.y, [BASE_TOP - 50, 0], null, { cut: c.parts });
    for (const n of c.parts) {
      const outline = outlines[n];
      expected[n] -= outline ? clip(outline, c.x[0], c.x[1], c.y[0], c.y[1]) * (BB[n].z1 - BB[n].z0) : ovl(BB[n], { x0: c.x[0], x1: c.x[1], y0: c.y[0], y1: c.y[1], z0: BASE_TOP - 50, z1: 0 });
    }
  }

  // TOP BOXES: four walls on the upper roof, glazing and doors cut in, a roof slab with deep overhangs
  for (const t of A.top_boxes) {
    const k = t.id.replace(/[^A-Za-z0-9]+/g, "_"), w = t.wall, [x0, x1] = t.x, [y0, y1] = t.y, Z = ["roof", `roof+${t.height}`];
    const walls = { S: [[x0, x1], [y0, y0 + w]], N: [[x0, x1], [y1 - w, y1]], W: [[x0, x0 + w], [y0 + w, y1 - w]], E: [[x1 - w, x1], [y0 + w, y1 - w]] };
    for (const [s, [xs, ys]] of Object.entries(walls)) B(`A_${k}_Wall_${s}`, xs, ys, Z, C.panel);
    for (const g of [...t.glazing, ...t.doors]) {
      const [xs, ys] = walls[g.wall], along = g.wall === "S" || g.wall === "N", wn = `A_${k}_Wall_${g.wall}`;
      const zs = [`roof+${g.z[0]}`, `roof+${g.z[1]}`], c = along ? (ys[0] + ys[1]) / 2 : (xs[0] + xs[1]) / 2;
      const span = [g.from, g.to], th = g.kind ? LEAF : PANE;
      if (along) cut([wn], span, [ys[0] - M, ys[1] + M], zs); else cut([wn], [xs[0] - M, xs[1] + M], span, zs);
      const n = `${g.kind ? "Door" : "Glass"}_A_${k}_${g.wall}${g.kind ? "_door" : ""}${g.kind ? "_" + g.from : ""}`;
      if (along) B(n, span, [c - th / 2, c + th / 2], zs, C.glass); else B(n, [c - th / 2, c + th / 2], span, zs, C.glass);
    }
    B(`A_${k}_Roof`, t.roof.x, t.roof.y, [`roof+${t.height}`, `roof+${t.height + t.roof.thickness}`], C.roof);
  }
  // PORTICO roof, PAVERS (terrace + roof walkway), glass RAILINGS
  B("A_Portico_Roof", A.portico.x, A.portico.y, [`roof+${A.portico.z[0]}`, `roof+${A.portico.z[1]}`], C.roof);
  for (const p of A.pavers) B(`A_Pavers_${p.id}`, p.x, p.y, ["roof", `roof+${A.pavers_thickness}`], C.pave);
  const R = A.railings, rz = A.pavers_thickness;
  for (const run of R.runs) B(`Glass_A_Rail_${run.id}`, run.x, run.y, [`roof+${rz}`, `roof+${rz + R.height}`], C.glass);
  // WALKWAY (revision 2): glass walls on the pavers and its own roof, from the east top box to the tower
  if (A.walkway) {
    for (const g of A.walkway.glass) B(`Glass_A_Walk_${g.id}`, g.x, g.y, [`roof+${g.z[0]}`, `roof+${g.z[1]}`], C.glass);
    const W = A.walkway.roof; B("A_Walk_Roof", W.x, W.y, [`roof+${W.z[0]}`, `roof+${W.z[1]}`], C.roof);
  }

  // GLASS LINK: slabs (ground, first floor, the roof walkway's base) and its glass faces
  for (const s of A.link.slabs) B(`A_Link_${s.id}`, s.x, s.y, s.z, s.id === "ROOF" ? C.roof : C.slab);
  for (const g of A.link.glass) B(`Glass_A_Link_${g.id}`, g.x, g.y, g.z, C.glass);

  // GLASS LIFT: four panes, a shaft roof, and the car (floor, top, four corner posts) at the ground floor
  const L = A.lift.shaft, [lx0, lx1] = L.x, [ly0, ly1] = L.y, p = L.pane, top = L.z[1];
  B("Glass_A_Lift_S", [lx0, lx1], [ly0, ly0 + p], L.z, C.glass); B("Glass_A_Lift_N", [lx0, lx1], [ly1 - p, ly1], L.z, C.glass);
  B("Glass_A_Lift_W", [lx0, lx0 + p], [ly0 + p, ly1 - p], L.z, C.glass); B("Glass_A_Lift_E", [lx1 - p, lx1], [ly0 + p, ly1 - p], L.z, C.glass);
  if (L.roof_thickness) B("A_Lift_Roof", L.x, L.y, [top, `roof+${val(top) - ROOF + L.roof_thickness}`], C.roof);   // revision 3: 0 = covered by the walkway roof
  const K = A.lift.car, [cx0, cx1] = K.x, [cy0, cy1] = K.y, P = 50;
  B("A_LiftCar_Floor", K.x, K.y, [0, P], C.dark); B("A_LiftCar_Top", K.x, K.y, [K.height - P, K.height], C.dark);
  [[cx0, cy0], [cx1 - P, cy0], [cx0, cy1 - P], [cx1 - P, cy1 - P]].forEach(([x, y], i) => B(`A_LiftCar_Post_${i + 1}`, [x, x + P], [y, y + P], [P, K.height - P], C.dark));

  // STONE STAIR TOWER: walls from the site base, doors to the lobby on every level, a garden door, a tall slot window
  const T = A.tower, [tx0, tx1] = T.x, [ty0, ty1] = T.y, tw = T.wall, TZ = ["base", T.top];
  const tWalls = { W: [[tx0, tx0 + tw], [ty0, ty1]], E: [[tx1 - tw, tx1], [ty0, ty1]], S: [[tx0 + tw, tx1 - tw], [ty0, ty0 + tw]], N: [[tx0 + tw, tx1 - tw], [ty1 - tw, ty1]] };
  for (const [s, [xs, ys]] of Object.entries(tWalls)) B(`A_Tower_Wall_${s}`, xs, ys, TZ, C.stone);
  const DL = T.doors_to_lobby, [wx0, wx1] = tWalls.W[0];
  for (const zs of DL.levels) cut(["A_Tower_Wall_W"], [wx0 - M, wx1 + M], DL.y, zs);
  { const g = T.garden_door, [, [ny0, ny1]] = tWalls.N, c = (ny0 + ny1) / 2;
    cut(["A_Tower_Wall_N"], g.x, [ny0 - M, ny1 + M], g.z); B("Door_A_Tower_Garden", g.x, [c - LEAF / 2, c + LEAF / 2], g.z, C.dark); }
  { const s = T.slot_window, [[ex0, ex1]] = tWalls.E, c = (ex0 + ex1) / 2;
    cut(["A_Tower_Wall_E"], [ex0 - M, ex1 + M], s.y, s.z); B("Glass_A_Tower_Slot", [c - PANE / 2, c + PANE / 2], s.y, s.z, C.glass); }
  B("A_Tower_Roof", T.roof.x, T.roof.y, [T.top, `roof+${val(T.top) - ROOF + T.roof.thickness}`], C.roof);
  B("A_Tower_GF", [tx0 + tw, tx1 - tw], [ty0 + tw, ty1 - tw], ["base", 0], C.slab);

  // STAIR: switchback, one solid tread block per step (300 deep under each tread), landings as slabs
  const S = A.stair, [se0, se1] = S.bands.rises_east, [sw0, sw1] = S.bands.rises_west, END = S.flight_end_x, G = S.going, TH = S.tread_thickness;
  const [fl0, fl1] = S.floor_landing_x, [hl0, hl1] = S.half_landing_x;
  S.storeys.forEach((st, si) => {
    const b = val(st.from), n = st.risers, k = n / 2, roofTop = isRoof(st.to);
    // a tread top as a number (default) and, for the top storey, as an expression of the roof parameter
    const zz = (i, depth) => {
      const def = b + i * (val(st.to) - b) / n;
      return roofTop ? { z0: def - depth, z1: def, zExpr: `${b} + ${i} * (upper_roof_top - ${b}) / ${n} - ${depth}` } : { z0: Math.max(def - depth, b), z1: def };
    };
    const tread = (name, xs, ys, i, depth) => { const z = zz(i, depth); box(name, xs[0], xs[1], ys[0], ys[1], z.z0, z.z1, z.zExpr ? { zExpr: z.zExpr } : {}); paint(name, C.timber); };
    for (let i = 1; i < k; i++) tread(`A_Stair_${si + 1}E_${i}`, [END - (k - i) * G, END - (k - i - 1) * G], [se0, se1], i, TH);
    tread(`A_Stair_${si + 1}_HalfLanding`, [hl0, hl1], [se0, sw1], k, 200);
    for (let j = 1; j < k; j++) tread(`A_Stair_${si + 1}W_${j}`, [END - j * G, END - (j - 1) * G], [sw0, sw1], k + j, TH);
    // the floor landing this storey arrives at (west end; it reaches the last tread)
    const arrive = END - (k - 1) * G;
    tread(`A_Stair_${si + 1}_Landing`, [fl0, fl1], [se0, sw1], n, 200);
    if (arrive > fl1) tread(`A_Stair_${si + 1}_LandingExt`, [fl1, arrive], [sw0, sw1], n, 200);
  });
}
