# STAGING for the video tour (2026-11-02, Sam: "the interior needs to look really nice"): builds the decor in
# decor_tour.json into a furnished .blend: the rooms on the tour path the furnishing runs left empty (hall,
# stair, landing, bedroom 3) and finishing touches in the furnished ones. Every piece is built in code from its box, so
# the same file gives the same decor every time. The model, its dressing and the furnishing are not changed, except the
# items the file lists under "hide". Everything added lives in the "Decor" collections. Its lights cast no shadows
# (EEVEE's shadow pool is already full; measured on the hook).
# Run: blender -b <furnished.blend> --factory-startup -P decorate.py -- <project> <out.blend> <out.json>
import bpy, bmesh, sys, json, os, math, random
from mathutils import Vector, Matrix

args = sys.argv[sys.argv.index("--") + 1:]
proj, out_blend, out_json = [os.path.abspath(a) for a in args[:3]]   # plain names / . work too
D = json.load(open(os.path.join(proj, "decor_tour.json"), encoding="utf-8"))
mm = lambda v: v / 1000
rng = random.Random(20261102)   # fixed seed: the same leaves every run

def coll(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    return c
DEC = coll("Decor"); LIG = coll("Decor_Lights")

# ---------- materials ----------
def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)
MATS = {}
def mat(kind, hexc, rough=0.7, metal=0.0, noise=0.0, scale=30.0, stretch=None, emit=0.0, alpha=1.0):
    key = (kind, hexc, rough, metal, noise, scale, stretch, emit, alpha)
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(f"D_{kind}_{hexc[1:]}"); m.use_nodes = True
    nt = m.node_tree; p = nt.nodes["Principled BSDF"]; base = lin(hexc)
    p.inputs["Roughness"].default_value = rough; p.inputs["Metallic"].default_value = metal
    if noise:
        tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 6
        src = tc.outputs["Object"]
        if stretch:
            mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = stretch; nt.links.new(src, mp.inputs["Vector"]); src = mp.outputs["Vector"]
        nt.links.new(src, nz.inputs["Vector"])
        rp = nt.nodes.new("ShaderNodeValToRGB"); e = rp.color_ramp.elements
        e[0].color = (*[c * (1 - noise) for c in base], 1); e[1].color = (*[min(1, c * (1 + noise)) for c in base], 1)
        nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"]); nt.links.new(rp.outputs["Color"], p.inputs["Base Color"])
    else:
        p.inputs["Base Color"].default_value = (*base, 1)
    if emit:
        p.inputs["Emission Color"].default_value = (*base, 1); p.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        p.inputs["Alpha"].default_value = alpha; m.surface_render_method = "BLENDED"
    MATS[key] = m; return m
WOOD = lambda h: mat("wood", h, 0.5, 0, 0.25, 3.0, (0.08, 1.0, 1.0))
FABRIC = lambda h: mat("fabric", h, 0.95, 0, 0.08, 180.0)
CERAMIC = lambda h: mat("ceramic", h, 0.45, 0, 0.06, 40.0)
BLACK = mat("black metal", "#1a1a1a", 0.35, 1.0)
BRASS = mat("brass", "#b08d57", 0.3, 1.0)
GLOW = mat("glow", "#ffd8a8", 0.5, 0, 0, 30, None, 12.0)
OPAL = mat("opal", "#fff1dc", 0.4, 0, 0, 30, None, 4.0)

# ---------- geometry helpers ----------
def mesh_ob(name, bm, m, coll_=DEC):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(m)
    ob = bpy.data.objects.new(name, me); coll_.objects.link(ob); return ob
def box(name, lo, hi, m):
    bm = bmesh.new()
    for v in bmesh.ops.create_cube(bm, size=1.0)["verts"]: v.co = Vector([lo[i] + (hi[i] - lo[i]) * (v.co[i] + 0.5) for i in range(3)])
    return mesh_ob(name, bm, m)
def bevel(ob, w=0.01, seg=3):
    md = ob.modifiers.new("Bevel", "BEVEL"); md.width = w; md.segments = seg; md.limit_method = "ANGLE"; return ob
def soft(ob, w=0.04, seg=4):
    bevel(ob, w, seg); sd = ob.modifiers.new("Soft", "SUBSURF"); sd.levels = sd.render_levels = 1
    for p in ob.data.polygons: p.use_smooth = True
    return ob
def cyl(name, c, r0, r1, z0, z1, m, seg=32, axis="Z"):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r0, radius2=r1, depth=z1 - z0)
    ob = mesh_ob(name, bm, m)
    for p in ob.data.polygons: p.use_smooth = len(p.vertices) == 4
    if axis == "Z": ob.location = (c[0], c[1], (z0 + z1) / 2)
    else:   # lying along x or y: c = the centre, z0..z1 = the extent along that axis
        ob.rotation_euler = (0, math.pi / 2, 0) if axis == "X" else (math.pi / 2, 0, 0); ob.location = c
    return ob
def sphere(name, c, r, m, scale=(1, 1, 1), seg=24):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    ob = mesh_ob(name, bm, m); ob.location = c; ob.scale = scale
    for p in ob.data.polygons: p.use_smooth = True
    return ob
def light(name, kind, loc, energy, color=(1.0, 0.72, 0.48), **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color; ld.use_shadow = False
    for k, v in kw.items(): setattr(ld, k, v)
    ob = bpy.data.objects.new(name, ld); ob.location = loc; LIG.objects.link(ob); return ob
def lohi(it): return [mm(it["x"][0]), mm(it["y"][0]), mm(it["z"])], [mm(it["x"][1]), mm(it["y"][1]), mm(it["z"] + it["h"])]
def thin_axis(lo, hi): return 0 if hi[0] - lo[0] < hi[1] - lo[1] else 1

# ---------- builders ----------
def rug(it):
    lo, hi = lohi(it); bevel(box(it["id"], lo, hi, FABRIC(it["colour"])), 0.004, 1)
    if it.get("border"):
        b = 0.1; z = hi[2]; bm_ = FABRIC(it["border"])
        for k, (a, c) in enumerate([((lo[0], lo[1]), (hi[0], lo[1] + b)), ((lo[0], hi[1] - b), (hi[0], hi[1])), ((lo[0], lo[1]), (lo[0] + b, hi[1])), ((hi[0] - b, lo[1]), (hi[0], hi[1]))]):
            box(f"{it['id']}_b{k}", (a[0], a[1], z), (c[0], c[1], z + 0.001), bm_)
def console(it):
    lo, hi = lohi(it); m = WOOD(it["colour"]); t = 0.035
    bevel(box(it["id"] + "_top", (lo[0], lo[1], hi[2] - t), hi, m), 0.004)
    ax = 1 if hi[1] - lo[1] > hi[0] - lo[0] else 0
    for k, s in enumerate((0, 1)):   # two slab ends
        a, b = list(lo), [hi[0], hi[1], hi[2] - t]
        if ax == 1: (b.__setitem__(1, lo[1] + t)) if s == 0 else a.__setitem__(1, hi[1] - t)
        else: (b.__setitem__(0, lo[0] + t)) if s == 0 else a.__setitem__(0, hi[0] - t)
        bevel(box(f"{it['id']}_end{k}", a, b, m), 0.004)
    a, b = list(lo), list(hi); a[2] = lo[2] + 0.12; b[2] = lo[2] + 0.12 + 0.025
    bevel(box(it["id"] + "_shelf", a, b, m), 0.003)
def round_mirror(it):
    lo, hi = lohi(it); ax = thin_axis(lo, hi); r = min(hi[1 - ax] - lo[1 - ax], hi[2] - lo[2]) / 2
    c = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2]
    fr = cyl(it["id"] + "_frame", c, r, r, 0, 0.02, BLACK, 64, "X" if ax == 0 else "Y")
    gl = cyl(it["id"] + "_glass", c, r - 0.02, r - 0.02, 0, 0.022, mat("mirror", "#e6e6e6", 0.02, 1.0), 64, "X" if ax == 0 else "Y")
def vase(it):
    lo, hi = lohi(it); c = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2); r = min(hi[0] - lo[0], hi[1] - lo[1]) / 2
    m = CERAMIC(it["colour"]); h = (hi[2] - lo[2]) * (0.55 if it.get("branches") else 1)
    v = cyl(it["id"], c, r * 0.75, r * 0.45, lo[2], lo[2] + h, m, 32); soft(v, r * 0.3, 3)
    if it.get("branches"):   # three thin dark stems with a few small leaves
        for k in range(3):
            a = 2 * math.pi * k / 3 + 0.4; ln = (hi[2] - lo[2]) * (0.75 + 0.15 * k)
            st = cyl(f"{it['id']}_stem{k}", (c[0], c[1]), 0.004, 0.002, lo[2] + h * 0.6, lo[2] + h * 0.6 + ln, mat("stem", "#3b3026", 0.8), 8)
            st.rotation_euler = (0.25 * math.cos(a), 0.25 * math.sin(a), 0)
            for j in range(5):
                t = 0.45 + 0.1 * j; p = Vector((c[0], c[1], lo[2] + h * 0.6)) + st.rotation_euler.to_matrix() @ Vector((0, 0, ln * t - ln / 2)) + Vector((0, 0, ln / 2))
                sphere(f"{it['id']}_leaf{k}_{j}", p + Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), 0)), 0.025, mat("leaf", "#5c6b3e", 0.6, 0, 0.15, 20), (1.6, 0.6, 0.25), 12)
def bowl(it):
    lo, hi = lohi(it); c = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2); r = min(hi[0] - lo[0], hi[1] - lo[1]) / 2
    for k in range(it.get("stack", 1)):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r * (1 - 0.12 * k))
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 0.001], context="VERTS")
        ob = mesh_ob(f"{it['id']}_{k}", bm, CERAMIC(it["colour"])); ob.scale = (1, 1, (hi[2] - lo[2]) / r * 0.9)
        ob.location = (c[0], c[1], lo[2] + (hi[2] - lo[2]) * 0.9 + 0.02 * k)
        sd = ob.modifiers.new("Solid", "SOLIDIFY"); sd.thickness = 0.006
        for p in ob.data.polygons: p.use_smooth = True
    if it["kind"] == "fruit bowl":   # lemons and green apples
        for k in range(7):
            a = 2 * math.pi * k / 7; rr = r * 0.45 * (0.4 + 0.6 * (k % 2))
            sphere(f"{it['id']}_fruit{k}", (c[0] + rr * math.cos(a), c[1] + rr * math.sin(a), lo[2] + 0.06 + 0.02 * (k % 3)), 0.04,
                   mat("fruit", "#e3c23a" if k % 2 else "#9bb53e", 0.4, 0, 0.1, 50), (1, 1, 0.92))
def books(it):
    lo, hi = lohi(it); cols = ["#2f3b45", "#a8613f", "#d8ccb4", "#5b4b3e", "#6f7350", "#e3dacb"]
    if it.get("lying"):
        z = lo[2]
        for k in range(3):
            th = 0.02 + 0.008 * (k % 2); sh = 0.012 * k
            o = box(f"{it['id']}_{k}", (lo[0] + sh, lo[1] + sh, z), (hi[0] - sh * 0.5, hi[1] - sh, z + th), mat("book", cols[(k * 2) % 6], 0.7)); bevel(o, 0.002, 1); z += th
    else:
        x = lo[0]
        while x < hi[0] - 0.02:
            w = rng.uniform(0.02, 0.04); h = (hi[2] - lo[2]) * rng.uniform(0.75, 1.0)
            o = box(f"{it['id']}_{int(x * 1000)}", (x, lo[1], lo[2]), (x + w, hi[1], lo[2] + h), mat("book", rng.choice(cols), 0.7)); bevel(o, 0.002, 1); x += w + 0.002
def table_lamp(it):
    lo, hi = lohi(it); c = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2); h = hi[2] - lo[2]
    b = cyl(it["id"] + "_body", c, 0.07, 0.05, lo[2], lo[2] + h * 0.55, CERAMIC(it["colour"])); soft(b, 0.02, 3)
    cyl(it["id"] + "_shade", c, 0.12, 0.09, lo[2] + h * 0.55, hi[2], mat("linen shade", "#efe4cf", 0.9, 0, 0, 30, None, 1.5), 48)
    light(it["id"] + "_light", "POINT", (c[0], c[1], lo[2] + h * 0.72), 12, shadow_soft_size=0.08)
def plant(it):
    lo, hi = lohi(it); c = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])); W = min(hi[0] - lo[0], hi[1] - lo[1]); H = hi[2] - lo[2]
    pr = W * 0.32; ph = min(0.45, H * 0.28)
    p = cyl(it["id"] + "_pot", c[:2], pr * 0.8, pr, lo[2], lo[2] + ph, CERAMIC(it.get("pot", "#d9cbb3"))); bevel(p, 0.01, 3)
    cyl(it["id"] + "_soil", c[:2], pr * 0.95, pr * 0.95, lo[2] + ph - 0.03, lo[2] + ph - 0.01, mat("soil", "#3a2e25", 1.0))
    small = H < 0.6
    leafm = [mat("leaf", h_, 0.55, 0, 0.12, 25) for h_ in (it["colour"], "#4a7a42", "#36592f")]
    n_st = 4 if small else 6
    for s in range(n_st):   # stems from the pot, each with leaves along its upper part
        a = 2 * math.pi * s / n_st + rng.uniform(-0.3, 0.3); lean = rng.uniform(0.12, 0.3)
        top = c + Vector((math.cos(a) * W * lean, math.sin(a) * W * lean, ph + (H - ph) * rng.uniform(0.75, 1.0)))
        base = c + Vector((0, 0, ph - 0.02)); d = top - base
        st = cyl(f"{it['id']}_st{s}", (0, 0), 0.006 if not small else 0.002, 0.004 if not small else 0.0015, 0, d.length, mat("stem", "#4a3b2c", 0.8), 8)
        st.location = base + d / 2; st.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        n_lv = 4 if small else 7
        for j in range(n_lv):
            t = 0.35 + 0.65 * j / max(1, n_lv - 1); pos = base + d * t
            sz = (0.05 if small else 0.13) * rng.uniform(0.75, 1.15)
            lf = sphere(f"{it['id']}_lf{s}_{j}", pos + Vector((rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04), 0)), sz, rng.choice(leafm), (1.0, 0.55, 0.08), 12)
            lf.rotation_euler = (rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9), rng.uniform(0, math.pi))
PAL = {"dusk": ["#2c3e57", "#c98a6b", "#e8c9a0"], "sand": ["#efe6d6", "#d8c6a5", "#b5653f"], "olive": ["#3a3633", "#6f7350", "#d8c6a5"], "clay": ["#5b4b3e", "#a8613f", "#e3dacb"]}
def art(it):
    lo, hi = lohi(it); ax = thin_axis(lo, hi)
    bevel(box(it["id"] + "_frame", lo, hi, WOOD(it.get("frame", "#a67c52")) if it.get("frame", "#") != "#1a1a1a" else BLACK), 0.003, 1)
    c0, c1 = list(lo), list(hi); al = 1 - ax; c0[al] += 0.025; c1[al] -= 0.025; c0[2] += 0.025; c1[2] -= 0.025
    wall_low = (lo[ax] < 4.2 and ax == 0 and lo[ax] > 3.9) or (ax == 0 and lo[ax] < 0.5) or (ax == 1 and lo[ax] < 5.1)  # the wall is on the low side
    if hi[ax] > 6.4 and ax == 0 or hi[ax] > 8.5 and ax == 0: wall_low = False
    if "wall" in it: wall_low = it["wall"] in ("south", "west")  # stated in the data (2026-11-03: TW-ART's canvas lay flush with its frame front and flickered)
    if wall_low: c1[ax] += 0.003
    else: c0[ax] -= 0.003
    # the canvas: soft horizontal bands of the palette, broken by noise (an abstract landscape)
    m = bpy.data.materials.new(f"D_canvas_{it['id']}"); m.use_nodes = True; nt = m.node_tree; p = nt.nodes["Principled BSDF"]; p.inputs["Roughness"].default_value = 0.9
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.5; nz.inputs["Detail"].default_value = 4
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); add = nt.nodes.new("ShaderNodeMath"); add.operation = "MULTIPLY_ADD"; add.inputs[1].default_value = 0.35
    nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(tc.outputs["Generated"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], add.inputs[0]); nt.links.new(sep.outputs["Z"], add.inputs[2])
    rp = nt.nodes.new("ShaderNodeValToRGB"); e = rp.color_ramp.elements; pal = PAL[it.get("palette", "sand")]
    e[0].position = 0.25; e[0].color = (*lin(pal[0]), 1); e[1].position = 0.85; e[1].color = (*lin(pal[2]), 1); e.new(0.55).color = (*lin(pal[1]), 1)
    nt.links.new(add.outputs[0], rp.inputs["Fac"]); nt.links.new(rp.outputs["Color"], p.inputs["Base Color"])
    box(it["id"] + "_canvas", c0, c1, m)
def pendant_globe(it):
    lo, hi = lohi(it); c = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2); r = (hi[0] - lo[0]) / 2
    sphere(it["id"] + "_globe", (c[0], c[1], lo[2] + r), r, OPAL, (1, 1, 1), 32)
    cyl(it["id"] + "_cord", c, 0.003, 0.003, lo[2] + 2 * r, mm(it["ceiling"]), BLACK, 8)
    cyl(it["id"] + "_rose", c, 0.05, 0.05, mm(it["ceiling"]) - 0.02, mm(it["ceiling"]), BLACK)
    light(it["id"] + "_light", "POINT", (c[0], c[1], lo[2] + r), 35, shadow_soft_size=r)
def sconce(it):
    lo, hi = lohi(it); c = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2]
    f = it.get("faces", "east"); d = {"east": Vector((1, 0, 0)), "west": Vector((-1, 0, 0)), "north": Vector((0, 1, 0)), "south": Vector((0, -1, 0))}[f]
    wall = Vector(c) - d * ((hi[0] - lo[0]) / 2 if f in ("east", "west") else (hi[1] - lo[1]) / 2)
    plate = box(it["id"] + "_plate", tuple(wall - Vector((0.006, 0.05, 0.08)) + d * 0.0), tuple(wall + Vector((0.006, 0.05, 0.08)) + d * 0.012), BRASS)
    if f in ("north", "south"): plate.rotation_euler = (0, 0, math.pi / 2); plate.location = wall;
    arm = wall + d * 0.09
    s = cyl(it["id"] + "_shade", arm[:2], 0.055, 0.04, arm.z - 0.06, arm.z + 0.07, BRASS, 32)
    sm = s.modifiers.new("Solid", "SOLIDIFY"); sm.thickness = 0.002
    sphere(it["id"] + "_bulb", (arm.x, arm.y, arm.z), 0.025, GLOW)
    light(it["id"] + "_up", "SPOT", (arm.x, arm.y, arm.z + 0.03), 25, spot_size=1.2, spot_blend=0.8, shadow_soft_size=0.04).rotation_euler = (math.pi, 0, 0)
    light(it["id"] + "_glow", "POINT", (arm.x, arm.y, arm.z), 4, shadow_soft_size=0.04)
def slat_wall(it):
    lo, hi = lohi(it); ax = thin_axis(lo, hi); al = 1 - ax; m = WOOD(it["colour"])
    back = list(lo), list(hi); back[1][ax] = lo[ax] + 0.012
    box(it["id"] + "_back", back[0], back[1], mat("slat back", "#2a2420", 0.9))
    w, g = 0.042, 0.018; a = lo[al] + 0.01
    while a + w <= hi[al] - 0.005:
        s0, s1 = list(lo), list(hi); s0[al], s1[al] = a, a + w; s0[ax] = lo[ax] + 0.012
        bevel(box(f"{it['id']}_{int(a * 1000)}", s0, s1, m), 0.003, 1); a += w + g
    light(it["id"] + "_wash", "AREA", ((lo[0] + hi[0]) / 2 + (0.15 if ax == 0 else 0), (lo[1] + hi[1]) / 2, hi[2] - 0.05), 20, shape="RECTANGLE", size=0.1, size_y=hi[al] - lo[al]).rotation_euler = (0, 0, 0)
def tv(it):
    lo, hi = lohi(it); bevel(box(it["id"], lo, hi, mat("tv body", "#111111", 0.3, 0.6)), 0.004, 1)
    ax = thin_axis(lo, hi); al = 1 - ax; s0, s1 = list(lo), list(hi); s0[al] += 0.008; s1[al] -= 0.008; s0[2] += 0.008; s1[2] -= 0.02
    if it.get("faces", "east") in ("east", "north"): s0[ax] = hi[ax]; s1[ax] = hi[ax] + 0.001
    else: s1[ax] = lo[ax]; s0[ax] = lo[ax] - 0.001
    box(it["id"] + "_screen", s0, s1, mat("tv screen", "#05070a", 0.06, 0.0))
def throw(it):
    lo, hi = lohi(it); soft(box(it["id"], lo, hi, FABRIC(it["colour"])), 0.015, 3)
def board(it):
    lo, hi = lohi(it); bevel(box(it["id"], lo, hi, WOOD(it["colour"])), 0.006, 2)
def jars(it):
    lo, hi = lohi(it); n = 4; w = (hi[0] - lo[0]) / n
    for k in range(n):
        c = (lo[0] + w * (k + 0.5), (lo[1] + hi[1]) / 2); h = (hi[2] - lo[2]) * (0.6 + 0.4 * ((k * 7) % 3) / 2)
        j = cyl(f"{it['id']}_{k}", c, w * 0.38, w * 0.38, lo[2], lo[2] + h, mat("jar glass", "#dfe6e2", 0.05, 0, 0, 30, None, 0, 0.35)); bevel(j, 0.008, 2)
        cyl(f"{it['id']}_{k}_fill", c, w * 0.34, w * 0.34, lo[2] + 0.005, lo[2] + h * 0.6, mat("jar fill", ["#d8b46a", "#7a5a3a", "#efe6d6", "#9b4a2a"][k], 0.8))
        cyl(f"{it['id']}_{k}_lid", c, w * 0.39, w * 0.39, lo[2] + h, lo[2] + h + 0.02, WOOD("#a67c52"))
def bed(it):
    lo, hi = lohi(it); m_frame = WOOD("#8a6440"); head_w = it.get("head", "west") == "west"
    bevel(box(it["id"] + "_plinth", (lo[0], lo[1], lo[2] + 0.05), (hi[0], hi[1], lo[2] + 0.28), m_frame), 0.01, 2)
    box(it["id"] + "_kick", (lo[0] + 0.08, lo[1] + 0.08, lo[2]), (hi[0] - 0.08, hi[1] - 0.08, lo[2] + 0.05), mat("shadow", "#151311", 0.9))
    soft(box(it["id"] + "_mattress", (lo[0] + 0.02, lo[1] + 0.02, lo[2] + 0.28), (hi[0] - 0.02, hi[1] - 0.02, lo[2] + 0.48), FABRIC("#f2efe8")), 0.03)
    soft(box(it["id"] + "_duvet", (lo[0] + (0.45 if head_w else 0), lo[1] - 0.02, lo[2] + 0.44), (hi[0] - (0 if head_w else 0.45) + 0.02, hi[1] + 0.02, hi[2]), FABRIC(it["colour"])), 0.05)
    fx = (hi[0] - 0.55, hi[0] - 0.12) if head_w else (lo[0] + 0.12, lo[0] + 0.55)
    soft(box(it["id"] + "_throw", (fx[0], lo[1] - 0.03, lo[2] + 0.5), (fx[1], hi[1] + 0.03, hi[2] + 0.025), FABRIC(it.get("throw", "#6f7350"))), 0.02)
    n = 2; w = (hi[1] - lo[1] - 0.12) / n
    for k in range(n):
        y0 = lo[1] + 0.06 + k * w; x0 = lo[0] + 0.06 if head_w else hi[0] - 0.3
        soft(box(f"{it['id']}_pillow{k}", (x0, y0 + 0.02, lo[2] + 0.48), (x0 + 0.24, y0 + w - 0.02, lo[2] + 0.66), FABRIC("#f6f3ec")), 0.07)
        soft(box(f"{it['id']}_cushion{k}", (x0 + 0.2, y0 + 0.12, lo[2] + 0.5), (x0 + 0.34, y0 + w - 0.12, lo[2] + 0.72), FABRIC("#a8613f" if k == 0 else "#d8ccb4")), 0.06)
def headboard(it):
    slat_wall(it)
def nightstand(it):
    lo, hi = lohi(it); m = WOOD(it["colour"])
    bevel(box(it["id"], (lo[0], lo[1], lo[2] + 0.12), hi, m), 0.006, 2)
    box(it["id"] + "_drawer", (hi[0] - 0.002, lo[1] + 0.03, hi[2] - 0.17), (hi[0] + 0.001, hi[1] - 0.03, hi[2] - 0.166), BLACK)
    for x in (lo[0] + 0.03, hi[0] - 0.05):
        for y in (lo[1] + 0.03, hi[1] - 0.05): box(f"{it['id']}_leg{int(x*1000)}{int(y*1000)}", (x, y, lo[2]), (x + 0.02, y + 0.02, lo[2] + 0.12), BLACK)
def lounge_chair(it):
    lo, hi = lohi(it); m = mat("leather", it["colour"], 0.42, 0, 0.12, 60)
    f = it.get("faces", "south"); back_hi = f == "south"   # facing south: the back is on the north side
    soft(box(it["id"] + "_seat", (lo[0] + 0.05, lo[1] + 0.05, lo[2] + 0.22), (hi[0] - 0.05, hi[1] - 0.05, lo[2] + 0.4), m), 0.05)
    b0 = (lo[0] + 0.05, hi[1] - 0.18 if back_hi else lo[1] + 0.05, lo[2] + 0.3); b1 = (hi[0] - 0.05, hi[1] - 0.05 if back_hi else lo[1] + 0.18, hi[2])
    soft(box(it["id"] + "_back", b0, b1, m), 0.06)   # (a tilt here would turn about the world origin: the objects sit at 0,0,0)
    for x in (lo[0] + 0.06, hi[0] - 0.09):
        for y in (lo[1] + 0.06, hi[1] - 0.09): box(f"{it['id']}_leg{int(x*1000)}{int(y*1000)}", (x, y, lo[2]), (x + 0.03, y + 0.03, lo[2] + 0.22), WOOD("#6b4a32"))

FLOOR = None
def floor(it):   # oak planks 180 mm wide, 1.2 m long, staggered, a hairline joint (Blender's brick texture), 4 mm thick
    global FLOOR
    if FLOOR is None:
        m = bpy.data.materials.new("D_oak_floor"); m.use_nodes = True; nt = m.node_tree; p = nt.nodes["Principled BSDF"]
        p.inputs["Roughness"].default_value = 0.45
        tc = nt.nodes.new("ShaderNodeTexCoord"); br = nt.nodes.new("ShaderNodeTexBrick")
        br.offset = 0.5; br.squash = 1.0; br.inputs["Scale"].default_value = 1.0; br.inputs["Mortar Size"].default_value = 0.0015
        br.inputs["Brick Width"].default_value = 1.2; br.inputs["Row Height"].default_value = 0.18
        br.inputs["Color1"].default_value = (*lin("#b08a62"), 1); br.inputs["Color2"].default_value = (*lin("#9a7652"), 1)
        br.inputs["Mortar"].default_value = (*lin("#5a4632"), 1); br.inputs["Bias"].default_value = 0.0
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 8
        mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.06, 1.0, 1.0)   # long grain along x
        nt.links.new(tc.outputs["Object"], br.inputs["Vector"]); nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs["Factor"].default_value = 0.35
        nt.links.new(br.outputs["Color"], mix.inputs["A"]); nt.links.new(nz.outputs["Color"], mix.inputs["B"])
        nt.links.new(mix.outputs["Result"], p.inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15; bump.inputs["Distance"].default_value = 0.002
        nt.links.new(br.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
        FLOOR = m
    lo, hi = lohi(it); ob = box(it["id"], lo, hi, FLOOR); ob.location = (0, 0, 0)

def stair_glass_rail(it):   # frameless glass on the stair's open side, side-mounted on steel standoffs, an oak handrail on top
    # v2 (Sam: "The anchors should line with the sides of the stairs - now they look like they are in air"; "the portion
    # above either should not exist or if it does (by code) it should be separated from the wall"): the standoffs sit on
    # each step's side face, the glass reaches lower over the step sides, the glass stops 12 mm under the first-floor
    # slab (the side mount is under the slab from y ~3.3) and the handrail ends 100 mm clear of it
    s = next(t for t in json.load(open(os.path.join(proj, "design.json")))["stairs"] if t["id"] == it["stair"])
    y_first, rise, going = mm(s["first_riser_y"]), mm(s["riser_height"]), mm(s["going"])
    pitch = lambda y: rise + (y - y_first) * rise / going            # the nosing line: z over the stair at y
    tread = lambda y: rise * (math.floor((y - y_first) / going) + 1)  # the top of the step at y
    CEIL = 2.8                                                       # the first-floor slab's underside (S_SL_FF z 2.80-3.20)
    x0 = mm(it["side_x"]) + 0.012; x1 = x0 + 0.012                   # 12 mm glass, 12 mm off the stair's side face
    ya, yb = mm(it["y"][0]), mm(it["y"][1]); H = mm(it["h"])
    gm = next((o.material_slots[0].material for o in bpy.data.objects if o.name.startswith("Glass_BL") and o.material_slots), None) \
        or mat("glass", "#dfe9e6", 0.05, 0, 0, 30, None, 0, 0.25)
    edge = bpy.data.materials.get("Glass_Edge") or mat("glass edge", "#4d8073", 0.05)
    steel = mat("brushed steel", "#a7a9ab", 0.3, 1.0)
    bot = lambda y: max(0.02, pitch(y) - 0.36)                        # the glass laps well over the steps' sides
    top = lambda y: min(pitch(y) + H - 0.05, CEIL - 0.012)
    y_ceil = y_first + (CEIL - 0.012 - H + 0.05 - rise) * going / rise    # where the sloped top meets the slab
    def slab(name, pts, xa, xb, m):                                   # a flat panel: pts = (y, z) round the outline
        bm = bmesh.new(); a = [bm.verts.new((xa, y, z)) for y, z in pts]; b = [bm.verts.new((xb, y, z)) for y, z in pts]
        n = len(pts); bm.faces.new(a); bm.faces.new(b[::-1])
        for i in range(n): j = (i + 1) % n; bm.faces.new((a[i], a[j], b[j], b[i]))
        return mesh_ob(name, bm, m)
    n, gap = 3, 0.02; w = (yb - ya - gap * (n - 1)) / n
    for k in range(n):
        p0 = ya + k * (w + gap); p1 = p0 + w
        tops = [(p1, top(p1))] + ([(y_ceil, top(y_ceil))] if p0 < y_ceil < p1 else []) + [(p0, top(p0))]
        slab(f"{it['id']}_glass_{k + 1}", [(p0, bot(p0)), (p1, bot(p1))] + tops, x0, x1, gm)
        for yy in (p0 + 0.15, p1 - 0.15):                             # two standoffs per panel, on a step's side face
            z = max(tread(yy), rise) - 0.10
            cyl(f"{it['id']}_standoff", ((mm(it["side_x"]) + x1 + 0.008) / 2, yy, z), 0.022, 0.022, mm(it["side_x"]), x1 + 0.008, steel, 24, "X")
    # the oak handrail: 56 wide x 42 deep on the glass's sloped top edge, from 60 mm before the first panel to 100 mm
    # under the slab, both ends cut square
    e0 = ya - 0.06; e1 = y_first + (CEIL - 0.10 - 0.042 - H + 0.05 - rise) * going / rise
    t0, t1 = pitch(e0) + H - 0.05, pitch(e1) + H - 0.05
    xc = (x0 + x1) / 2
    slab(f"{it['id']}_handrail", [(e0, t0), (e1, t1), (e1, t1 + 0.042), (e0, t0 + 0.042)], xc - 0.028, xc + 0.028, WOOD("#b07a4a"))
    bevel(bpy.data.objects[f"{it['id']}_handrail"], 0.008, 3)
    slab(f"{it['id']}_channel", [(e0, t0 - 0.004), (e1, t1 - 0.004), (e1, t1 + 0.002), (e0, t0 + 0.002)], x0 - 0.003, x1 + 0.003, edge)

BUILD = {"floor": floor, "rug": rug, "console": console, "round mirror": round_mirror, "vase": vase, "bowl": bowl, "fruit bowl": bowl, "books": books,
         "table lamp": table_lamp, "plant": plant, "art": art, "pendant globe": pendant_globe, "sconce": sconce, "slat wall": slat_wall,
         "tv": tv, "throw": throw, "board": board, "jars": jars, "bed": bed, "headboard": headboard, "nightstand": nightstand, "lounge chair": lounge_chair,
         "stair glass rail": stair_glass_rail}

hidden = []
for h in D.get("hide", []):
    for ob in bpy.data.objects:
        if ob.name == h["id"] or ob.name.startswith(h["id"] + "_"): ob.hide_render = True; ob.hide_viewport = True; hidden.append(ob.name)
built, failed = [], []
for it in D["items"]:
    try: BUILD[it["kind"]](it); built.append(it["id"])
    except Exception as e: failed.append(f"{it['id']}: {e!r}")
# FIX (Sam 2026-11-02: "two ceiling lights floating above the staircase - looks like maybe they should belong on the
# ceiling of the second floor"): dress_home_v4.py spreads the hall's LED dots over the whole room at the ground-floor
# ceiling (2.8 m), but over the stair (design.json ST1, x 4.0-5.1) the first floor has its opening, so three dots
# (x 4.63, y 1.06 / 2.59 / 4.12) hang in the void. Lift them to the stairwell's own ceiling (5.9 m, FF_S).
lifted = 0
led = bpy.data.objects.get("LED_Dots")
if led:
    mw, inv = led.matrix_world, led.matrix_world.inverted()
    for v in led.data.vertices:
        w = mw @ v.co
        if 4.0 < w.x < 5.1 and 0.3 < w.y < 4.88 and 2.7 < w.z < 2.85:
            w.z += 3.1; v.co = inv @ w; lifted += 1
    led.data.update()
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
res = {"built": len(built), "failed": failed, "hidden": hidden, "objects_in_decor": len(DEC.objects), "lights": len(LIG.objects),
       "stair_dots_lifted": lifted // 8}
json.dump(res, open(out_json, "w"), indent=2); print("DECOR", json.dumps(res))
