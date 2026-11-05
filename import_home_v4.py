# Import home_v4.obj (or home_v7.obj) (SolidCraft export, mm, Z up) into an empty scene, save a .blend, write a check JSON.
# Run: blender -b --factory-startup -P import_home_v4.py -- <obj> <out.blend> <out.json>
import bpy, sys, json, os
from mathutils import Vector

obj_path, blend_path, json_path = [os.path.abspath(a) for a in sys.argv[sys.argv.index("--") + 1:][:3]]   # plain file names work too

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "METERS"

# SolidCraft is Z up with y pointing north, so keep the axes as they are; mm -> m.
bpy.ops.wm.obj_import(filepath=obj_path, forward_axis="Y", up_axis="Z", global_scale=0.001)

objs = [o for o in scene.objects if o.type == "MESH"]
lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
tris = 0
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)

os.makedirs(os.path.dirname(blend_path), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

result = {
    "blender": bpy.app.version_string,
    "objects": len(objs),
    "names_sample": sorted(o.name for o in objs)[:5],
    "triangles": tris,
    "bbox_min_m": [round(v, 4) for v in lo],
    "bbox_max_m": [round(v, 4) for v in hi],
    "blend": blend_path,
}
with open(json_path, "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps(result))
