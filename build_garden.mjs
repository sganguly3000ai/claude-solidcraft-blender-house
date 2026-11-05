// Garden v1 (2026-10-25, STAGE 3): builds garden.json into the same SolidCraft script (called by
// build_home.mjs after the addition). New bodies are named "G_..." (beds, steps, lower lawn) and "Shrub_G..." (plants);
// the only change to an existing part is the cut listed under house_changes: the garden lawn ends at the drop.
import { clipArea } from "./build_addition.mjs";

export function buildGarden(G, { box, poly, paint, expected, BB, BASE_TOP, area, D }) {
  const C = { stone: "#a89f8f", soil: "#5a4632", step: "#b8b6ae", lawn: "#6f9a4a", shrub: "#4f7a3c", grass: "#9aa35a" };
  const B = (name, [x0, x1], [y0, y1], [z0, z1], colour) => { box(name, x0, x1, y0, y1, z0, z1); paint(name, colour); };

  // the garden lawn ends at the drop (exact volume: its outline clipped to the cut)
  const outlines = Object.fromEntries(D.landscape.lawns.map((l) => [`Lawn_${l.id}`, l.outline]));
  for (const c of G.house_changes.landscape_cuts) {
    box(null, c.x[0], c.x[1], c.y[0], c.y[1], BASE_TOP - 50, 0, { cut: c.parts });
    for (const n of c.parts) expected[n] -= clipArea(outlines[n], c.x[0], c.x[1], c.y[0], c.y[1], area) * (BB[n].z1 - BB[n].z0);
  }

  // RAISED BEDS: a stone edge on the low (north) side and beside the steps, soil behind it
  const Bd = G.beds, [by0, by1] = Bd.band_y, e = Bd.edge, ST = G.steps, [sx0, sx1] = ST.x;
  for (const b of Bd.beds) {
    const [x0, x1] = b.x, west = x1 <= sx0;
    B(`G_Bed_${b.id}_Edge_N`, [x0, x1], [by1 - e, by1], [BASE_TOP, Bd.edge_top], C.stone);
    const side = west ? [x1 - e, x1] : [x0, x0 + e];   // the edge beside the steps
    B(`G_Bed_${b.id}_Edge_Steps`, side, [by0, by1 - e], [BASE_TOP, Bd.edge_top], C.stone);
    B(`G_Bed_${b.id}_Soil`, west ? [x0, x1 - e] : [x0 + e, x1], [by0, by1 - e], [BASE_TOP, Bd.soil_top], C.soil);
  }

  // STEPS going down to the north: one solid block per tread, from the site base up to that tread
  for (let i = 1; i < ST.risers; i++) {
    const y0 = ST.first_riser_y + (i - 1) * ST.going;
    B(`G_Step_${i}`, [sx0, sx1], [y0, y0 + ST.going], [BASE_TOP, ST.top - i * ST.riser_height], C.step);
  }

  // LOWER LAWN at the front lawn's level
  for (const l of G.lower_lawn) B(`G_Lawn_${l.id}`, l.x, l.y, [BASE_TOP, G.levels.lower_garden], C.lawn);

  // PLANTS on the beds' soil: shrubs and ornamental grasses alternate (low-poly octagons, as in v4)
  const P = G.plants, oct = ([cx, cy], d) => Array.from({ length: 8 }, (_, i) => [cx + (d / 2) * Math.cos((i + 0.5) * Math.PI / 4), cy + (d / 2) * Math.sin((i + 0.5) * Math.PI / 4)]);
  P.x.forEach((x, i) => {
    const grass = i % 2 === 1, n = grass ? `Shrub_GR_G${i + 1}` : `Shrub_G${i + 1}`;
    poly(n, oct([x, P.y], P.spread), Bd.soil_top, Bd.soil_top + P.height[grass ? "grass" : "shrub"]);
    paint(n, grass ? C.grass : C.shrub);
  });
}
