# Dress the imported model for a dusk look like the two reference photos (ref\front.jpg, side.jpg).
# Pass 2. Data in: the model's own colour groups (home_v4_script.json, appearance.assign) pick each part's material;
# design.json gives the cladding module, soffit downlights, step lights, rooms (interior light) and trees.
# The model's geometry is never changed. Added things (window frames, light dots, room lights, ground, street) live in
# their own "Dressing" collections and are derived from the model or design.json. No render here.
# Run: blender -b <import.blend> --factory-startup -P dress_home_v4.py -- <project dir> <out.blend> <out.json>
import bpy, bmesh, sys, json, os, re, math
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
proj, out_blend, out_json = [os.path.abspath(a) for a in args[:3]]   # plain names / . work too
MODEL = args[3] if len(args) > 3 else "home_v4"   # home_v5 = v4 + addition.json; home_v7 = all the alterations
script = json.load(open(os.path.join(proj, f"{MODEL}_script.json")))
ADDN = GARDN = None   # the addition (addition.json) and the garden (garden.json, home_v6: it includes the addition)
def take(j):   # a data file and every file it includes (ground.json, home_v7 -> garden -> addition)
    global ADDN, GARDN
    for inc in j.get("includes", []): take(json.load(open(os.path.join(proj, inc))))
    if "top_boxes" in j: ADDN = j
    if "beds" in j: GARDN = j
if True:   # one folder: the alteration files sit next to this script
    for fn in ("addition.json", "garden.json", "ground.json"):
        f = os.path.join(proj, fn)
        if os.path.exists(f) and json.load(open(f))["model_name"] == MODEL: take(json.load(open(f)))
AROOF = lambda v: (ADDN["roof_level"] + float(v[4:] or 0)) if isinstance(v, str) else v   # "roof+N" -> mm at default
D = json.load(open(os.path.join(proj, "design.json")))
sc = bpy.context.scene

SOFFIT_LOOK = "photo"   # the photos show dark soffits; design.json says warm timber ("design")
WARM = (1.0, 0.62, 0.32)   # ~2700 K
PANEL_W, PANEL_H, JOINT = 1.2, 0.6, 0.010   # design.json: 1200 x 600 module, open 10 mm joints

# ---------- node helpers ----------
class NT:
    def __init__(self, m): self.t = m.node_tree; self.n = self.t.nodes; self.p = self.n["Principled BSDF"]
    def new(self, kind, **inputs):
        nd = self.n.new(kind)
        for k, v in inputs.items(): self.set(nd.inputs[k], v)
        return nd
    def set(self, sock, v):
        if hasattr(v, "is_output") or hasattr(v, "links"): self.t.links.new(v, sock)
        else: sock.default_value = v
    def math(self, op, a, b=0.0):
        nd = self.n.new("ShaderNodeMath"); nd.operation = op
        self.set(nd.inputs[0], a); self.set(nd.inputs[1], b); return nd.outputs[0]
    def ramp(self, fac, c0, c1, p0=0.0, p1=1.0):
        nd = self.n.new("ShaderNodeValToRGB"); e = nd.color_ramp.elements
        e[0].position, e[0].color = p0, (*c0, 1); e[1].position, e[1].color = p1, (*c1, 1)
        self.set(nd.inputs["Fac"], fac); return nd.outputs["Color"]
    def face_uz(self):
        """(u, z) in metres across a wall face: u runs along the face (y on faces whose normal is along x, else x)."""
        g = self.n.new("ShaderNodeNewGeometry")
        pos = self.n.new("ShaderNodeSeparateXYZ"); self.set(pos.inputs[0], g.outputs["Position"])
        nrm = self.n.new("ShaderNodeSeparateXYZ"); self.set(nrm.inputs[0], g.outputs["Normal"])
        f = self.math("GREATER_THAN", self.math("ABSOLUTE", nrm.outputs["X"]), 0.5)
        u = self.math("ADD", pos.outputs["X"], self.math("MULTIPLY", f, self.math("SUBTRACT", pos.outputs["Y"], pos.outputs["X"])))
        return u, pos.outputs["Z"]

def new_mat(name, base, rough, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = NT(m); nt.set(nt.p.inputs["Base Color"], (*base, 1)); nt.set(nt.p.inputs["Roughness"], rough)
    nt.set(nt.p.inputs["Metallic"], metal); return m, nt

def noise_mat(name, base, rough, metal=0.0, bump=0.0, scale=8.0, vary=0.0, dark=0.7):
    m, nt = new_mat(name, base, rough, metal)
    if bump or vary:
        tc = nt.new("ShaderNodeTexCoord"); nz = nt.new("ShaderNodeTexNoise", Scale=scale, Detail=6.0)
        nt.set(nz.inputs["Vector"], tc.outputs["Object"])
        if bump:
            b = nt.new("ShaderNodeBump", Strength=bump, Distance=0.02); nt.set(b.inputs["Height"], nz.outputs["Fac"])
            nt.set(nt.p.inputs["Normal"], b.outputs["Normal"])
        if vary:
            nt.set(nt.p.inputs["Base Color"], nt.ramp(nz.outputs["Fac"], [c * dark for c in base], base, 0.5 - vary / 2, 0.5 + vary / 2))
    return m

def panel_mat(name, base, rough, metal):
    """Rainscreen cladding: 1200 x 600 panels, open dark joints, slight tone change per panel."""
    m, nt = new_mat(name, base, rough, metal)
    u, z = nt.face_uz()
    du = nt.math("PINGPONG", u, PANEL_W / 2); dz = nt.math("PINGPONG", z, PANEL_H / 2)
    joint = nt.math("MAXIMUM", nt.math("LESS_THAN", du, JOINT / 2), nt.math("LESS_THAN", dz, JOINT / 2))
    cell = nt.new("ShaderNodeCombineXYZ")
    nt.set(cell.inputs["X"], nt.math("FLOOR", nt.math("DIVIDE", u, PANEL_W)))
    nt.set(cell.inputs["Y"], nt.math("FLOOR", nt.math("DIVIDE", z, PANEL_H)))
    wn = nt.new("ShaderNodeTexWhiteNoise"); nt.set(wn.inputs["Vector"], cell.outputs[0])
    tone = nt.ramp(wn.outputs["Value"], [c * 0.85 for c in base], [c * 1.15 for c in base])
    mix = nt.new("ShaderNodeMixRGB"); mix.blend_type = "MIX"
    nt.set(mix.inputs["Fac"], joint); nt.set(mix.inputs["Color1"], tone); nt.set(mix.inputs["Color2"], (0.004, 0.004, 0.005, 1))
    nt.set(nt.p.inputs["Base Color"], mix.outputs["Color"])
    b = nt.new("ShaderNodeBump", Strength=0.6, Distance=0.01); nt.set(b.inputs["Height"], nt.math("SUBTRACT", 1.0, joint))
    nt.set(nt.p.inputs["Normal"], b.outputs["Normal"])
    return m

def stone_mat(name):
    """Split-face stone, random-length coursed (brick pattern on the face + strong rough bump)."""
    m, nt = new_mat(name, (0.2, 0.19, 0.17), 0.9)
    u, z = nt.face_uz()
    v = nt.new("ShaderNodeCombineXYZ"); nt.set(v.inputs["X"], u); nt.set(v.inputs["Y"], z)
    br = nt.new("ShaderNodeTexBrick", Scale=1.0, **{"Mortar Size": 0.004, "Mortar Smooth": 0.3, "Brick Width": 0.95,
                                                     "Row Height": 0.24, "Bias": 0.0})
    br.offset, br.squash, br.squash_frequency = 0.37, 0.6, 2
    nt.set(br.inputs["Vector"], v.outputs[0])
    nt.set(br.inputs["Color1"], (0.30, 0.30, 0.30, 1)); nt.set(br.inputs["Color2"], (0.17, 0.17, 0.175, 1))
    nt.set(br.inputs["Mortar"], (0.09, 0.09, 0.09, 1))
    tc = nt.new("ShaderNodeTexCoord"); nz = nt.new("ShaderNodeTexNoise", Scale=14.0, Detail=8.0, Roughness=0.7)
    nt.set(nz.inputs["Vector"], tc.outputs["Object"])
    mix = nt.new("ShaderNodeMixRGB"); mix.blend_type = "MULTIPLY"
    nt.set(mix.inputs["Fac"], 0.6); nt.set(mix.inputs["Color1"], br.outputs["Color"]); nt.set(mix.inputs["Color2"], nt.ramp(nz.outputs["Fac"], (0.6, 0.6, 0.6), (1.3, 1.3, 1.25)))
    nt.set(nt.p.inputs["Base Color"], mix.outputs["Color"])
    h = nt.math("ADD", nt.math("MULTIPLY", nz.outputs["Fac"], 0.6), nt.math("MULTIPLY", nt.math("SUBTRACT", 1.0, br.outputs["Fac"]), 0.4))
    b = nt.new("ShaderNodeBump", Strength=0.9, Distance=0.03); nt.set(b.inputs["Height"], h)
    nt.set(nt.p.inputs["Normal"], b.outputs["Normal"])
    return m

def glass_mat(name, rough=0.0, alpha=0.14):
    """See-through glass as a thin blended reflective layer (EEVEE's screen-space refraction smeared the rooms)."""
    m, nt = new_mat(name, (0.0, 0.0, 0.0), rough)
    nt.set(nt.p.inputs["Alpha"], alpha); nt.set(nt.p.inputs["Specular IOR Level"], 0.8)
    m.surface_render_method = "BLENDED"
    return m

def emit_mat(name, strength):
    m, nt = new_mat(name, (0.05, 0.05, 0.05), 0.5)
    nt.set(nt.p.inputs["Emission Color"], (*WARM, 1)); nt.set(nt.p.inputs["Emission Strength"], strength); return m

# INSIDE vs OUTSIDE: an outer wall or roof is one solid in the model, so one material covers both sides. Each
# footprint below (from design.json's room outlines: the main house, the garage wing) lets a material test, per pixel,
# whether the surface faces into the house (a point 10 cm along its normal lies inside a footprint); inside faces get
# plaster / a white ceiling, outside faces keep the cladding, stone or dark soffit.
# Each footprint also has a height range (the main house up to its highest ceiling, 6.5 m), so the addition's roof
# overhangs above the house stay outside; the addition's rooms (addition.json) are footprints of their own.
def footprints():
    wings = {"main": [], "garage": []}
    for r in D["rooms"]:
        xs = [p[0] / 1000 for p in r["polygon"]]; ys = [p[1] / 1000 for p in r["polygon"]]
        wings["garage" if min(xs) >= 13.7 else "main"].append((min(xs), max(xs), min(ys), max(ys)))
    top = {"main": 6.6, "garage": 6.0}
    f = [(min(b[0] for b in v), max(b[1] for b in v), min(b[2] for b in v), max(b[3] for b in v), -1.0, top[k]) for k, v in wings.items() if v]
    for r in (ADDN or {}).get("rooms", []):
        f.append((r["x"][0] / 1000, r["x"][1] / 1000, r["y"][0] / 1000, r["y"][1] / 1000, AROOF(r["z"][0]) / 1000 - 0.3, AROOF(r["z"][1]) / 1000 + 0.15))
    return f
FOOT = footprints()

def with_interior(m, base, rough):
    """Mix in an interior finish where the surface faces into a footprint."""
    nt = NT(m); out = next(n for n in nt.n if n.type == "OUTPUT_MATERIAL")
    g = nt.n.new("ShaderNodeNewGeometry")
    off = nt.n.new("ShaderNodeVectorMath"); off.operation = "MULTIPLY_ADD"
    nt.set(off.inputs[0], g.outputs["Normal"]); off.inputs[1].default_value = (0.1, 0.1, 0.1); nt.set(off.inputs[2], g.outputs["Position"])
    s = nt.n.new("ShaderNodeSeparateXYZ"); nt.set(s.inputs[0], off.outputs[0])
    mask = None
    for x0, x1, y0, y1, z0, z1 in FOOT:
        r = nt.math("MULTIPLY", nt.math("MULTIPLY", nt.math("GREATER_THAN", s.outputs["X"], x0), nt.math("LESS_THAN", s.outputs["X"], x1)),
                    nt.math("MULTIPLY", nt.math("GREATER_THAN", s.outputs["Y"], y0), nt.math("LESS_THAN", s.outputs["Y"], y1)))
        r = nt.math("MULTIPLY", r, nt.math("MULTIPLY", nt.math("GREATER_THAN", s.outputs["Z"], z0), nt.math("LESS_THAN", s.outputs["Z"], z1)))
        mask = r if mask is None else nt.math("MAXIMUM", mask, r)
    inner = nt.n.new("ShaderNodeBsdfPrincipled")
    inner.inputs["Base Color"].default_value = (*base, 1); inner.inputs["Roughness"].default_value = rough
    mix = nt.n.new("ShaderNodeMixShader"); nt.set(mix.inputs["Fac"], mask)
    nt.set(mix.inputs[1], nt.p.outputs["BSDF"]); nt.set(mix.inputs[2], inner.outputs["BSDF"])
    nt.set(out.inputs["Surface"], mix.outputs["Shader"])
    return m

PLASTER, CEILING = (0.72, 0.62, 0.50), (0.80, 0.78, 0.74)
CHARCOAL = with_interior(panel_mat("Charcoal_Panel", (0.085, 0.09, 0.098), 0.38, 0.35), PLASTER, 0.9)   # RAL 7021 tone
STONE = with_interior(stone_mat("Stone_SplitFace"), PLASTER, 0.9)
BLACK = new_mat("Black_Metal", (0.012, 0.012, 0.013), 0.35, 0.8)[0]
M = {
    "#2b2d31": CHARCOAL,
    "#3a3d42": CHARCOAL,                       # roofs + balcony: fascias are cladding too; soffits/tops below
    "#a89f8f": STONE,
    "#9cc3d6": glass_mat("Glass_Clear", 0.02, 0.2),
    "#1f2023": BLACK,
    "#c9c6bf": noise_mat("Slab_Floor", (0.48, 0.45, 0.40), 0.55, bump=0.05, scale=4, vary=0.2, dark=0.85),
    "#8d8a84": noise_mat("Plinth_Stone", (0.30, 0.29, 0.27), 0.8, bump=0.2, scale=12),
    "#b08a5a": noise_mat("Stair_Timber", (0.35, 0.22, 0.11), 0.5, vary=0.3, scale=30),
    "#e6e1d8": noise_mat("Interior_Warm", (0.72, 0.62, 0.50), 0.9),
    "#b8b6ae": noise_mat("Paving_LightGrey", (0.40, 0.40, 0.38), 0.7, bump=0.1, scale=3, vary=0.2),
    "#9a9a94": noise_mat("Gravel", (0.30, 0.30, 0.28), 1.0, bump=0.5, scale=80, vary=0.5),
    "#55575a": noise_mat("Driveway_Block", (0.09, 0.09, 0.095), 0.85, bump=0.15, scale=40, vary=0.3),
    "#668f44": noise_mat("Site_Ground", (0.06, 0.10, 0.035), 1.0, vary=0.4, scale=2),
    "#6f9a4a": noise_mat("Lawn", (0.07, 0.15, 0.04), 1.0, bump=0.2, scale=200, vary=0.5),
    "#5a4632": noise_mat("Bark", (0.08, 0.06, 0.04), 0.9),
    "#557a3a": noise_mat("Tree_Crown", (0.30, 0.16, 0.03), 0.8, vary=0.7, scale=3),   # autumn, like the photos
    "#4f7a3c": noise_mat("Shrub", (0.03, 0.08, 0.025), 0.8, vary=0.6, scale=5),
    "#9aa35a": noise_mat("Grass_Clump", (0.14, 0.16, 0.06), 0.9, vary=0.5, scale=8),
}
GLASS_BAL = glass_mat("Glass_Balustrade", 0.02, 0.18)
GLASS_EDGE = new_mat("Glass_Edge", (0.30, 0.50, 0.45), 0.05)[0]   # polished laminated edge: the green line real glass shows
FRAMELESS = lambda n: n.startswith(("Glass_BL", "Glass_A_Rail", "Glass_A_Lift"))   # balustrades, the addition's railings and lift shaft
OPEN_DOORS = {"Glass_D24": 0.5}
OPEN_SOLID = {"Door_D04"}   # STAGING, not model: solid door leaves shown open (hidden from the render, kept in the file)   # STAGING, not model: sliding doors shown part open (share of one leaf); model pane = closed
GLASS_OBS = emit_mat("Glass_Obscure", 0.6)   # obscure glass: a soft warm glow, no view in
SOFFIT = with_interior(new_mat("Soffit_Dark", (0.035, 0.037, 0.04), 0.5, 0.2)[0] if SOFFIT_LOOK == "photo"
                       else noise_mat("Soffit_Timber", (0.42, 0.25, 0.12), 0.55, vary=0.3, scale=20), CEILING, 0.9)
MEMBRANE = new_mat("Roof_Membrane", (0.35, 0.36, 0.37), 0.7)[0]
DECK = noise_mat("Balcony_Pavers", (0.30, 0.29, 0.28), 0.6, vary=0.2, scale=3)
LED = emit_mat("LED_Warm", 40.0)

norm = lambda n: re.sub(r" \((\d+)\)$", r"_(\1)", n)
group = {}
for c in script["commands"]:
    if c["command"] == "appearance.assign":
        for b in c["params"]["bodies"]: group[norm(b)] = c["params"]["color"]

model = [o for o in bpy.data.objects if o.type == "MESH"]
unassigned = []
for o in model:
    hexc = group.get(o.name) or group.get(re.sub(r"_\(\d+\)$", "", o.name))
    if hexc is None: unassigned.append(o.name); continue
    mats = [M[hexc]]
    if FRAMELESS(o.name): mats = [GLASS_BAL]
    elif o.name in ("Glass_W12", "Glass_W16"): mats = [GLASS_OBS]   # obscure glass (design.json)
    o.data.materials.clear()
    for m in mats: o.data.materials.append(m)
    if hexc == "#3a3d42":   # roofs + balcony: undersides = soffits, tops = membrane / pavers
        o.data.materials.append(SOFFIT); o.data.materials.append(DECK if o.name.startswith("B_") else MEMBRANE)
        for poly in o.data.polygons:
            poly.material_index = 1 if poly.normal.z < -0.7 else 2 if poly.normal.z > 0.7 else 0

def coll(name):
    c = bpy.data.collections.new(name); sc.collection.children.link(c); return c

def boxes_obj(name, boxes, mat, col, mm=False):
    """One mesh from a list of (min, max) world boxes. mm=True builds it in millimetres at scale 0.001, like the model's
    parts, so a material's texture comes out at the same size as on them."""
    k = 1000.0 if mm else 1.0
    bm = bmesh.new()
    for lo, hi in boxes:
        r = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        for v in r:
            v.co = Vector([(lo[i] + (hi[i] - lo[i]) * (v.co[i] + 0.5)) * k for i in range(3)])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    if mm: ob.scale = (0.001,) * 3
    return ob

def bbox(o):
    w = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(v[i] for v in w) for i in range(3)]), Vector([max(v[i] for v in w) for i in range(3)])

# ---------- WINDOW FRAMES (trim: black aluminium), derived from each glass pane ----------
FR, DEPTH = 0.05, 0.09
frames = coll("Dressing_Frames"); n_frames = 0
def span_box(thin, along, t0, t1, b0, b1, h0, h1):
    p, q = [0, 0, 0], [0, 0, 0]
    p[thin], q[thin] = t0, t1; p[along], q[along] = b0, b1; p[2], q[2] = h0, h1
    return (Vector(p), Vector(q))

# balustrade panes (frameless, design.json: "in a recessed base channel"): a dark channel lip and polished glass edges
n_bal = 0
for o in model:
    if not FRAMELESS(o.name): continue
    lo, hi = bbox(o); ext = hi - lo
    thin = 0 if ext.x < ext.y else 1; along = 1 - thin; c = (lo[thin] + hi[thin]) / 2
    a0, a1, z0, z1 = lo[along], hi[along], lo.z, hi.z
    boxes_obj("Channel_" + o.name[6:], [span_box(thin, along, c - 0.04, c + 0.04, a0, a1, z0, z0 + 0.05)], BLACK, frames)
    e, t = 0.012, ext[thin] / 2 + 0.001
    boxes_obj("Edge_" + o.name[6:], [span_box(thin, along, c - t, c + t, a0, a1, z1 - e, z1),
                                      span_box(thin, along, c - t, c + t, a0, a0 + e, z0, z1),
                                      span_box(thin, along, c - t, c + t, a1 - e, a1, z0, z1)], GLASS_EDGE, frames)
    n_bal += 1

for o in model:
    if o.name in OPEN_SOLID: o.hide_render = True

# sliding doors staged part open: the model's single pane is hidden from the render (kept in the file) and two leaves
# of the same total size take its place, the sliding one on the inner track, moved over the fixed one
n_open = 0
for o in model:
    if o.name not in OPEN_DOORS: continue
    lo, hi = bbox(o); ext = hi - lo
    thin = 0 if ext.x < ext.y else 1; along = 1 - thin; c = (lo[thin] + hi[thin]) / 2
    a0, a1, z0, z1 = lo[along], hi[along], lo.z, hi.z; half = (a1 - a0) / 2; shift = OPEN_DOORS[o.name] * half
    o.hide_render = True; n_open += 1
    for k, (b0, b1, tc) in enumerate([(a0, a0 + half, c - 0.035), (a0 + half - shift, a1 - shift, c + 0.035)]):
        leaf = "Leaf_" + o.name[6:] + ("_fixed" if k == 0 else "_sliding")
        boxes_obj(leaf + "_glass", [span_box(thin, along, tc - 0.012, tc + 0.012, b0, b1, z0, z1)], M["#9cc3d6"], frames)
        boxes_obj(leaf + "_frame", [span_box(thin, along, tc - 0.03, tc + 0.03, b0, b1, z0, z0 + FR),
                                    span_box(thin, along, tc - 0.03, tc + 0.03, b0, b1, z1 - FR, z1),
                                    span_box(thin, along, tc - 0.03, tc + 0.03, b0, b0 + FR, z0, z1),
                                    span_box(thin, along, tc - 0.03, tc + 0.03, b1 - FR, b1, z0, z1)], BLACK, frames)
    boxes_obj("Frame_" + o.name[6:], [span_box(thin, along, c - DEPTH / 2, c + DEPTH / 2, a0, a1, z1 - FR, z1)], BLACK, frames)   # head track

for o in model:
    if not o.name.startswith("Glass_") or FRAMELESS(o.name) or o.name in OPEN_DOORS: continue
    lo, hi = bbox(o); ext = hi - lo
    thin = 0 if ext.x < ext.y else 1; along = 1 - thin
    c = (lo[thin] + hi[thin]) / 2; t0, t1 = c - DEPTH / 2, c + DEPTH / 2
    a0, a1, z0, z1 = lo[along], hi[along], lo.z, hi.z
    def bar(b0, b1, h0, h1): return span_box(thin, along, t0, t1, b0, b1, h0, h1)
    bars = [bar(a0, a1, z0, z0 + FR), bar(a0, a1, z1 - FR, z1), bar(a0, a0 + FR, z0, z1), bar(a1 - FR, a1, z0, z1)]
    w, h = a1 - a0, z1 - z0
    bays = max(1, math.ceil(w / 1.5))
    for i in range(1, bays):
        m = a0 + w * i / bays; bars.append(bar(m - FR / 2, m + FR / 2, z0, z1))
    if h >= 2.6:   # tall glazing: a transom with a fixed light above, like the photos
        tz = z0 + h * 0.78; bars.append(bar(a0, a1, tz - FR / 2, tz + FR / 2))
    boxes_obj("Frame_" + o.name[6:], bars, BLACK, frames); n_frames += 1

# ---------- LIGHTS from design.json (mm -> m) ----------
lights = coll("Dressing_Lights")
def add_light(name, kind, loc, energy, size=None, col=lights, radius=0.05):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = WARM
    if kind == "SPOT": ld.spot_size = size or 1.3; ld.spot_blend = 0.8
    if kind == "AREA": ld.shape = "SQUARE"; ld.size = size or 1.0
    else: ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld); ob.location = loc; col.objects.link(ob); return ob

dots = []
n_down = 0
for item in D["soffit_lights"]["items"]:
    z = item["z"] / 1000
    for x, y in item["points"]:
        n_down += 1; X, Y = x / 1000, y / 1000
        add_light(f"Downlight_{n_down:02d}", "SPOT", (X, Y, z - 0.03), 300, 1.9).data.spot_blend = 0.5
        dots.append((Vector((X - 0.04, Y - 0.04, z - 0.012)), Vector((X + 0.04, Y + 0.04, z - 0.002))))
n_riser = 0
for x, y, z in D["landscape"]["steps"][0]["riser_lights"]["points_xyz"]:
    n_riser += 1; X, Y, Z = x / 1000, y / 1000, z / 1000
    add_light(f"RiserLight_{n_riser}", "POINT", (X, Y - 0.12, Z + 0.03), 3, radius=0.02).data.use_shadow = False
    dots.append((Vector((X - 0.08, Y - 0.012, Z - 0.02)), Vector((X + 0.08, Y + 0.002, Z + 0.03))))
if GARDN:   # the garden steps go DOWN to the north: each riser faces north, its light sits in the riser's middle
    st = GARDN["steps"]
    for i in range(st["risers"]):
        Y = (st["first_riser_y"] + i * st["going"]) / 1000; Z = (st["top"] - (i + 0.5) * st["riser_height"]) / 1000
        for x in st["riser_lights_x"]:
            n_riser += 1; X = x / 1000
            add_light(f"RiserLight_{n_riser}", "POINT", (X, Y + 0.12, Z), 3, radius=0.02).data.use_shadow = False
            dots.append((Vector((X - 0.08, Y - 0.002, Z - 0.025)), Vector((X + 0.08, Y + 0.012, Z + 0.025))))

# Stage 6 fix (2026-10-27, Sam: "you can also investigate the bright spot"): the soft light's square is sized from the
# room's area, so in a long narrow room it stuck out through the walls. The landing (13.4 x 1.12 m) had a 2.71 m square
# that reached 0.8 m past its south wall, above the outside roof (light 6.35, roof top 6.30), and lit a bright patch on
# it. A square wider than 0.9 of either side of its room becomes a rectangle inside the room; energy unchanged.
fitted = []
def fit_to_room(l, w, d):
    s0 = l.data.size
    if s0 <= 0.9 * min(w, d): return
    l.data.shape = "RECTANGLE"; l.data.size, l.data.size_y = min(s0, 0.9 * w), min(s0, 0.9 * d)
    fitted.append(l.name)
# interior: one soft ceiling light per room + rows of small ceiling downlights (seen through the glass, like the photos)
CEIL = {"GF": 2.8, "FF_S": 5.9, "FF_N": 6.4}
DARK_ROOMS = ("Garage", "Plant", "Coats", "Linen", "Walk-in", "WC")
n_rooms = 0
for r in D["rooms"]:
    if r["name"].startswith(DARK_ROOMS): continue
    xs = [p[0] / 1000 for p in r["polygon"]]; ys = [p[1] / 1000 for p in r["polygon"]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    if r["floor"] == "GF": cz = CEIL["GF"]
    elif r["name"].startswith("Recreation"): cz = 5.9
    else: cz = CEIL["FF_S"] if y1 <= 4.94 + 0.01 else CEIL["FF_N"]
    n_rooms += 1
    rl = add_light(f"Room_{n_rooms:02d}", "AREA", ((x0 + x1) / 2, (y0 + y1) / 2, cz - 0.05), 6 * r["area_m2"],
                   size=0.7 * math.sqrt(r["area_m2"]))
    fit_to_room(rl, x1 - x0, y1 - y0)
    rl.data.color = (1.0, 0.42, 0.12)   # interiors read amber-gold through the glass in both photos
    nx, ny = max(1, round((x1 - x0) / 1.6)), max(1, round((y1 - y0) / 1.6))
    for i in range(nx):
        for j in range(ny):
            X = x0 + (i + 0.5) * (x1 - x0) / nx; Y = y0 + (j + 0.5) * (y1 - y0) / ny
            dots.append((Vector((X - 0.04, Y - 0.04, cz - 0.01)), Vector((X + 0.04, Y + 0.04, cz - 0.002))))
for r in (ADDN or {}).get("rooms", []):   # the addition's rooms (addition.json), lit the same way
    x0, x1, y0, y1 = r["x"][0] / 1000, r["x"][1] / 1000, r["y"][0] / 1000, r["y"][1] / 1000
    cz, area_m2 = AROOF(r["z"][1]) / 1000, (x1 - x0) * (y1 - y0)
    n_rooms += 1
    rl = add_light(f"Room_{n_rooms:02d}", "AREA", ((x0 + x1) / 2, (y0 + y1) / 2, cz - 0.05), 6 * area_m2, size=0.7 * math.sqrt(area_m2))
    fit_to_room(rl, x1 - x0, y1 - y0)
    rl.data.color = (1.0, 0.42, 0.12)
    nx, ny = max(1, round((x1 - x0) / 1.6)), max(1, round((y1 - y0) / 1.6))
    for i in range(nx):
        for j in range(ny):
            X = x0 + (i + 0.5) * (x1 - x0) / nx; Y = y0 + (j + 0.5) * (y1 - y0) / ny
            dots.append((Vector((X - 0.04, Y - 0.04, cz - 0.01)), Vector((X + 0.04, Y + 0.04, cz - 0.002))))
boxes_obj("LED_Dots", dots, LED, lights)

# ---------- GROUND, STREET, SKY ----------
site = bpy.data.objects["Site_Base"]; slo, shi = bbox(site)
ground = coll("Dressing_Ground")
gz = shi.z - 0.004
# Stage 6 (2026-10-26): the neighbour lawn used to be one box over the whole site, 120 mm ABOVE the street, so the street
# never showed. It now stops at the two sidewalks' outer edges (and leaves room for the apron, below); kerbs fill the
# 0.2 m gaps between sidewalk and street.
ASPHALT = noise_mat("Asphalt", (0.04, 0.04, 0.045), 0.8, bump=0.1, scale=60, vary=0.3)
# the driveway apron (Sam: "make the driveway apron permanent in the dressing"): the driveway's paving carried across
# the house-side sidewalk and a dropped kerb, sloping from the driveway's front edge down to the street. Its x range and
# height come from the model's Driveway where it meets the plot's front edge, so every model version dresses the same way.
drv = bpy.data.objects.get("Driveway"); apron = None
if drv:
    dv = [drv.matrix_world @ v.co for v in drv.data.vertices]
    front = [v for v in dv if abs(v.y - min(w.y for w in dv)) < 0.01]
    apron = (min(v.x for v in front), max(v.x for v in front), max(v.z for v in front))
st_top = gz - 0.12
# Stage 6c (2026-10-27), Sam: "the side walks where they cross the driveway - should be sloped as it is in ADA compliant
# sidewalk intersections". The apron was one 1-in-13 plane, so the sidewalk tilted 8% sideways across the driveway.
# Now it is a crossing as ADA guidance has it (not checked against a local code): across the driveway the walk keeps a
# level 1.2 m path (2% fall to the road); the cars' slope is a ramp in front of it down to a dropped kerb with a 13 mm
# lip; behind it a short ramp takes the driveway down to the walk. Each side, the sidewalk and kerb fall at 1 in 10 at
# most to meet it (flared wings), so there is no step anywhere. Depths are measured from the plot's front edge.
# Sam (2026-10-27): "that black patch between the road and the driveway should be concrete also but it should be sloped
# up from the road to the driveway - it should also account for the ada slopes on the side". The cars' ramp is now the
# sidewalk's concrete too (it already rose from the road; its sides are the 1-in-10 wings). Only the 0.3 m back ramp
# stays the driveway's paving.
D_BACK, D_PATH, D_KERB, D_ROAD = 0.3, 1.5, 2.0, 2.2      # back ramp ends / level path ends / kerb back / road edge
LIP, FALL = 0.013, 0.02
walk_top = gz + 0.004
lip_top = st_top + LIP
FLARE = round((walk_top - lip_top) / 0.10 + 0.05, 2)   # the wing's length: the kerb's drop at 1 in 10, plus a margin
beyond = [((-150, -150, gz - 0.2), (150, slo.y - 11.2, gz)), ((-150, slo.y, gz - 0.2), (150, 150, gz))]
if apron: beyond += [((-150, slo.y - 2.0, gz - 0.2), (apron[0] - FLARE, slo.y, gz)), ((apron[1] + FLARE, slo.y - 2.0, gz - 0.2), (150, slo.y, gz))]
else: beyond += [((-150, slo.y - 2.0, gz - 0.2), (150, slo.y, gz))]
boxes_obj("Ground_Beyond", beyond, noise_mat("Neighbour_Lawn", (0.04, 0.08, 0.025), 1.0, vary=0.5, scale=0.3), ground)
# Sam (2026-10-27): "the sidewalk looks to be made of pavers - they should be the same concrete material like the walkway
# coming and meeting it. the curbs should also be concrete. also make sure there is proper dividers in the concrete".
# They already shared the walkway's material (Paving_LightGrey), but the model's parts are in millimetres (object scale
# 0.001) and these were in metres, so its texture came out 1000 x coarser and read as pavers. Sidewalk, kerbs and apron
# are now built in millimetres like the model, so the same material looks the same. The concrete is cut into flags by
# tooled joints: across the sidewalk every 2.0 m (spacing about equal to the walk's 2.0 m width, the usual rule for
# sidewalks), across the kerbs at the same places, and along the back of each kerb. A joint is a 15 mm gap over a dark
# joint bed sunk 3 mm below the concrete's top.
J, PITCH = 0.015, 2.0
def flags(x0, x1, y0, y1, z0, z1):
    cuts = [x0] + [k * PITCH for k in range(math.floor(x0 / PITCH) + 1, math.ceil(x1 / PITCH)) if x0 + J < k * PITCH < x1 - J] + [x1]
    return [((cuts[i] + (J / 2 if i else 0), y0, z0), (cuts[i + 1] - (J / 2 if i + 1 < len(cuts) - 1 else 0), y1, z1)) for i in range(len(cuts) - 1)]
walks = [(-150, 150, slo.y - 13.2, slo.y - 11.2 - J)]                      # far side: house side of it is its kerb
kerb_runs = [(-150, 150, slo.y - 11.2, slo.y - 11.0)]
if apron:
    ax0, ax1, az = apron
    wx0, wx1 = ax0 - FLARE, ax1 + FLARE
    walks += [(-150, wx0, slo.y - 2.0 + J, slo.y), (wx1, 150, slo.y - 2.0 + J, slo.y)]
    kerb_runs += [(-150, wx0, slo.y - 2.2, slo.y - 2.0), (wx1, 150, slo.y - 2.2, slo.y - 2.0)]
    # the crossing's top: the driveway's profile across its width, blending to the plain walk/kerb top over each wing
    # Sam (2026-10-27): "Yes, add joints" (so the slopes show): tooled joints, like the sidewalk's, where the wings meet
    # the plain sidewalk and the ramp, along the back of the dropped kerb's wings (continuing the kerb's joint), and
    # across the driveway at both edges of the level path. Each is a 15 mm band of the joints' dark material in the
    # crossing's own surface (flush: a groove would need its own walls; at drone distance it is about one pixel).
    path_lo = walk_top - FALL * (D_PATH - D_BACK)
    P = [(0.0, az), (D_BACK, walk_top), (D_PATH, path_lo), (D_ROAD, lip_top)]
    def prof(d):
        for (d0, z0), (d1, z1) in zip(P, P[1:]):
            if d <= d1: return z0 + (z1 - z0) * (d - d0) / (d1 - d0)
    ds = sorted({0.0, D_BACK - J / 2, D_BACK + J / 2, D_PATH - J / 2, D_PATH + J / 2, D_KERB - J, D_KERB, D_ROAD})
    WS = 6   # wing columns (so the wing's surface follows the blend closely)
    xs = sorted({wx0 + FLARE * i / WS for i in range(WS + 1)} | {ax1 + FLARE * i / WS for i in range(WS + 1)}
                | {wx0 + J, ax0 - J / 2, ax0 + J / 2, ax1 - J / 2, ax1 + J / 2, wx1 - J})
    def ztop(x, d):
        t = 1.0 if ax0 <= x <= ax1 else (x - wx0) / FLARE if x < ax0 else (wx1 - x) / FLARE
        return walk_top + (prof(d) - walk_top) * t
    def joint(x, d):   # a cell's centre in a joint band?
        on_x = x < wx0 + J or x > wx1 - J or abs(x - ax0) < J / 2 or abs(x - ax1) < J / 2
        if ax0 < x < ax1: return on_x or abs(d - D_BACK) < J / 2 or abs(d - D_PATH) < J / 2
        return on_x or D_KERB - J < d < D_KERB
    zb = gz - 0.15                                      # flat underside, at the kerbs' foot
    bm = bmesh.new(); top, bot = {}, {}
    for i, x in enumerate(xs):
        for j, d in enumerate(ds):
            top[i, j] = bm.verts.new(Vector((x, slo.y - d, ztop(x, d))) * 1000)
            bot[i, j] = bm.verts.new(Vector((x, slo.y - d, zb)) * 1000)
    CONC, BLOCK, JOINT = 0, 1, 2                         # all but the back ramp is the sidewalk's concrete
    for i in range(len(xs) - 1):
        for j in range(len(ds) - 1):
            cx, cd = (xs[i] + xs[i + 1]) / 2, (ds[j] + ds[j + 1]) / 2
            f = bm.faces.new((top[i, j], top[i + 1, j], top[i + 1, j + 1], top[i, j + 1]))
            f.material_index = JOINT if joint(cx, cd) else BLOCK if ax0 <= cx <= ax1 and cd < D_BACK else CONC
            bm.faces.new((bot[i, j + 1], bot[i + 1, j + 1], bot[i + 1, j], bot[i, j]))
    ni, nj = len(xs) - 1, len(ds) - 1
    rim = [(i, 0) for i in range(ni)] + [(ni, j) for j in range(nj)] + [(i, nj) for i in range(ni, 0, -1)] + [(0, j) for j in range(nj, 0, -1)]
    for k, a_ in enumerate(rim):
        b_ = rim[(k + 1) % len(rim)]
        bm.faces.new((top[a_], bot[a_], bot[b_], top[b_]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])   # the wing cells are not flat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Driveway_Apron"); bm.to_mesh(me); bm.free()
    JOINT_MAT = new_mat("Joint_Dark", (0.035, 0.035, 0.035), 0.9)[0]
    me.materials.append(M["#b8b6ae"]); me.materials.append(M["#55575a"]); me.materials.append(JOINT_MAT)   # concrete; Driveway_Block; joints
    ap = bpy.data.objects.new("Driveway_Apron", me); ap.scale = (0.001,) * 3; ground.objects.link(ap)
else:
    walks += [(-150, 150, slo.y - 2.0 + J, slo.y)]
    kerb_runs += [(-150, 150, slo.y - 2.2, slo.y - 2.0)]
side = [b for x0, x1, y0, y1 in walks for b in flags(x0, x1, y0, y1, gz, gz + 0.004)]
kerbs = [b for x0, x1, y0, y1 in kerb_runs for b in flags(x0, x1, y0, y1, gz - 0.15, gz + 0.004)]
# the joint bed: under each walk and its kerb together (so the joint along the kerb shows it too), split round the apron;
# kept 10 mm inside the concrete's outer faces (a shared face flickered as dark stripes on the kerbs)
E = 0.01
beds = [((x0 + (E if x0 > -150 else 0), slo.y - 13.2 + E if y1 < slo.y - 10 else y0 + E, gz - 0.15 + E),
         (x1 - (E if x1 < 150 else 0), slo.y - 11.0 - E if y1 < slo.y - 10 else slo.y - E, gz + 0.001))
        for x0, x1, y0, y1 in kerb_runs]
boxes_obj("Sidewalk", side, M["#b8b6ae"], ground, mm=True)
boxes_obj("Kerb", kerbs, M["#b8b6ae"], ground, mm=True)
boxes_obj("Concrete_Joints", beds, JOINT_MAT if apron else new_mat("Joint_Dark", (0.035, 0.035, 0.035), 0.9)[0], ground, mm=True)
boxes_obj("Street", [((-150, slo.y - 11.0, gz - 0.15), (150, slo.y - 2.2, st_top))], ASPHALT, ground)

w = sc.world or bpy.data.worlds.new("World"); sc.world = w; w.use_nodes = True
wn = w.node_tree.nodes; wl = w.node_tree.links
bg = wn["Background"]; tc = wn.new("ShaderNodeTexCoord"); sep = wn.new("ShaderNodeSeparateXYZ")
wl.new(tc.outputs["Generated"], sep.inputs[0])
cr = wn.new("ShaderNodeValToRGB"); e = cr.color_ramp.elements
e[0].position, e[0].color = 0.0, (0.66, 0.70, 0.78, 1)   # pale dusk horizon
e[1].position, e[1].color = 0.5, (0.22, 0.32, 0.52, 1)   # blue above
wl.new(sep.outputs["Z"], cr.inputs["Fac"]); bg.inputs["Strength"].default_value = 0.8
# soft clouds: stretched noise, only above the horizon, lightening the sky a little
cn = wn.new("ShaderNodeTexNoise"); cn.inputs["Scale"].default_value = 2.5; cn.inputs["Detail"].default_value = 6
mp = wn.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 1.0, 4.0); wl.new(tc.outputs["Generated"], mp.inputs["Vector"])
wl.new(mp.outputs["Vector"], cn.inputs["Vector"])
cc = wn.new("ShaderNodeValToRGB"); ce = cc.color_ramp.elements
ce[0].position, ce[0].color = 0.55, (0, 0, 0, 1); ce[1].position, ce[1].color = 0.75, (1, 1, 1, 1)
wl.new(cn.outputs["Fac"], cc.inputs["Fac"])
hz = wn.new("ShaderNodeMath"); hz.operation = "MULTIPLY"; hz.use_clamp = True
wl.new(sep.outputs["Z"], hz.inputs[0]); hz.inputs[1].default_value = 6.0
amt = wn.new("ShaderNodeMath"); amt.operation = "MULTIPLY"
wl.new(cc.outputs["Color"], amt.inputs[0]); wl.new(hz.outputs[0], amt.inputs[1])
mixc = wn.new("ShaderNodeMixRGB"); mixc.blend_type = "MIX"
wl.new(amt.outputs[0], mixc.inputs["Fac"]); wl.new(cr.outputs["Color"], mixc.inputs["Color1"])
mixc.inputs["Color2"].default_value = (0.62, 0.66, 0.74, 1)
wl.new(mixc.outputs["Color"], bg.inputs["Color"])
sun_d = bpy.data.lights.new("Dusk_Sun", "SUN"); sun_d.energy = 0.4; sun_d.color = (0.7, 0.8, 1.0); sun_d.angle = 0.3
sun = bpy.data.objects.new("Dusk_Sun", sun_d); sun.rotation_euler = (1.2, 0, -2.4); lights.objects.link(sun)

# ---------- VEGETATION: seeded, code-built foliage in the model's own tree / shrub volumes ----------
# The model's crowns and shrubs are simple blocks (they mark where the plants are); they stay in the file but are
# hidden from the render, and a lumpy cluster of spheres (or grass blades) fills the same volume. Same seed, same plants.
import random
from mathutils import Matrix

def leaf_mat(name, colours, scale=1.5):
    m, nt = new_mat(name, colours[0], 0.75)
    tc = nt.new("ShaderNodeTexCoord"); nz = nt.new("ShaderNodeTexNoise", Scale=scale, Detail=4.0)
    nt.set(nz.inputs["Vector"], tc.outputs["Object"])
    cr = nt.new("ShaderNodeValToRGB"); e = cr.color_ramp.elements
    e[0].position, e[0].color = 0.35, (*colours[0], 1); e[1].position, e[1].color = 0.65, (*colours[-1], 1)
    if len(colours) == 3: mid = e.new(0.5); mid.color = (*colours[1], 1)
    nt.set(cr.inputs["Fac"], nz.outputs["Fac"]); nt.set(nt.p.inputs["Base Color"], cr.outputs["Color"])
    bz = nt.new("ShaderNodeTexNoise", Scale=60.0, Detail=2.0); nt.set(bz.inputs["Vector"], tc.outputs["Object"])
    b = nt.new("ShaderNodeBump", Strength=0.8, Distance=0.05); nt.set(b.inputs["Height"], bz.outputs["Fac"])
    nt.set(nt.p.inputs["Normal"], b.outputs["Normal"])
    return m

GREEN = leaf_mat("Leaves_Green", [(0.02, 0.06, 0.015), (0.05, 0.12, 0.03), (0.09, 0.16, 0.04)])
AUTUMN = leaf_mat("Leaves_Autumn", [(0.25, 0.08, 0.01), (0.45, 0.22, 0.02), (0.35, 0.33, 0.05)])
DARKTREE = leaf_mat("Leaves_Background", [(0.02, 0.03, 0.015), (0.06, 0.05, 0.02), (0.04, 0.07, 0.02)], 0.5)
GRASS = leaf_mat("Grass_Blades", [(0.08, 0.10, 0.03), (0.20, 0.20, 0.07)], 8.0)
BARK = M["#5a4632"]

def blob_cluster(name, centre, half, n, rmin, rmax, mat, col, seed, subdiv=2):
    rng = random.Random(seed); bm = bmesh.new()
    for _ in range(n):
        while True:
            d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
            if d.length <= 1: break
        r = rng.uniform(rmin, rmax)
        p = Vector((centre[i] + d[i] * max(half[i] - r * 0.6, 0.05) for i in range(3)))
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r, matrix=Matrix.Translation(p))
    for v in bm.verts:   # break up the perfect spheres
        v.co += Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.04 * rmax
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); col.objects.link(ob); return ob

def grass_clump(name, lo, hi, n, mat, col, seed):
    rng = random.Random(seed); bm = bmesh.new(); c = (lo + hi) / 2; rx, ry = (hi.x - lo.x) / 2, (hi.y - lo.y) / 2
    h = hi.z - lo.z
    for _ in range(n):
        a, rr = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random())
        x, y = c.x + math.cos(a) * rr * rx * 0.8, c.y + math.sin(a) * rr * ry * 0.8
        L = h * rng.uniform(0.6, 1.3)
        tilt = Matrix.Rotation(rng.uniform(0, 0.5) * rr, 4, Vector((-math.sin(a), math.cos(a), 0)))
        mtx = Matrix.Translation((x, y, lo.z + L / 2)) @ tilt
        bmesh.ops.create_cone(bm, segments=3, radius1=0.012, radius2=0.0, depth=L, matrix=mtx, cap_ends=False)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); col.objects.link(ob); return ob

veg = coll("Dressing_Vegetation"); n_veg = 0
for o in model:
    nm = o.name
    if not (nm.endswith("_Crown") or nm.startswith("Shrub_")): continue
    lo, hi = bbox(o); c, half = (lo + hi) / 2, (hi - lo) / 2
    o.hide_render = True; n_veg += 1
    seed = sum(map(ord, nm))
    if nm.endswith("_Crown"):
        mat = GREEN if nm.startswith(("Tree_T1", "Tree_T2")) else AUTUMN   # entry trees green, the others autumn
        k = max(1.0, half.x * half.y * half.z)
        blob_cluster("Foliage_" + nm, c, half * 1.05, int(30 * k ** 0.5) + 20, 0.35, 0.7, mat, veg, seed)
    elif nm.startswith("Shrub_GR"):
        grass_clump("Grass_" + nm, lo, hi, 220, GRASS, veg, seed)
    else:
        blob_cluster("Foliage_" + nm, c, half, 14, min(half.x, half.y) * 0.35, min(half.x, half.y) * 0.65, GREEN, veg, seed)

# background tree line (no data: pure scenery, seeded), behind and beside the plot like the photos
rng = random.Random(7); n_bg = 0
spots = [(rng.uniform(-30, 45), rng.uniform(32, 55)) for _ in range(18)] + \
        [(rng.uniform(-28, -14), rng.uniform(-6, 30)) for _ in range(6)] + [(rng.uniform(36, 50), rng.uniform(-6, 30)) for _ in range(6)]
for i, (x, y) in enumerate(spots):
    H = rng.uniform(9, 15); R = rng.uniform(3, 5.5); n_bg += 1
    boxes_obj(f"BG_Trunk_{i}", [((x - 0.2, y - 0.2, gz), (x + 0.2, y + 0.2, gz + H * 0.5))], BARK, veg)
    blob_cluster(f"BG_Tree_{i}", (x, y, gz + H - R), Vector((R, R, R * 1.1)), 70, 0.6, 1.2,
                 AUTUMN if rng.random() < 0.4 else DARKTREE, veg, 100 + i, subdiv=2)

# ---------- CAMERAS (matched to the photos by eye, then refined on stills) ----------
cams = coll("Dressing_Cameras")
def add_cam(name, loc, target, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 600
    ob = bpy.data.objects.new(name, cd); ob.location = loc; cams.objects.link(ob)
    t = bpy.data.objects.new(name + "_Target", None); t.location = target; cams.objects.link(t)
    c = ob.constraints.new("TRACK_TO"); c.target = t; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
    return ob
sc.camera = add_cam("Cam_Front", (10.0, -17.0, 1.5), (10.0, 0.0, 3.8), 22)   # from the street, like front.jpg
add_cam("Cam_Garden", (-2.0, 24.0, 1.3), (8.0, 10.0, 3.0), 22)                 # garden side, like side.jpg
# interiors (rooms from design.json, eye height 1.5-1.6 m above each floor): the model as it is, no furniture yet
add_cam("Cam_Living", (6.0, 5.4, 1.5), (2.0, 9.6, 1.2), 16)          # living room, SE corner -> garden doors + west glass
add_cam("Cam_Stair", (6.0, 0.8, 1.6), (4.6, 4.6, 2.8), 16)           # entrance hall by the front door -> main stair
add_cam("Cam_Bedroom", (9.7, 4.5, 4.7), (12.0, 0.5, 4.3), 16)        # main bedroom (first floor) -> street window W13
add_cam("Cam_Flex", (3.0, 2.3, 4.6), (1.9, -1.9, 3.9), 18)           # flex room (first floor) -> sliding door D24 + street balcony
# for the add-on (rendered for v4 AND v5: the same views before and after)
add_cam("Cam_Tower", (31.0, 21.0, 1.6), (16.0, 6.5, 5.0), 22)        # garden, north-east: the east side where the tower goes
add_cam("Cam_Aerial", (-16.0, -24.0, 24.0), (10.0, 4.0, 4.0), 28)    # high from the street, south-west: the roofs
# the way into the stair + lift section from each floor (v5): utility -> back door D04 -> lobby; landing -> W21 door;
# east top room -> walkway -> tower
add_cam("Cam_EntryGF", (11.6, 3.0, 1.6), (15.2, 5.4, 1.2), 18)       # ground floor: from the utility through D04 (staged open)
add_cam("Cam_EntryFF", (9.0, 5.56, 4.75), (15.5, 5.6, 4.5), 20)      # first floor: along the landing to the W21 glass door
add_cam("Cam_EntryRoof", (9.6, 6.6, 8.5), (16.0, 5.5, 8.0), 18)      # roof level: from the east top room to the walkway
# the back garden (v6): standing on the lower lawn, looking up the steps to the terrace and the house
add_cam("Cam_Backyard", (6.5, 25.5, 1.0), (5.0, 14.0, 0.6), 24)    # back on the steps' axis, looking level (v2 framing)
# the street (Stage 6): low drone, 9 m up from the south-west, the framing Sam chose for the drone opening
add_cam("Cam_Street", (-9.0, -26.0, 9.0), (13.0, 8.0, 4.0), 26)

# ---------- RENDER SETTINGS (EEVEE, nothing rendered here) ----------
sc.render.engine = "BLENDER_EEVEE"
ee = sc.eevee
for k, v in (("taa_render_samples", 32), ("use_raytracing", True), ("ray_tracing_method", "SCREEN"),
             ("use_shadows", True), ("use_fast_gi", True), ("fast_gi_method", "GLOBAL_ILLUMINATION"),
             ("shadow_pool_size", "1024")):
    try: setattr(ee, k, v)
    except (AttributeError, TypeError): pass
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Punchy"; sc.view_settings.exposure = 0.4

bpy.ops.wm.save_as_mainfile(filepath=out_blend)
res = {"pass": 2, "model": MODEL, "addition": bool(ADDN), "garden": bool(GARDN), "soffit_look": SOFFIT_LOOK, "footprints_m": FOOT, "balustrade_panes": n_bal,
       "doors_staged_open": {k: v for k, v in OPEN_DOORS.items()} if n_open else {}, "unassigned": unassigned, "frames": n_frames, "downlights": n_down,
       "riser_lights": n_riser, "room_lights": n_rooms, "room_lights_fitted": fitted, "led_dots": len(dots), "plants_replaced": n_veg,
       "background_trees": n_bg, "raytracing": getattr(ee, "use_raytracing", None),
       "shadow_pool": getattr(ee, "shadow_pool_size", None)}
json.dump(res, open(out_json, "w"), indent=2); print(json.dumps(res))
