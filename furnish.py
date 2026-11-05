# Furnish a dressed model from a furnishing.json (a Claude design run): every item is built in code from its box
# (x, y, z_base, height, "faces", material words, colour), so the same data gives the same furniture every time. The
# house model and its dressing are not changed, except: the generic ceiling dots inside the furnished rooms are removed
# (the data's own downlights replace them) and those rooms' soft fill light is turned down. Everything added lives in
# the "Furnishing" collections.
# STAGING, not data: curtains are shown drawn back to the ends of their track (the data gives the closed box); lamps
# given only as light points get a code-built body (base, stem, shade) at that point.
# Run: blender -b <dressed.blend> --factory-startup -P furnish.py -- <project> <out.blend> <out.json> [before] <furnishing.json> [...]
#   one or more furnishing files (each next to its own rooms_*.json); "before" = add only the furnishing cameras (the
#   same views, unfurnished)
import bpy, bmesh, sys, json, os, math, random, re
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
proj, out_blend, out_json = [os.path.abspath(a) for a in args[:3]]   # plain names / . work too
BEFORE = "before" in args[3:]
FILES = [a for a in args[3:] if a != "before"]
def load(fjson):
    # one folder: furnishing_<rooms>.json goes with rooms_<rooms>.json
    d, suf = os.path.dirname(os.path.abspath(fjson)), os.path.basename(fjson)[len("furnishing_"):]
    return json.load(open(fjson)), json.load(open(os.path.join(d, "rooms_" + suf)))
F, R = load(FILES[0])   # the file being built (furnish_one sets these for each file in turn)
sc = bpy.context.scene
mm = lambda v: v / 1000.0

def coll(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in sc.collection.children: sc.collection.children.link(c)
    return c

# ---------- cameras (both modes, so before and after share them) ----------
cams = coll("Furnishing_Cameras")
def add_cam(name, loc, target, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 600
    ob = bpy.data.objects.new(name, cd); ob.location = loc; cams.objects.link(ob)
    t = bpy.data.objects.new(name + "_Target", None); t.location = target; cams.objects.link(t)
    c = ob.constraints.new("TRACK_TO"); c.target = t; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
add_cam("Cam_Furn_Living", (5.8, 9.3, 1.5), (2.0, 5.9, 0.9), 16)    # living, NE by the garden doors -> the sofa group, media wall, W07 (v1 from the NW had the floor lamp in the face)
add_cam("Cam_Furn_Dining", (10.6, 8.9, 1.6), (6.4, 6.9, 1.0), 16)    # from the kitchen -> the table, the sideboard, the living beyond
add_cam("Cam_Furn_Garden", (8.6, 5.6, 1.5), (5.0, 9.6, 1.1), 16)     # from the sideboard -> the table, the sliders, the terrace
add_cam("Cam_Furn_Kitchen", (9.4, 6.0, 1.6), (12.8, 9.0, 1.0), 16)    # from the dining passage -> the island, the sink run under W05, the shelves
add_cam("Cam_Furn_Kitchen2", (10.0, 8.7, 1.6), (13.2, 6.6, 1.1), 16)  # in the aisle at the sink run's west end -> the island, the tall bank, the east run (v1 stood inside the worktop)
add_cam("Cam_Furn_Ensuite", (8.95, 1.35, 4.75), (5.4, 1.5, 4.2), 14)   # from the door D21 -> the vanity, the WC, the walk-in shower

def in_poly(p, poly):
    c = False; j = len(poly) - 1
    for i in range(len(poly)):
        (xi, yi), (xj, yj) = poly[i], poly[j]
        if (yi > p[1]) != (yj > p[1]) and p[0] < (xj - xi) * (p[1] - yi) / (yj - yi) + xi: c = not c
        j = i
    return c
in_rooms = lambda x, y: any(in_poly((x * 1000, y * 1000), r["outline"]) for r in R["rooms"])

res = {"mode": "before" if BEFORE else "furnished", "sources": [os.path.relpath(f, proj) for f in FILES]}
if BEFORE:
    bpy.ops.wm.save_as_mainfile(filepath=out_blend); json.dump(res, open(out_json, "w"), indent=2); print(json.dumps(res)); sys.exit(0)

# ---------- materials from the data's words and colour ----------
def lin(h):   # "#rrggbb" (sRGB) -> linear RGB
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)
MATS = {}
def mat(words, hexc):
    key = (words, hexc)
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new("F_" + words.lower().split(",")[0][:24] + "_" + hexc[1:]); m.use_nodes = True
    w = words.lower().split(",")[0]   # the first clause names the main material ("oak frame, clay leather seat" = oak)
    nt = m.node_tree; p = nt.nodes["Principled BSDF"]; base = lin(hexc)
    rough, bump, scale, vary = 0.8, 0.0, 30.0, 0.08
    if any(k in w for k in ("oak", "veneer", "wood")): rough, bump, scale, vary = 0.5, 0.05, 3.0, 0.25
    if "leather" in w: rough, bump, scale, vary = 0.42, 0.03, 60.0, 0.12
    if any(k in w for k in ("wool", "linen", "boucl", "rug")): rough, bump, scale, vary = 0.97, 0.15, 220.0, 0.10
    if any(k in w for k in ("travertine", "stone", "stoneware", "clay")): rough, bump, scale, vary = 0.6, 0.08, 18.0, 0.18
    if "canvas" in w: rough, bump, scale, vary = 0.9, 0.02, 2.5, 0.6
    # kitchen and bathroom words (2026-10-26); later lines win
    if "lacquer" in w: rough, bump, scale, vary = 0.45, 0.0, 30.0, 0.03
    if any(k in w for k in ("ceramic", "porcelain", "fireclay", "zellige")): rough, bump, scale, vary = (0.55 if "matt" in w else 0.15), 0.01, 40.0, 0.05
    if any(k in w for k in ("bronze", "steel", "brass", "chrome", "metal")):
        p.inputs["Metallic"].default_value = 1.0; rough, bump, scale, vary = (0.35 if "brushed" in w else 0.2), 0.0, 30.0, 0.04
    if "black glass" in w or "smoked glass" in w: rough, bump, scale, vary = 0.08, 0.0, 30.0, 0.0
    elif "glass" in w:   # clear glass (shower screen): a thin blended reflective layer, as the house's own glass
        base, rough, vary = (0.0, 0.0, 0.0), 0.02, 0.0                # (transmission rendered as an opaque pale panel in EEVEE)
        p.inputs["Alpha"].default_value = 0.12; p.inputs["Specular IOR Level"].default_value = 0.8; m.surface_render_method = "BLENDED"
    if "mirror" in w:
        p.inputs["Metallic"].default_value = 1.0; base = (0.9, 0.9, 0.9); rough, vary = 0.02, 0.0
    p.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    if "oak" in w or "veneer" in w:   # long grain: stretch the noise along x
        mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.08, 1.0, 1.0)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB"); e = rp.color_ramp.elements
    e[0].color = (*[c * (1 - vary) for c in base], 1); e[1].color = (*[min(1, c * (1 + vary)) for c in base], 1)
    if "canvas" in w:   # an earth-tone abstract: clay, sand, olive bands
        e[0].color = (*lin("#b5653f"), 1); e.new(0.5).color = (*lin("#d8c6a5"), 1); e[1].color = (*lin("#6f7350"), 1)
    nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"]); nt.links.new(rp.outputs["Color"], p.inputs["Base Color"])
    if bump:
        b = nt.nodes.new("ShaderNodeBump"); b.inputs["Strength"].default_value = bump; b.inputs["Distance"].default_value = 0.005
        nt.links.new(nz.outputs["Fac"], b.inputs["Height"]); nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    MATS[key] = m; return m
OAK = lambda: mat("oiled oak", "#a67c52")
BLACK = mat("black metal", "#1a1a1a")
SHADE = mat("linen shade", "#efe4cf")
SHADE.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.5   # lamp shades glow a little

furn = coll("Furnishing")
def boxes(name, bxs, m):
    bm = bmesh.new()
    for lo, hi in bxs:
        for v in bmesh.ops.create_cube(bm, size=1.0)["verts"]:
            v.co = Vector([lo[i] + (hi[i] - lo[i]) * (v.co[i] + 0.5) for i in range(3)])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(m)
    ob = bpy.data.objects.new(name, me); furn.objects.link(ob); return ob
def bevel(ob, w=0.012, seg=2):
    md = ob.modifiers.new("Bevel", "BEVEL"); md.width = w; md.segments = seg; md.limit_method = "ANGLE"
def cyl(name, c, r, z0, z1, m, verts=24):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r, depth=z1 - z0)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(m)
    ob = bpy.data.objects.new(name, me); ob.location = (c[0], c[1], (z0 + z1) / 2); furn.objects.link(ob)
    bpy.context.view_layer.update(); return ob

def back_side(it):   # the side away from where it faces: (axis, low side?) e.g. faces north -> back on the south (y low)
    f = (it.get("faces") or "none").lower()
    return {"north": (1, True), "south": (1, False), "east": (0, True), "west": (0, False)}.get(f)

def lohi(it):
    return [mm(it["x"][0]), mm(it["y"][0]), mm(it["z_base"])], [mm(it["x"][1]), mm(it["y"][1]), mm(it["z_base"] + it["height"])]

def soft(ob, w=0.035, seg=4):   # an upholstered piece: a wide rounded bevel, then a light subdivision
    bevel(ob, w, seg); sd = ob.modifiers.new("Soft", "SUBSURF"); sd.levels = sd.render_levels = 1
    for p in ob.data.polygons: p.use_smooth = True
def seat(it, m, arm=0.14, back=0.2, seat_z=0.42, legs=0.1, arms=True):
    # LOOK UPGRADE 2026-11-02 (staging, same data): v1 was five bevelled boxes. Now: a plinth on slim oak legs, one seat
    # cushion per ~0.75 m with 12 mm gaps, matching back cushions leaning back, rounded arms, and on a sofa two throw
    # pillows in a contrast colour. The item's box is unchanged: nothing reaches outside it.
    lo, hi = lohi(it); bs = back_side(it) or (1, True); ax, low = bs; ox = 1 - ax
    z0 = lo[2] + legs; zc = lo[2] + seat_z - 0.12   # plinth top = cushion bottom
    sofa = (hi[ox] - lo[ox]) > 1.3
    inner0 = lo[ox] + (arm if arms else 0.02); inner1 = hi[ox] - (arm if arms else 0.02)
    back0, back1 = (lo[ax], lo[ax] + back) if low else (hi[ax] - back, hi[ax])
    seat0, seat1 = (back1, hi[ax] - 0.02) if low else (lo[ax] + 0.02, back0)
    def bx(o0, o1, a0, a1, z_0, z_1):   # a box from along-the-seat (o) and front-back (a) ranges
        p, q = [0, 0, z_0], [0, 0, z_1]; p[ox], q[ox] = o0, o1; p[ax], q[ax] = a0, a1; return (tuple(p), tuple(q))
    pl = boxes(f"{it['id']}_plinth", [bx(lo[ox], hi[ox], lo[ax], hi[ax], z0, zc)], m); bevel(pl, 0.02, 3)
    n = max(1, round((inner1 - inner0) / 0.75)); g = 0.012; w = (inner1 - inner0 - g * (n - 1)) / n
    for i in range(n):
        o0 = inner0 + i * (w + g)
        c = boxes(f"{it['id']}_seat{i}", [bx(o0, o0 + w, seat0, seat1, zc, lo[2] + seat_z)], m); soft(c, 0.045)
        tilt_in = 0.05   # the back cushion leans: built as a box, its top pushed back by the bevel's look
        bk = boxes(f"{it['id']}_back{i}", [bx(o0, o0 + w, back0 + (0.02 if low else 0), back1 - (0 if low else 0.02) + (tilt_in if low else -tilt_in) * 0, lo[2] + seat_z, hi[2] - 0.02)], m); soft(bk, 0.06)
    frame = boxes(f"{it['id']}_back", [bx(lo[ox], hi[ox], back0 if low else back1 - 0.08, back0 + 0.08 if low else back1, zc, hi[2] - 0.12)], m); bevel(frame, 0.02, 3)
    if arms:
        for k, (o0, o1) in enumerate(((lo[ox], lo[ox] + arm), (hi[ox] - arm, hi[ox]))):
            ar = boxes(f"{it['id']}_arm{k}", [bx(o0, o1, lo[ax], hi[ax], zc, lo[2] + min(it["height"] / 1000, 0.62))], m); soft(ar, 0.05)
    if sofa:   # two throw pillows, one each end, leaning on the back cushions
        pm = mat("linen pillow", "#a8613f" if "#d" in it.get("colour", "#d").lower()[:2] else "#e3dacb")
        for k, o in enumerate((inner0 + 0.06, inner1 - 0.06 - 0.45)):
            a0 = back1 if low else back0 - 0.14
            pz = lo[2] + seat_z
            p = boxes(f"{it['id']}_pillow{k}", [bx(o, o + 0.45, a0, a0 + 0.14, pz, pz + 0.42)], pm); soft(p, 0.07, 4)
    lg = []
    for o in (lo[ox] + 0.07, hi[ox] - 0.1):
        for a_ in (lo[ax] + 0.07, hi[ax] - 0.1):
            p, q = [0, 0, lo[2]], [0, 0, z0]; p[ox], q[ox] = o, o + 0.03; p[ax], q[ax] = a_, a_ + 0.03; lg.append((tuple(p), tuple(q)))
    boxes(f"{it['id']}_legs", lg, OAK())

def table(it, m, top=0.04, leg=0.06, inset=0.08):
    lo, hi = lohi(it)
    t = boxes(f"{it['id']}_top", [((lo[0], lo[1], hi[2] - top), (hi[0], hi[1], hi[2]))], m); bevel(t, 0.006)
    lg = []
    for x in (lo[0] + inset, hi[0] - inset - leg):
        for y in (lo[1] + inset, hi[1] - inset - leg): lg.append(((x, y, lo[2]), (x + leg, y + leg, hi[2] - top)))
    boxes(f"{it['id']}_legs", lg, m)

def chair(it, m):
    lo, hi = lohi(it); ax, low = back_side(it) or (1, True)
    s = boxes(f"{it['id']}_seat", [((lo[0], lo[1], lo[2] + 0.42), (hi[0], hi[1], lo[2] + 0.47))], m); bevel(s, 0.01)
    bk = [list(lo), list(hi)]
    if low: bk[1][ax] = lo[ax] + 0.04
    else: bk[0][ax] = hi[ax] - 0.04
    bk[0][2] = lo[2] + 0.5; b = boxes(f"{it['id']}_back", [tuple(map(tuple, bk))], m); bevel(b, 0.01)
    lg = []
    for x in (lo[0] + 0.02, hi[0] - 0.05):
        for y in (lo[1] + 0.02, hi[1] - 0.05): lg.append(((x, y, lo[2]), (x + 0.03, y + 0.03, lo[2] + 0.42)))
    boxes(f"{it['id']}_legs", lg, OAK())

def cabinet(it, m):
    lo, hi = lohi(it); w = it["material"].lower(); stone = any(k in w for k in ("stone", "travertine", "quartz", "marble"))
    c = boxes(f"{it['id']}_body", [((lo[0] + 0.03, lo[1] + 0.03, lo[2]), (hi[0] - 0.03, hi[1] - 0.03, lo[2] + 0.06)),
                                    ((lo[0], lo[1], lo[2] + 0.06), (hi[0], hi[1], hi[2] - (0.02 if stone else 0)))], m); bevel(c, 0.004)
    if stone: boxes(f"{it['id']}_top", [((lo[0], lo[1], hi[2] - 0.02), (hi[0], hi[1], hi[2]))], mat("stone top", "#c9bca6"))
    thin = 0 if hi[0] - lo[0] < hi[1] - lo[1] else 1; along = 1 - thin; n = max(2, round((hi[along] - lo[along]) / 0.55))
    face = hi[thin] if it.get("faces", "").lower() in ("north", "east") else lo[thin]
    grooves = []
    for i in range(1, n):
        a = lo[along] + (hi[along] - lo[along]) * i / n; g0, g1 = [0, 0, lo[2] + 0.08], [0, 0, hi[2] - 0.04]
        g0[along], g1[along] = a - 0.002, a + 0.002; g0[thin], g1[thin] = face - 0.002, face + 0.002; grooves.append((tuple(g0), tuple(g1)))
    boxes(f"{it['id']}_joints", grooves, BLACK)

def art(it, m):
    lo, hi = lohi(it); thin = 0 if hi[0] - lo[0] < hi[1] - lo[1] else 1
    boxes(f"{it['id']}_frame", [(tuple(lo), tuple(hi))], OAK())
    c0, c1 = list(lo), list(hi); along = 1 - thin
    c0[along] += 0.03; c1[along] -= 0.03; c0[2] += 0.03; c1[2] -= 0.03
    wall_low = lo[thin] < (R["rooms"][0]["outline"][0][thin] / 1000 + 0.2) or any(abs(lo[thin] - mm(p[thin])) < 0.06 for r in R["rooms"] for p in r["outline"])
    if wall_low: c1[thin] += 0.004
    else: c0[thin] -= 0.004
    boxes(f"{it['id']}_canvas", [(tuple(c0), tuple(c1))], m)

def curtain(it, m, open_share=0.18):   # STAGING: drawn back, a folded stack at each end, + the ceiling track
    lo, hi = lohi(it); thin = 0 if hi[0] - lo[0] < hi[1] - lo[1] else 1; along = 1 - thin
    L = hi[along] - lo[along]; c = (lo[thin] + hi[thin]) / 2
    t0, t1 = [0, 0, R["ceiling_z"] / 1000 - 0.03], [0, 0, R["ceiling_z"] / 1000]
    t0[thin], t1[thin] = c - 0.015, c + 0.015; t0[along], t1[along] = lo[along], hi[along]
    boxes(f"{it['id']}_track", [(tuple(t0), tuple(t1))], BLACK)
    for k, (a0, a1) in enumerate([(lo[along], lo[along] + L * open_share), (hi[along] - L * open_share, hi[along])]):
        bm = bmesh.new(); folds = max(4, int((a1 - a0) / 0.06)); amp = (hi[thin] - lo[thin]) / 2
        rows = []
        for z in (lo[2] + 0.01, t0[2]):
            row = []
            for i in range(folds + 1):
                p = [0, 0, z]; p[along] = a0 + (a1 - a0) * i / folds; p[thin] = c + (amp if i % 2 else -amp) * 0.9
                row.append(bm.verts.new(p))
            rows.append(row)
        for i in range(folds): bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
        me = bpy.data.meshes.new(f"{it['id']}_stack{k}"); bm.to_mesh(me); bm.free(); me.materials.append(m)
        ob = bpy.data.objects.new(me.name, me); furn.objects.link(ob)
        ob.modifiers.new("Solid", "SOLIDIFY").thickness = 0.006
        sm = ob.modifiers.new("Smooth", "SUBSURF"); sm.levels = sm.render_levels = 2

def rug(it, m):
    lo, hi = lohi(it); r = boxes(f"{it['id']}", [(tuple(lo), tuple(hi))], m); bevel(r, 0.004, 1)
    if "border" in it.get("material", ""):   # "with clay border": a 120 mm band
        b = 0.12; bx = [((lo[0], lo[1], hi[2]), (hi[0], lo[1] + b, hi[2] + 0.001)), ((lo[0], hi[1] - b, hi[2]), (hi[0], hi[1], hi[2] + 0.001)),
                        ((lo[0], lo[1], hi[2]), (lo[0] + b, hi[1], hi[2] + 0.001)), ((hi[0] - b, lo[1], hi[2]), (hi[0], hi[1], hi[2] + 0.001))]
        boxes(f"{it['id']}_border", bx, mat("wool clay border", "#a8613f"))

def coffee(it, m):
    lo, hi = lohi(it)
    t = boxes(f"{it['id']}_top", [((lo[0], lo[1], hi[2] - 0.04), (hi[0], hi[1], hi[2]))], m); bevel(t, 0.008)
    b = boxes(f"{it['id']}_base", [((lo[0] + 0.12, lo[1] + 0.1, lo[2]), (hi[0] - 0.12, hi[1] - 0.1, hi[2] - 0.04))], OAK()); bevel(b, 0.005)

# ---------- kitchen and bathroom pieces (2026-10-26) ----------
def slab(it, m, b=0.003):
    lo, hi = lohi(it); o = boxes(it["id"], [(tuple(lo), tuple(hi))], m); bevel(o, b, 1); return o
def front_axis(it):   # (axis, +1/-1) of the face a person uses, from "faces"
    return {"north": (1, 1), "south": (1, -1), "east": (0, 1), "west": (0, -1)}.get((it.get("faces") or "").lower())
def sink(it, m):   # LOOK UPGRADE 2026-11-02: an undermount basin you can see into (v1: a dark plane on the top)
    lo, hi = lohi(it); r = 0.03
    if hi[2] - lo[2] > 0.05:   # sit-on basin: a ceramic block with a shallow well
        o = boxes(it["id"], [(tuple(lo), tuple(hi))], m); bevel(o, 0.02, 3)
        boxes(it["id"] + "_well", [((lo[0] + r, lo[1] + r, hi[2] - 0.004), (hi[0] - r, hi[1] - r, hi[2] + 0.0005))], mat("basin well", "#6d625a"))
        return
    # undermount: cut the opening (rounded corners) through whatever stands under it (worktop, cabinet top), then a
    # fireclay bowl 200 mm deep with a drain and a thin steel rim at the top edge
    top = lo[2] - 0.0 ; depth = 0.2
    cut = boxes(it["id"] + "_cutter", [((lo[0], lo[1], top - depth - 0.02), (hi[0], hi[1], top + 0.05))], m); bevel(cut, 0.04, 4)
    cut.hide_render = True; cut.hide_viewport = True; cut.display_type = "WIRE"
    bpy.context.view_layer.update()
    for ob in list(furn.objects):
        if ob is cut or ob.type != "MESH" or ob.name.startswith(it["id"]): continue
        mn = [min((ob.matrix_world @ Vector(c))[i] for c in ob.bound_box) for i in range(3)]
        mx = [max((ob.matrix_world @ Vector(c))[i] for c in ob.bound_box) for i in range(3)]
        if mn[0] < hi[0] and mx[0] > lo[0] and mn[1] < hi[1] and mx[1] > lo[1] and mn[2] < top and mx[2] > top - depth:
            bo = ob.modifiers.new("SinkCut", "BOOLEAN"); bo.operation = "DIFFERENCE"; bo.object = cut; bo.solver = "EXACT"
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector([lo[0] + (hi[0] - lo[0]) * (v.co[0] + 0.5), lo[1] + (hi[1] - lo[1]) * (v.co[1] + 0.5), top - depth + depth * (v.co[2] + 0.5)])
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.9], context="FACES")   # open at the top
    for f in bm.faces: f.normal_flip()   # we look at the inside
    me = bpy.data.meshes.new(it["id"] + "_bowl"); bm.to_mesh(me); bm.free(); me.materials.append(m)
    bowl = bpy.data.objects.new(me.name, me); furn.objects.link(bowl); bevel(bowl, 0.035, 4)
    sd = bowl.modifiers.new("Solid", "SOLIDIFY"); sd.thickness = 0.012
    cyl(it["id"] + "_drain", ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2), 0.045, top - depth + 0.001, top - depth + 0.004, mat("brushed steel drain", "#9a958e"), 32)
def faucet(it, m):   # LOOK UPGRADE 2026-11-02: a round column rising into an arched gooseneck spout towards the user
    lo, hi = lohi(it); cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2; fa = front_axis(it) or (1, -1)
    reach = 0.22; h = hi[2] - lo[2]
    cyl(it["id"] + "_base", (cx, cy), 0.026, lo[2], lo[2] + 0.02, m, 32)
    cd = bpy.data.curves.new(it["id"] + "_neck", "CURVE"); cd.dimensions = "3D"; cd.bevel_depth = 0.013; cd.bevel_resolution = 6
    sp = cd.splines.new("BEZIER"); sp.bezier_points.add(2)
    def at(along, z):   # a point "along" metres towards the user from the column, at height z
        p = [cx, cy, z]; p[fa[0]] += fa[1] * along; return Vector(p)
    pts = [(at(0, lo[2] + 0.02), at(0, lo[2] - 0.05), at(0, lo[2] + 0.12)),
           (at(reach * 0.45, hi[2]), at(0.0, hi[2]), at(reach * 0.9, hi[2])),
           (at(reach, hi[2] - 0.12), at(reach, hi[2] - 0.02), at(reach, hi[2] - 0.2))]
    for bp, (co, l_, r_) in zip(sp.bezier_points, pts):
        bp.co = co; bp.handle_left_type = bp.handle_right_type = "FREE"; bp.handle_left = l_; bp.handle_right = r_
    ob = bpy.data.objects.new(cd.name, cd); cd.materials.append(m); furn.objects.link(ob)
    lever = [cx - 0.008, cy - 0.008, lo[2] + h * 0.55]; lv1 = [cx + 0.008, cy + 0.008, lo[2] + h * 0.55 + 0.012]
    lever[1 - fa[0]] += 0.02; lv1[1 - fa[0]] += 0.11
    boxes(it["id"] + "_lever", [(tuple(lever), tuple(lv1))], m)
def hob(it, m):
    lo, hi = lohi(it); boxes(it["id"], [((lo[0], lo[1], lo[2]), (hi[0], hi[1], lo[2] + 0.004))], m)
    zones = []
    for fx in (0.28, 0.72):
        for fy in (0.3, 0.7):
            x = lo[0] + (hi[0] - lo[0]) * fx; y = lo[1] + (hi[1] - lo[1]) * fy
            zones.append(((x - 0.09, y - 0.09, lo[2] + 0.004), (x + 0.09, y + 0.09, lo[2] + 0.0045)))
    boxes(it["id"] + "_zones", zones, mat("hob marks", "#3d3b3a"))
def appliance_front(it, m):   # oven / microwave: glass front on the user side, a bar handle
    lo, hi = lohi(it); boxes(it["id"] + "_body", [(tuple(lo), tuple(hi))], m)
    fa = front_axis(it)
    if fa:
        ax, s = fa; oth = 1 - ax; f = hi[ax] if s > 0 else lo[ax]
        h0, h1 = [0, 0, hi[2] - 0.08], [0, 0, hi[2] - 0.06]; h0[oth], h1[oth] = lo[oth] + 0.08, hi[oth] - 0.08
        h0[ax], h1[ax] = (f, f + 0.03) if s > 0 else (f - 0.03, f)
        boxes(it["id"] + "_handle", [(tuple(h0), tuple(h1))], mat("brushed steel handle", "#9a9690"))
def extractor(it, m):
    lo, hi = lohi(it); boxes(it["id"], [(tuple(lo), tuple(hi))], m)
def shelf(it, m):   # open shelves: a 40 mm board at the bottom and every ~400 mm up the box
    lo, hi = lohi(it); n = max(1, round((hi[2] - lo[2]) / 0.4)); bx = []
    for i in range(n):
        z = lo[2] + (hi[2] - lo[2] - 0.04) * (i / max(1, n - 1) if n > 1 else 0); bx.append(((lo[0], lo[1], z), (hi[0], hi[1], z + 0.04)))
    o = boxes(it["id"], bx, m); bevel(o, 0.003, 1)
def stool(it, m):
    lo, hi = lohi(it); s = boxes(it["id"] + "_seat", [((lo[0] + 0.02, lo[1] + 0.02, hi[2] - 0.05), (hi[0] - 0.02, hi[1] - 0.02, hi[2]))], m); bevel(s, 0.015, 2)
    lg = []
    for x in (lo[0] + 0.04, hi[0] - 0.07):
        for y in (lo[1] + 0.04, hi[1] - 0.07): lg.append(((x, y, lo[2]), (x + 0.03, y + 0.03, hi[2] - 0.05)))
    lg.append(((lo[0] + 0.04, lo[1] + 0.04, lo[2] + 0.25), (hi[0] - 0.04, lo[1] + 0.07, lo[2] + 0.27)))   # footrest
    boxes(it["id"] + "_legs", lg, OAK())
def wc(it, m):   # wall-hung: a rounded bowl in the top 340 mm of the box, nothing under it
    lo, hi = lohi(it); b = boxes(it["id"], [((lo[0], lo[1], max(lo[2], hi[2] - 0.34)), tuple(hi))], m); bevel(b, 0.06, 4)
    boxes(it["id"] + "_seat", [((lo[0] + 0.01, lo[1] + 0.01, hi[2]), (hi[0] - 0.01, hi[1] - 0.01, hi[2] + 0.02))], m)
def mirror_cabinet(it, m):
    lo, hi = lohi(it); boxes(it["id"] + "_body", [(tuple(lo), tuple(hi))], OAK())
    fa = front_axis(it) or (1, -1); ax, s = fa; f0, f1 = list(lo), list(hi)
    if s > 0: f0[ax] = hi[ax]; f1[ax] = hi[ax] + 0.004
    else: f0[ax] = lo[ax] - 0.004; f1[ax] = lo[ax]
    boxes(it["id"] + "_mirror", [(tuple(f0), tuple(f1))], mat("mirror", "#d0d0d0"))
def towel_rail(it, m):
    lo, hi = lohi(it); thin = 0 if hi[0] - lo[0] < hi[1] - lo[1] else 1; along = 1 - thin; c = (lo[thin] + hi[thin]) / 2; bx = []
    for a in (lo[along] + 0.015, hi[along] - 0.035):
        p0, p1 = [0, 0, lo[2]], [0, 0, hi[2]]; p0[along], p1[along] = a, a + 0.02; p0[thin], p1[thin] = c - 0.01, c + 0.01; bx.append((tuple(p0), tuple(p1)))
    for i in range(int((hi[2] - lo[2]) / 0.12)):
        z = lo[2] + 0.06 + i * 0.12; p0, p1 = [0, 0, z], [0, 0, z + 0.016]; p0[along], p1[along] = lo[along], hi[along]; p0[thin], p1[thin] = c - 0.008, c + 0.008; bx.append((tuple(p0), tuple(p1)))
    boxes(it["id"], bx, m)
def shower_tray(it, m):   # the tiled floor; if the words say so, the same tile up the room walls round it to the ceiling
    lo, hi = lohi(it); slab(it, m, 0.001)
    if "wall" in it.get("material", "").lower():
        ceil = R["ceiling_z"] / 1000; bx = []
        for r in R["rooms"]:
            xs = [mm(p[0]) for p in r["outline"]]; ys = [mm(p[1]) for p in r["outline"]]; X0, X1, Y0, Y1 = min(xs), max(xs), min(ys), max(ys)
            if abs(lo[0] - X0) < 0.01: bx.append(((X0, lo[1], hi[2]), (X0 + 0.01, hi[1], ceil)))
            if abs(hi[0] - X1) < 0.01: bx.append(((X1 - 0.01, lo[1], hi[2]), (X1, hi[1], ceil)))
            if abs(lo[1] - Y0) < 0.01: bx.append(((lo[0], Y0, hi[2]), (hi[0], Y0 + 0.01, ceil)))
            if abs(hi[1] - Y1) < 0.01: bx.append(((lo[0], Y1 - 0.01, hi[2]), (hi[0], Y1, ceil)))
        if bx: boxes(it["id"] + "_wall_tiles", bx, m)
def shower_head(it, m):
    lo, hi = lohi(it); boxes(it["id"], [((lo[0], lo[1], lo[2]), (hi[0], hi[1], lo[2] + 0.012))], m)
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2; cyl(it["id"] + "_arm", (cx, cy), 0.012, lo[2] + 0.012, R["ceiling_z"] / 1000, m, 12)
def hand_shower(it, m):
    lo, hi = lohi(it); cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    cyl(it["id"] + "_rail", (cx, cy), 0.012, lo[2], hi[2], m, 12)
    boxes(it["id"] + "_valve", [((lo[0], cy - 0.05, lo[2] - 0.1), (hi[0], cy + 0.05, lo[2]))], m)
    boxes(it["id"] + "_head", [((lo[0], cy - 0.035, hi[2] - 0.3), (hi[0], cy + 0.035, hi[2] - 0.08))], m)
def niche(it, m):   # a wall niche (lined panel) or a boxed ledge (a block with a shelf top)
    lo, hi = lohi(it)
    if "ledge" in (it.get("name", "") + it["kind"]).lower():
        o = boxes(it["id"], [(tuple(lo), (hi[0], hi[1], hi[2] - 0.03))], m); bevel(o, 0.003, 1)
        boxes(it["id"] + "_top", [((lo[0], lo[1], hi[2] - 0.03), tuple(hi))], mat("honed travertine shelf", "#d4c3a5"))
    else: slab(it, m, 0.002)

BUILD = [("mirror cabinet", mirror_cabinet), ("mirror", mirror_cabinet), ("shower tray", shower_tray), ("shower screen", slab),
         ("shower head", shower_head), ("hand shower", hand_shower), ("towel rail", towel_rail), ("niche", niche), ("wc", wc),
         ("basin", sink), ("sink", sink), ("faucet", faucet), ("tap", faucet), ("hob", hob), ("extractor", extractor),
         ("oven", appliance_front), ("microwave", appliance_front), ("worktop", slab), ("stool", stool), ("shelf", shelf),
         ("fridge", cabinet), ("dishwasher", cabinet), ("island", cabinet), ("vanity", cabinet),
         ("sofa", seat), ("armchair", lambda it, m: seat(it, m, arm=0.12, back=0.18)), ("coffee", coffee), ("rug", rug),
         ("dining chair", chair), ("chair", chair), ("table", table), ("media", cabinet), ("sideboard", cabinet), ("storage", cabinet),
         ("cabinet", cabinet), ("art", art), ("print", art), ("canvas", art), ("curtain", curtain), ("blind", curtain)]
built, fallback, lamp_bodies, dimmed, curtains = [], [], [], [], []
stats = {"dots": 0, "items": 0, "lights": 0}
def furnish_one(fjson):
    global F, R
    F, R = load(fjson); FZ = R.get("floor_z", 0) / 1000
    stats["items"] += len(F["items"]); stats["lights"] += len(F.get("lights", []))
    curtains.extend(i["id"] for i in F["items"] if "curtain" in i["kind"].lower())
    for it in F["items"]:
        m = mat(it.get("material", "plain"), it.get("colour", "#999999"))
        kind = (it["kind"] + " " + it.get("name", "")).lower()
        fn = next((f for k, f in BUILD if k in it["kind"].lower()), None) or next((f for k, f in BUILD if k in kind), None)
        if fn: fn(it, m); built.append(it["id"])
        else: lo, hi = lohi(it); boxes(it["id"], [(tuple(lo), tuple(hi))], m); fallback.append(it["id"])

    # ---------- lights from the data ----------
    lights = coll("Furnishing_Lights")
    WARM = (1.0, 0.70, 0.45)   # ~2700 K
    def light(name, kind, loc, energy, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = WARM
        for k, v in kw.items(): setattr(ld, k, v)
        ob = bpy.data.objects.new(name, ld); ob.location = loc; lights.objects.link(ob); return ob
    DOT = mat("downlight bezel", "#f2efe8")
    GLOW = bpy.data.materials.new("F_Downlight_Glow"); GLOW.use_nodes = True
    g = GLOW.node_tree.nodes["Principled BSDF"]; g.inputs["Emission Color"].default_value = (1.0, 0.75, 0.5, 1); g.inputs["Emission Strength"].default_value = 30
    notes = {l["id"]: l.get("note", "") for l in F.get("lights", [])}
    for l in F.get("lights", []):
        ref = re.match(r"as ([A-Z0-9-]+)", l.get("note", ""))   # "as PD-KT-1; ..." = the same fitting as that light
        if ref and ref.group(1) in notes: l = {**l, "note": notes[ref.group(1)] + "; " + l["note"]}
        x, y, z = mm(l["x"]), mm(l["y"]), mm(l["z"]); k = l["kind"].lower()
        if "down" in k:
            light(l["id"], "SPOT", (x, y, z - 0.03), 60, spot_size=1.6, spot_blend=0.6, shadow_soft_size=0.03,
                  use_shadow=False)   # no shadows from the ceiling downlights: EEVEE's shadow buffer overflowed (11.8k / 4096 pages)
            boxes(l["id"] + "_ring", [((x - 0.045, y - 0.045, z - 0.006), (x + 0.045, y + 0.045, z - 0.001))], DOT)
            boxes(l["id"] + "_lens", [((x - 0.03, y - 0.03, z - 0.007), (x + 0.03, y + 0.03, z - 0.006))], GLOW)
        elif "pendant" in k and re.search(r"dome|(\d+)\s*dia", l.get("note", "")):   # a round shade (e.g. "ceramic dome, 300 dia")
            d = re.search(r"(\d+)\s*dia", l.get("note", "")); r = (int(d.group(1)) / 2000) if d else 0.15
            cl = re.search(r"(terracotta|clay|ceramic|oak|black|bronze)", l.get("note", "")); shade_m = mat(("matt " + cl.group(1) + " ceramic") if cl else "ceramic", "#b5653f" if not cl or cl.group(1) in ("terracotta", "clay") else "#3a3633")
            sh = cyl(l["id"] + "_shade", (x, y), r, z, z + r * 1.1, shade_m, 32); bevel(sh, r * 0.5, 4)
            cyl(l["id"] + "_cord", (x, y), 0.003, z + r * 1.1, R["ceiling_z"] / 1000, BLACK, 8)
            light(l["id"], "SPOT", (x, y, z + 0.02), 35, spot_size=1.4, spot_blend=0.7, shadow_soft_size=0.05)
            light(l["id"] + "_glow", "POINT", (x, y, z + r * 0.5), 6, shadow_soft_size=0.05, use_shadow=False); lamp_bodies.append(l["id"])
        elif "pendant" in k:   # linear shade ~1200 long over the table, hung from the ceiling (the note's size)
            tb = next((i for i in F["items"] if i["kind"].lower().startswith("dining table") or i["id"].startswith("DN-TAB")), None)
            along_x = not tb or (tb["x"][1] - tb["x"][0]) >= (tb["y"][1] - tb["y"][0]); hl, hw = 0.6, 0.09
            lo = (x - (hl if along_x else hw), y - (hw if along_x else hl), z); hi = (x + (hl if along_x else hw), y + (hw if along_x else hl), z + 0.14)
            sh = boxes(l["id"] + "_shade", [(lo, hi)], mat("rattan clay pendant", "#b98a5c")); bevel(sh, 0.03, 3)
            ceil = R["ceiling_z"] / 1000
            boxes(l["id"] + "_wires", [((lo[0] + 0.05, y - 0.002, hi[2]), (lo[0] + 0.054, y + 0.002, ceil)), ((hi[0] - 0.054, y - 0.002, hi[2]), (hi[0] - 0.05, y + 0.002, ceil))], BLACK)
            light(l["id"], "AREA", (x, y, z - 0.01), 80, shape="RECTANGLE", size=hl * 2 if along_x else hw * 2, size_y=hw * 2 if along_x else hl * 2)
            light(l["id"] + "_up", "POINT", (x, y, z + 0.2), 15, shadow_soft_size=0.3)
            lamp_bodies.append(l["id"])
        elif "floor" in k:   # STAGING: base 300 x 300 (the note), stem, drum shade at the light point
            boxes(l["id"] + "_base", [((x - 0.15, y - 0.15, FZ), (x + 0.15, y + 0.15, FZ + 0.025))], BLACK)
            boxes(l["id"] + "_stem", [((x - 0.012, y - 0.012, FZ + 0.025), (x + 0.012, y + 0.012, z - 0.1))], BLACK)
            cyl(l["id"] + "_shade", (x, y), 0.22, z - 0.15, z + 0.15, SHADE, 32)
            light(l["id"], "POINT", (x, y, z), 40, shadow_soft_size=0.15); lamp_bodies.append(l["id"])
        elif "table" in k:   # STAGING: a stoneware body on the table top under it, linen shade at the light point
            under = [i for i in F["items"] if i["x"][0] <= l["x"] <= i["x"][1] and i["y"][0] <= l["y"] <= i["y"][1] and i["z_base"] + i["height"] < l["z"]]
            tz = max([mm(i["z_base"] + i["height"]) for i in under], default=FZ + 0.5)
            cyl(l["id"] + "_body", (x, y), 0.08, tz, z - 0.12, mat("stoneware", "#b9a58c"), 24)
            cyl(l["id"] + "_shade", (x, y), 0.16, z - 0.12, z + 0.1, SHADE, 32)
            light(l["id"], "POINT", (x, y, z), 18, shadow_soft_size=0.1); lamp_bodies.append(l["id"])
        elif "strip" in k:   # an LED strip under a cabinet or shelf: its run from the note ("x 9750-10650"), else 0.9 m
            run = re.search(r"x\s*(\d+)\s*(?:-|to|–)\s*(\d+)", l.get("note", "")); x0, x1 = (mm(int(run.group(1))), mm(int(run.group(2)))) if run else (x - 0.45, x + 0.45)
            boxes(l["id"] + "_led", [((x0, y - 0.006, z - 0.004), (x1, y + 0.006, z))], GLOW)
            light(l["id"], "AREA", ((x0 + x1) / 2, y, z - 0.01), 10, shape="RECTANGLE", size=x1 - x0, size_y=0.03, use_shadow=False)
        elif "wall light" in k:   # a slim linear light (e.g. over the mirror)
            boxes(l["id"] + "_bar", [((x - 0.3, y - 0.02, z - 0.015), (x + 0.3, y + 0.02, z + 0.015))], GLOW)
            light(l["id"], "AREA", (x, y, z - 0.02), 12, shape="RECTANGLE", size=0.6, size_y=0.04, use_shadow=False)
        elif "night" in k:
            light(l["id"], "POINT", (x, y, z), 1.5, use_shadow=False)
        else:
            light(l["id"], "POINT", (x, y, z), 20)

    # ---------- the dressing inside the furnished rooms: generic ceiling dots removed, the soft fill turned down ----------
    led = bpy.data.objects.get("LED_Dots")
    if led:
        bm = bmesh.new(); bm.from_mesh(led.data); bm.verts.ensure_lookup_table()
        gone = set()
        for f in bm.faces:
            c = f.calc_center_median()
            if abs(c.z - R["ceiling_z"] / 1000) < 0.05 and in_rooms(c.x, c.y): gone.update(f.verts)
        stats["dots"] += len(gone) // 8
        bmesh.ops.delete(bm, geom=list(gone), context="VERTS"); bm.to_mesh(led.data); bm.free()
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.name.startswith("Room_") and in_rooms(ob.location.x, ob.location.y) \
                and abs(ob.location.z - R["ceiling_z"] / 1000) < 0.2:   # this floor only (rooms above share the plan)
            ob.data.energy *= 0.35; dimmed.append(ob.name)


for fj in FILES: furnish_one(fj)

bpy.ops.wm.save_as_mainfile(filepath=out_blend)
res.update({"items": stats["items"], "built_by_kind": len(built), "plain_boxes": fallback, "lights": stats["lights"],
            "lamp_bodies_staged": lamp_bodies, "curtains_staged_open": curtains,
            "ceiling_dots_removed": stats["dots"], "room_fill_dimmed": dimmed})
json.dump(res, open(out_json, "w"), indent=2); print(json.dumps(res))
