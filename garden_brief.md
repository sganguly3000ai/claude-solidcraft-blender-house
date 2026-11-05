# Garden v1: the brief (Sam's words, 2026-10-25) and how it became data

STAGE 3. The back garden steps down in a terrace. Model `home_v6` = v4 (`..\v4\design.json`, untouched) + the
add-on (`..\addition_v1\addition.json`, untouched) + this garden (`garden.json`):
`node build_home.mjs addition.json garden.json`.

## Sam's words, verbatim, in order
1. "in the reference the rear of the house the ground contours down - hence there is flight of stairs and a raised
   garden bed - I think we should have that."
2. "but we want the lawn to have a smooth contour to match up with the front lawn"
3. "one of main things is terracing the back yard with the raised flower beds and the steps going down. again mark
   this stage with a stage number before you make the backyard changes - so that we can highlight"
4. "Approved: lower garden at -600 (front lawn level), one 3 m flight of 3 lit steps in the middle, raised
   stone-edged beds across. Build it as garden.json."

## Who decided what
- Sam: terraces, raised beds, steps going down, the lower level = the front lawn's, one flight, approval.
- Claude Code: the layout from design.json (proposal: `data\history\garden\01_terracing_proposal_2026-10-25.md`), the
  data, the build code. One change from the approved proposal, found while laying it out: the drop moved from
  y 15500 to y 16500, because the garden terrace's depth is a live parameter (3.9 m -> 6 m in the demo) and at 15500
  the terrace would have run into the beds. With the garden, terrace_depth now has a limit of 6.5 m (measured with
  SolidCraft's clash check: 6.5 m clean; 6.6 m the terrace slab and plinth run into the beds and the top step; first
  estimated "about 6.6 m", corrected by the measurement).
