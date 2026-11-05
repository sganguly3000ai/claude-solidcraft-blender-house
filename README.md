# Dream It, Design It: the files

These are the files from the video **[Claude Opus 5.5, SolidCraft, Blender: Dream Home Build Workflow](https://youtu.be/MCdjk965ThA)**
(YouTube channel **Unfolding It**). With them you can rebuild
the same house on your own computer: the CAD model in SolidCraft, then the furnished, decorated scene in Blender.

The same data files always give the same model. You do not need Claude to rebuild it: Claude's part is already done,
and its results are the data files in this folder.

Everything sits in this one folder. Run every command below **from inside this folder**.

## What you need

| Tool | What it does here | Where to get it |
|---|---|---|
| **Node.js** (version 18 or newer; made with 22) | runs the build and check scripts (`.mjs`) | https://nodejs.org |
| **SolidCraft** (made with 0.18.2) | turns the build script's output into the CAD model, with no window | its own GitHub page: https://github.com/tangency-labs/solidcraft (the version used: https://github.com/tangency-labs/solidcraft/releases/tag/v0.18.2) |
| **Blender** (made with 5.2) | makes it look real: materials, lights, furniture, decor | https://www.blender.org |

Tell the scripts where SolidCraft's command-line tool is, once per terminal (only needed for the checks):

```powershell
# Windows PowerShell (use your own path)
$env:SOLIDCRAFT_CLI = "C:\Tools\SolidCraft-0.18.2\solidcraft-0.18.2-windows-x64-portable\solidcraft-cli.exe"
```
```bash
# macOS / Linux
export SOLIDCRAFT_CLI=/path/to/solidcraft-cli
```

In the commands below, `solidcraft-cli` and `blender` stand for those programs. Use their full paths if they are not on
your PATH (on Windows, for example `& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"`).

## What to run, in order

### 1. DESIGN: build the CAD model (SolidCraft)

```bash
node build_home.mjs ground.json
solidcraft-cli run home_v7_script.json --out home_v7.obj --save home_v7.solidcraft
```

- `build_home.mjs` reads `design.json` (the house Claude designed) and the alteration files, and writes
  `home_v7_script.json`: the model as SolidCraft commands. `ground.json` includes `garden.json`, which includes
  `addition.json`, so naming `ground.json` builds all of them.
- SolidCraft runs those commands and writes the model: `home_v7.obj` (for Blender) and `home_v7.solidcraft`
  (open it in the SolidCraft app and try the parameters).
- Want the original two-storey house only, before any alteration? Run `node build_home.mjs` with no file. It writes
  `home_v4_script.json`; then use `home_v4` in place of `home_v7` in the SolidCraft command.

### 2. DREAM: make it look real (Blender, no window)

```bash
blender -b --factory-startup -P import_home_v4.py -- home_v7.obj home_v7_import.blend home_v7_import_check.json
blender -b home_v7_import.blend --factory-startup -P dress_home_v4.py -- . home_v7_dressed.blend home_v7_dressed_check.json home_v7
blender -b home_v7_dressed.blend --factory-startup -P furnish.py -- . home_v7_furnished.blend home_v7_furnished_check.json furnishing_living_dining.json furnishing_kitchen.json furnishing_ensuite.json
blender -b home_v7_furnished.blend --factory-startup -P decorate.py -- . home_v7_decorated.blend home_v7_decorated_check.json
```

| Step | Reads | Writes |
|---|---|---|
| `import_home_v4.py` | `home_v7.obj` | `home_v7_import.blend` |
| `dress_home_v4.py` | the model, `design.json`, the alteration files | materials, window frames, lights, ground, street, cameras: `home_v7_dressed.blend` |
| `furnish.py` | `furnishing_*.json` with their `rooms_*.json` | the furniture, built piece by piece: `home_v7_furnished.blend` |
| `decorate.py` | `decor_tour.json`, `design.json` | floors, pictures, lamps and more for the tour: `home_v7_decorated.blend` |

Open `home_v7_decorated.blend` in Blender and look around. You can change anything there, but a save in Blender never
gets back to the data: the scripts rebuild the scene from the data files every time.

Each step also writes a small `_check.json` with what it made.

### 3. The checks (optional)

```bash
node check_home.mjs home_v7
node check_ground.mjs home_v7
node check_furnishing.mjs furnishing_living_dining.json home_v7
node check_furnishing.mjs furnishing_kitchen.json home_v7 --front-min 1000
node check_furnishing.mjs furnishing_ensuite.json home_v7 --front-min 700
```

- `check_home.mjs`: every part's volume against `design.json`; SolidCraft's clash check over all pairs (with a test
  clash that must be found); nothing floats; two builds are byte-identical; the saved model is the current build.
- `check_ground.mjs`: no lawn or soil stands as a step of 100 mm or more.
- `check_furnishing.mjs`: furniture inside its room, no overlaps, clear doorways and walkways, and no clash with the
  house (SolidCraft). It also draws a plan: `furnishing_<rooms>_plan.svg`.

Each check prints PASS or FAIL and writes its results to a `_checks.json` file.

## The files

**PLAN: what Claude (Opus) designed**

| File | What it is |
|---|---|
| `design.json` | the whole house and garden as data: the baseline everything is built from |
| `01_..._09_*.svg` | the nine drawings Claude made with it (plans, elevations, section, a sample view) |
| `design_README.md` | Claude's own notes on the design |
| `prompt.txt` | the prompt I gave Opus (see the note below) |

**The alterations** (each its own data file; `design.json` is never changed)

| File | What it adds |
|---|---|
| `addition.json` | the third floor: two rooms, the stair and lift tower, the glass walkway |
| `garden.json` | the terraced back garden with steps and raised beds |
| `ground.json` | the ground and driveway levels, so the house matches the terrain |
| `furnishing_*.json` + `rooms_*.json` | the furniture for the living and dining room, the kitchen and the en-suite (`existing_for_kitchen.json`: the dining furniture next door, used by the kitchen check) |
| `decor_tour.json` | floors, pictures, lamps and other decor for the video tour |
| `*_brief.md`, `furnishing_*_prompt.txt` | what I asked for each alteration |

**The scripts**

| Script | Language | Job |
|---|---|---|
| `build_home.mjs` (+ `build_addition.mjs`, `build_garden.mjs`, `build_ground.mjs`) | JavaScript (Node) | data -> SolidCraft commands |
| `check_home.mjs`, `check_ground.mjs` (+ `ground_edges.mjs`), `check_furnishing.mjs` | JavaScript (Node) | the checks |
| `import_home_v4.py`, `dress_home_v4.py`, `furnish.py`, `decorate.py` | Python, run inside Blender | the Blender scene |

Every script was written by Claude Code.

## A note on the prompt

You do not need `prompt.txt` to get my results: start from `design.json`. Asking Claude again, even with the same
prompt, gives a different design each time. The data file is the baseline.

`prompt.txt` is here to show what I asked. It was the third round of the design: it builds on the earlier round
("the folder v2") and on two style photos of a house I liked. Those photos are someone else's pictures, so they are
not in this repo. To try it yourself, use your own photos and your own words.

## What this is, and is not

A proof of concept, not a permit set. An architect or engineer still has to check the structure, the stair and lift
sizes, and the building rules where you live.

## Licence

MIT (see `LICENSE`): use, change and share these files freely; keep the copyright notice. SolidCraft, Blender and
Node.js are not part of this repo and come with their own licences.
