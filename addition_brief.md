# Addition v1: the brief (Sam's words, 2026-10-25) and how it became data

This folder holds the FIRST change to the house since Claude designed it (v4). The v4 design (`..\v4\design.json`)
is NOT edited: the addition is its own data file (`addition.json`), merged by the build script
(`node build_home.mjs addition.json` -> model `home_v5`). Without the addition file
the build gives the v4 model exactly as before (checked: identical script).

## Sam's brief, verbatim, in order
1. "there is what looks like a 2 1/2 (3) story portion in the reference image - which does not exist in the model we
   developed ... that little 2 1/2 (3) story really makes the reference pop ... add one of those stories to our model
   in solidcraft ... both portions are going to be smaller than the 2nd floor as in the reference ... we would like to
   also have a covered portico connecting the two sections."
2. "Only do the main section two smaller portions one on each side of the main building - with a portico roof
   connecting the two sections. leave the garage alone"; curved roofs: "if flat on the connector looks better - no
   need for curved - take curved out".
3. (after Claude Code found there is no room upstairs for a stair) "can we find a any area around the house where we
   can add on from the ground floor - that gives us the space to add a staircase as well as an elevator. this
   addition can be bolted on to the side of the home, from each of the 2 existing floors this stair/elevator section
   should be accessed from some common area - that is not through some bedroom or some room on the ground floor that
   was initially designed to be an office etc. If we can find such a spot and it does not ruin the look of the home -
   instead enhances - that is what we should do."
4. "Yes, develop the detailed east-tower layout (stair, lift, glass links, path, kitchen window) for discussion."
5. "without actually seeing it - it is hard to visualize - so go ahead and refactor" (= build it).

## Who decided what
- Sam: what to add, where not to (garage), flat roofs, the common-area rule, build it.
- Claude Code (Opus 5.5): the sizes and positions, read from design.json; the stair problem; the east site; the
  layout (analyses 1-3 in `data\history\addon\`); the data in `addition.json`; the build code
  (`build_addition.mjs`).
- Not decided by anyone qualified: lift product sizes, stair rules, fire separation, waterproofing (architect).
