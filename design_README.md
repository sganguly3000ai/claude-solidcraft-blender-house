# Family house v3: v2 redesigned in the style of the reference photos

v3 keeps the v2 plans: every room, the L-shape, the side-entry two-car garage, the garage-to-utility fire door, and the rec room with its own stair from inside the garage. The outside is redesigned in the style of the two photos in `ref/`: flat roofs stacked as boxes, charcoal panels, split-face stone, timber soffits with warm downlights, a covered entry framed by a stone pier, a street balcony, a covered garden terrace, and finished landscaping.

Every drawing is an A3 landscape SVG at 1:100 (1 m = 10 mm), except the sample view. Levels are relative to the house ground-floor finished floor (±0.00). `design.json` holds the same building as data, in millimetres, with the same layout and conventions as v2.

## Files

| File | Content |
|---|---|
| `01_ground_floor_plan.svg` | Ground floor and site: walls, doors, windows, both stairs, cars, room names and areas. Also the porch, stone cheek wall, entry pier, lit entry steps, raised beds P1–P3, forecourt, path, driveway and apron, side path, gravel strips, lawns, trees and shrubs, the covered garden terrace with its piers and post, roof edges above (dashed), dimensions, the section line, north arrow and legend |
| `02_first_floor_plan.svg` | First floor and rec room. Also the street balcony with its glass balustrade, the terrace roof below, roof edges above, and the line where the roof steps up |
| `03_roof_plan.svg` | The three roof plates (terrace +3.20, lower +6.30, upper +6.90), the balcony, falls, outlets, overhang dimensions and all 31 soffit downlights (reflected) |
| `04_south_elevation.svg` | Street elevation with materials A–E, beds, steps, plants, levels |
| `05_north_elevation.svg` | Garden elevation with the covered terrace |
| `06_east_elevation.svg` | Driveway elevation with the side-entry garage door |
| `07_west_elevation.svg` | West elevation: the stacked boxes in profile |
| `08_section_AA.svg` | Section A–A at x = 5.80 m (looking west), through the steps, porch, front door, balcony, hall, stair (seen beyond), both roofs, the step wall and the garden terrace |
| `09_sample_view.svg` | Hand-drawn style isometric view from the south-east street corner, with callouts |
| `design.json` | The whole building and landscape as data (see the end of this README) |

## What changed from v2, and why

### The two photos, and what I took from each

- **`ref/front.jpg` (street front).** I took four things from it:
  - The stacked flat-roof boxes with deep, thin fascias and a taller box set back on top.
  - The covered entry under a lower canopy, with a stone pier next to a tall dark door and floor-to-ceiling glass.
  - The balcony with frameless glass on top of that canopy.
  - Warm downlights in the soffits, and the raised stone-edged bed and lit steps in front.
- **`ref/side.jpg` (side and garden).** I took three things from it:
  - The covered terrace under an extended roof, opening through big glass doors.
  - Large floor-to-ceiling glass in dark frames, grouped in clear bands.
  - The long, low raised bed with lit steps.

I did not copy the house. Its plan, proportions and window positions all come from v2.

### The changes, one wish at a time

1. **Flat roofs, stacked boxes (wish 1).** The butterfly roof is gone. There are now three flat roof plates, each with a thin 400 mm charcoal fascia and a timber soffit:
   - **Lower roof, top +6.30.** It covers the south (street) half of the house and the whole garage wing as one plate. It cantilevers **1.50 m** towards the street over the house and **1.00 m** around the garage.
   - **Upper roof, top +6.90, the "top box".** It covers the north half of the house (landing, bedrooms 2 and 3, bathroom, study). It sits 0.60 higher and starts 4.94 m back from the street face, so from the street it reads as a box set back on top, as in `front.jpg`. It cantilevers **1.20 m** over the garden.
   - **Terrace roof, top +3.20.** It covers the garden terrace.

   Together with the balcony (+2.80 to +3.20) and the garage wing standing 2.90 m forward, the street front now has four depths and three heights.
2. **Covered, recessed entry (wish 2).** The front door sits in a 3.00 x 2.10 m porch:
   - On the west, a full-height **stone cheek wall** (0.30 thick, running from the house wall out to the steps).
   - Overhead, the **balcony slab**, a timber soffit at +2.80 with two downlights.
   - On the east, a **0.60 x 0.60 stone pier** at the front corner.

   The door is a **charcoal pivot door, 1.00 x 2.80**, beside a **floor-to-ceiling glass sidelight** 1.10 wide. The wall east of the door (to the office window) is split-face stone, which the downlights graze, as in the photo.
3. **Large windows in dark frames (wish 3).**
   - All ground-floor windows and glass doors now run floor to ceiling (+0.00 to +2.80); the kitchen sills stay at +1.05 for the worktops.
   - The south first-floor windows run +3.20 to +5.90, right under the soffit.
   - The rec room windows use the same +3.20 to +5.90 band, so one horizontal band of glass runs along the house and the garage.
   - Snug and flex-room openings line up vertically (both x 0.80–3.40).
   - Frames, fascias, doors and the garage door are all dark aluminium.
4. **Materials (wish 4).**
   - Charcoal panels are the main material.
   - Split-face stone is used for the entry pier, the cheek wall, the wall beside the front door, the garage wing's street wall and crook wall (to +2.70), the two terrace piers and the bed edges.
   - Timber is used under every soffit.
   - Frameless glass is used on the balcony.
5. **Street balcony (wish 5).** It is **6.90 x 2.10 m (14.5 m²)**, over the entry, reached from the flex room through a new 2.60 m sliding glass door (D24, which replaces v2 window W10). The deck is at +3.15 and the frameless glass balustrade is 1.10 high on three sides. The lower roof's 1.50 overhang covers most of it.
6. **Covered garden terrace (wish 6).** It is **10.90 x 3.90 m (42.5 m²)**, off the living and dining rooms, under an extended flat roof (soffit +2.80). The roof rests on two **stone piers** and a slim **charcoal steel post**. The living room now opens through **4.80 m sliding glass doors** (v2: 4.00). The dining room's fixed glazing becomes **2.80 m sliding glass doors** (D23).
7. **Warm downlights (wish 7).** There are **31 downlights**, drawn as fittings on the roof plan (reflected) and on the elevations and section, and listed with coordinates in `design.json`:
   - 7 under the street overhang.
   - 10 around the garage overhangs: 5 on the south, 4 over the garage door and the apron, 1 in the crook.
   - 4 in the porch / balcony soffit.
   - 8 in the terrace soffit.
   - 2 under the upper roof's garden overhang.

   The 8 step lights are listed separately.
8. **Landscaping (wish 8).** It is shown on the ground floor plan (which is now also the site plan), on all four elevations, the section and the sample view:
   - **Raised planting beds** P1 (west of the entry), P2 (in front of the office) and P3 (along the garage's stone wall). Each has a split-face stone edge with a concrete coping, top at −0.15, which is 450 above the forecourt.
   - **Wide entry steps**, 3.00 wide, 4 risers x 150, 3 treads x 400, with **a light in every riser** (8 lights).
   - A **paved forecourt** (−0.60), a **2.00 m path** to the street, and a paved link east to the driveway.
   - The **driveway and a 7.10 m turning apron** to the east-facing garage door, rising 1:11 from the street.
   - A paved **side path** north of the garage (back door, garage side door, garden).
   - **Lawns** at the front and in the garden.
   - Four **small trees**: two framing the steps, one on the front lawn by the garage wing, one in the garden by the terrace.
   - Two **clipped round shrubs** flanking the steps, **low shrubs** in P1 and P2, and **ornamental grasses** in P3.
9. **The garage wing now belongs to the house.**
   - It shares the lower roof: the same plate, the same +6.30 top and the same 400 fascia, running unbroken from the house's west end to the garage's east end.
   - It uses the same charcoal panels and the same window band, and its stone matches the stone at the entry.
   - To make this work, its roof went up from +5.70 (v2) to +6.30, so the rec room ceiling is now +5.90 (3.20 clear; v2 had 2.70).

### What did not change

The plans, every room and its size, both stairs, the fire door, the garage size and the side entry are all exactly as in v2. All wall centre lines and room outlines in `design.json` are unchanged.

## Materials (tags used on the elevations)

| Tag | Material | Where |
|---|---|---|
| A | Dark charcoal panel cladding: through-coloured fibre-cement or aluminium rainscreen panels, 1200 x 600, open joints | All walls not marked B, house and garage wing |
| B | Natural split-face stone, grey-buff, coursed | Entry pier, entry cheek wall, the ground-floor wall beside the front door, garage street wall and crook wall (to +2.70), terrace piers, bed edges (with a concrete coping) |
| C | Warm timber soffit boards (oiled thermally modified ash or cedar) with recessed warm-white LED downlights | Under every overhang, the porch / balcony and the terrace roof |
| D | Frameless laminated toughened glass balustrade, 1.10 high | Street balcony, three sides |
| E | Dark charcoal / black aluminium | Window and door frames, 400 fascias, flush sectional garage door; the front door is a charcoal pivot door |
| – | Roofs: pale grey single-ply membrane on tapered insulation. Paving: large-format grey pavers. Driveway: dark permeable block paving. Gravel strips along the house front | |

## Rooms (clear inside sizes, width east-west x depth north-south)

All rooms are the same size as in v2.

### Ground floor (±0.00; garage −0.15; ceiling +2.80)

| Room | Size | Area |
|---|---|---|
| Entrance hall (with the stair) | 2.50 x 4.58 | 11.5 m² |
| Living room (open plan) | 6.00 x 4.70 | 28.2 m² |
| Dining area (open plan, incl. the passage to the utility) | 3.40 x 4.70 | 17.8 m² |
| Kitchen with island | 4.00 x 3.50 | 14.0 m² |
| Guest WC | 1.50 x 2.00 | 3.0 m² |
| Utility / laundry (garage door and back door) | 2.38 x 3.66 | 8.7 m² |
| Snug / playroom * | 3.58 x 4.58 | 16.4 m² |
| Office * | 2.96 x 4.58 | 13.6 m² |
| Coats * | 1.50 x 2.46 | 3.7 m² |
| Plant room * | 2.38 x 2.00 | 4.8 m² |
| **Garage** (two cars + stair), clear height 2.40 | 7.60 x 6.50 (parking bay 6.60 x 6.50) | 49.4 m² |

### First floor (+3.20; rec room +2.70)

| Room | Size | Area | Ceiling |
|---|---|---|---|
| Main bedroom | 4.50 x 4.58 | 20.6 m² | +5.90 (2.70 clear) |
| En-suite | 3.86 x 2.28 | 8.8 m² | +5.90 |
| Walk-in wardrobe | 2.10 x 2.18 | 4.6 m² | +5.90 |
| Flex room / guest bedroom * (opens onto the balcony) | 3.58 x 4.58 | 16.4 m² | +5.90 |
| Linen * | 1.64 x 2.18 | 3.6 m² | +5.90 |
| Landing | 13.40 x 1.12 | 15.0 m² | +6.40 (3.20 clear) |
| Bedroom 2 | 4.10 x 3.46 | 14.2 m² | +6.40 |
| Bedroom 3 | 4.10 x 3.46 | 14.2 m² | +6.40 |
| Family bathroom | 2.50 x 3.46 | 8.7 m² | +6.40 |
| Study | 2.34 x 3.46 | 8.1 m² | +6.40 |
| **Rec room** (over the garage) | 7.60 x 6.50 | 49.4 m² (45.9 m² clear of the stairwell) | +5.90 (3.20 clear) |

\* = space added in v1, not in the original brief.

### Outdoor spaces

| Space | Size | Area | Level |
|---|---|---|---|
| Covered entry porch | 3.00 x 2.10 | 6.3 m² | ±0.00 |
| Street balcony | 6.90 x 2.10 | 14.5 m² | +3.15 |
| Covered garden terrace | 10.90 x 3.90 | 42.5 m² | −0.02 |

Gross areas are unchanged: house 280 m², garage 57 m², rec room 57 m², **394 m² in total**, plus 63.3 m² of covered outdoor space.

## Key levels

| Item | Level |
|---|---|
| Street, front lawn, forecourt | −0.60 |
| Garden, garage floor, driveway apron | −0.15 |
| House ground floor, porch | ±0.00 |
| Ground-floor ceiling, porch / balcony / terrace soffits | +2.80 |
| Rec room floor | +2.70 |
| Balcony deck | +3.15 |
| First floor, terrace roof top | +3.20 |
| Balcony balustrade top | +4.25 |
| Lower roof soffit, south first-floor ceilings, rec room ceiling | +5.90 |
| Lower roof top (house south part + garage wing) | +6.30 |
| North first-floor ceilings | +6.40 |
| Upper roof soffit / top | +6.50 / +6.90 |

## Where a structural engineer is needed

The drawings show only the structure the design needs. All of it must be designed by an engineer:

1. **The 1.50 m street cantilever** of the lower roof, and the 1.00 / 1.20 / 0.60 m overhangs, inside a 400 mm edge: joist or steel sizes, deflection, wind uplift.
2. **The step between the roofs.** The upper roof's south edge sits on the step wall F-STEP along the landing wall (14 m long). It needs a steel beam carried on the end walls (or on posts in the partitions).
3. **The balcony / porch slab.** It cantilevers 2.10 m from the first-floor structure, propped by the stone pier and the cheek wall. It needs a thermally broken connection, the balcony live load, the glass barrier load and waterproofing over the porch.
4. **The terrace roof.** A steel beam spans about 4.7 m twice (pier – post – pier), with a 0.60 m cantilever and a ledger into the house wall. The piers, the post and their pad foundations need sizing.
5. **The stone piers and cheek wall.** They carry load, so each needs a structural core (steel or concrete) faced with stone.
6. **Large openings.**
   - New in v3: the 4.80 m living door, the 2.80 m dining door, the 3.60 m main-bedroom window and the 5.20 m rec room window.
   - Also needed, but unchanged from v2: the 4.80 m garage door.
7. **The raised beds.** They retain 450 mm of soil.
8. **Foundations** are placeholders, as in v2.

## What I could not do, or had to decide

1. **The entry is recessed by the porch, not by moving the door.** The front door stays in the house wall line, because pushing it back would have shortened the hall below its 2.5 x 4 m brief and crowded the stair foot. The recess comes from the 2.10 m deep porch, which has the stone cheek wall on one side, the stone pier on the other and the balcony above.
2. **The balcony is off the flex room, not the main bedroom.** The entry sits in front of the snug and the hall, and the only first-floor room above it with an outside wall is the flex room / guest bedroom. The en-suite clerestory (obscure glass, sill +4.80) also faces the balcony.
3. **The street front is 0.45 m below the garden.** Wide entry steps need a level difference, so I set the street, front lawn and forecourt at −0.60. The garden stays at −0.15. The driveway ramps up 1:11 to the level apron, and a grassed bank takes up the difference along the west side. The rest of the site is assumed:
   - The street boundary is 8.00 m in front of the house.
   - The plot is about 33 m wide.
   - Please check these against the real site.
4. **Ceiling heights changed.**
   - Ground floor: 2.80 (v2: 2.70).
   - South first-floor rooms: a flat 2.70.
   - North first-floor rooms and landing: 3.20, because of the taller top box.
   - Rec room: 3.20.
5. **Bedroom windows on the garden side have sills at +3.50,** 0.30 above the floor. This keeps them clear of the terrace roof's upstand and stops anyone treating the terrace roof as a balcony (it is not walkable). The floor-to-ceiling first-floor windows on the south have fixed laminated lower panes for guarding.
6. **Bed P1 is partly under the balcony,** so it needs drip irrigation and shade-tolerant planting. Bed P3 is partly under the garage overhang.
7. **No gutters on the fascias.** To keep the fascias thin, all three roofs drain to internal outlets or a concealed box gutter, with downpipes boxed in the walls (one beside the terrace post). Pipe sizes and routes need a plumber or engineer.
8. **The rec room is still not linked to the first-floor landing,** for the same reasons as in v2.
9. **The section moved.** It now runs through the entry, house and terrace (x = 5.80 m), because that is where the new design is. The v2 section through the garage stair is still valid: the stair is unchanged; only the garage roof above it is higher.
10. **The sample view is an isometric seen from above,** so the timber soffits themselves cannot be seen. They are suggested by a warm edge strip and light pools, and drawn properly in the elevations and section. The covered terrace is hidden behind the house in this view. The view is hand-built from the same coordinates; it is not a render, and no image-generation model was used.
11. **No species list,** as asked: plants are named only as "small tree", "low shrubs", "clipped round shrub" and "ornamental grasses".
12. **Not checked visually or automatically.** I wrote every SVG by hand from coordinates and could not open or render them in this session. I also could not run an automated comparison against `design.json`. I checked the numbers drawing by drawing and fixed the overlaps I found (two labels on dark cladding, one label over a wall). Please look through the sheets for crowded labels; the dimension and level lines cross the drawings in places.
13. **Not designed:** structure (see above), drainage sizing, fire separation details (garage wall and fire door, as v2), insulation, building regulations and planning.

## How design.json maps to the drawings

- Same layout and conventions as v2: `levels`, `materials`, `floors[].walls`, `openings`, `rooms`, `stairs`, `slabs`, `roofs` and `areas_m2`.
- New sections: `outdoor_spaces`, `balconies`, `balustrades`, `piers_and_posts`, `feature_walls`, `soffit_lights` and `landscape`. The `landscape` section holds `planting_beds` (outlines and edge heights), `steps` (with the riser lights), `paved_areas`, `driveway`, `lawns`, `trees` and `shrubs` (each with a position, height and spread).
- Wall coordinates are centre lines; openings are positioned along their wall from its start point. Sill and head heights are absolute levels in mm, so they read straight off the elevations.
- Changed wall ids:
  - The first-floor west and east walls are split at the roof step: `F-W1` / `F-W2` and `F-E1` / `F-E2`.
  - The step wall is `F-STEP`.
  - Stone areas on charcoal walls are `feature_zones`.
- Changed opening ids:
  - `D23` (dining sliding doors) replaces v2 `W04`.
  - `D24` (flex room balcony door) replaces v2 `W10`.
- Plan drawing coordinates: paper X = 45 + x/100, Y = 165 − y/100 (mm). Elevations and the section give their own mapping in a comment at the top of each file.
