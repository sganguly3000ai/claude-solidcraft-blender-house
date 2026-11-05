# Ground v1: the brief (Sam's words, 2026-10-25) and how it became data

STAGE 4. Every lawn blends into its surroundings. Model `home_v7` = v4 (`..\v4\design.json`, untouched) + the
add-on (`..\addition_v1\addition.json`, untouched) + the garden (`..\garden_v1\garden.json`, untouched) + this file
(`ground.json`): `node build_home.mjs ground.json` (it includes the garden, which
includes the addition).

## Sam's words, verbatim, in order
1. "the back yard has improved tremendously.  The only observation is in the cam_tower image.  i cannot quite make
   out but appears the lawn part looks like terraced and does not blend into the driveway and the rest of the lawn
   that is below.  I do not know but I think you mentioned this has to be mainly done in Solidcraft first - is that
   correct?"
2. "yes we do not want any landscaped area that look unreal - the lawns with grasses should all blend into their
   srroundings. Just like the rest of the exercise - we should log this exercise and refactor also to add to the
   story"
3. "Yes, build Stage 4 as proposed: all six points, banks inside the plot. Tag first, log everything."

## Who decided what
- Sam: the rule (no unreal landscaping; lawns blend), all six points of the proposal, banks inside the plot.
- Claude Code: the measurement (the ground audit), the proposal
  (`data\history\ground\01_ground_blend_proposal_2026-10-25.md`), the layout, the data, the build code.
- Changes from the approved proposal, found while laying it out (logged in `ground.json`'s notes):
  - The east boundary bank is 1 m wide (1 in 2.2), not 1.5 m. Claude's driveway already reaches x 29000, so a bank
    starting at 28500 would leave a step against the driveway's edge.
  - Raising the forecourt link (point 5) would have made it stand up to 270 mm above the east front lawn. So the
    lawn's last metre beside the link rises to meet it, in the same way as point 6.
  - The west bed loses its first 1.5 m to the bank, and with it one shrub (Shrub_G1).
