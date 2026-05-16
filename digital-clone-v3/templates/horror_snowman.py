"""
Template: Horror Snowman "Snowman in my house"
Structure (25 seconds):
  0-3  sec: Dark screen + typing text (handled by fallback/motion canvas)
  3-8  sec: Snowman stands in garden, camera slowly approaches
  8-15 sec: Snowman comes alive — eyes glow red
  15-20 sec: Snowman walks toward camera, sharp teeth
  20-25 sec: Jumpscare (fast approach) + THE END text
"""

import bpy
import math

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

DURATION = {duration}
FPS = 30
TOTAL_FRAMES = int(DURATION * FPS)
bpy.context.scene.frame_end = TOTAL_FRAMES
bpy.context.scene.render.fps = FPS
bpy.context.scene.render.resolution_x = 1080
bpy.context.scene.render.resolution_y = 1920
bpy.context.scene.render.resolution_percentage = 100

# ─── WORLD (dark night sky) ───
scene = bpy.context.scene
scene.world.use_nodes = True
wd = scene.world.node_tree
wd.nodes.clear()
wn_bg = wd.nodes.new('ShaderNodeBackground')
wn_out = wd.nodes.new('ShaderNodeOutputWorld')
wn_bg.inputs[0].default_value = (0.015, 0.025, 0.05, 1)
wn_bg.inputs[1].default_value = 0.5
wd.links.new(wn_bg.outputs[0], wn_out.inputs[0])

# ─── LIGHTING (dark but visible) ───
bpy.ops.object.light_add(type='SUN', location=(8, 8, 15))
sun = bpy.context.active_object
sun.data.energy = 3.0
sun.data.color = (0.5, 0.6, 0.9)

# Warm lantern in front
bpy.ops.object.light_add(type='POINT', location=(3, 5, 2.5))
candle = bpy.context.active_object
candle.data.energy = 80
candle.data.color = (1.0, 0.6, 0.2)
candle.data.shadow_soft_size = 0.5

# Fill from side
bpy.ops.object.light_add(type='AREA', location=(-4, 3, 3))
fill = bpy.context.active_object
fill.data.energy = 40
fill.data.color = (0.4, 0.5, 0.8)
fill.data.size = 3

# Rim light (cold blue from behind)
bpy.ops.object.light_add(type='AREA', location=(-2, -6, 4))
rim = bpy.context.active_object
rim.data.energy = 50
rim.data.color = (0.3, 0.4, 0.7)
rim.data.size = 4

# ─── CAMERA ───
bpy.ops.object.camera_add(location=(0, -9, 2.5))
cam = bpy.context.active_object
cam.rotation_euler = (math.radians(75), 0, 0)
scene.camera = cam

# ─── SNOWMAN (three spheres, slightly smaller) ───
# Bottom
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 1.0))
bottom = bpy.context.active_object
bottom.name = "SnowBottom"
bottom.scale = (1, 1, 0.85)

# Middle
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.75, location=(0, 0, 2.4))
middle = bpy.context.active_object
middle.name = "SnowMiddle"
middle.scale = (1, 1, 0.9)

# Head
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 3.5))
head = bpy.context.active_object
head.name = "SnowHead"

# Snow material
snow_mat = bpy.data.materials.new(name="Snow")
snow_mat.use_nodes = True
bsdf = snow_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs['Base Color'].default_value = (0.92, 0.95, 1.0, 1)
bsdf.inputs['Roughness'].default_value = 0.65

for obj in [bottom, middle, head]:
    obj.data.materials.append(snow_mat)

# Eyes (black coal, larger)
eye_objs = []
for x in [-0.14, 0.14]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(x, 0.42, 3.55))
    eye = bpy.context.active_object
    eye.name = f"Eye_{x}"
    eye_mat = bpy.data.materials.new(name=f"EyeMat_{x}")
    eye_mat.use_nodes = True
    eye_mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.02, 0.02, 0.02, 1)
    eye.data.materials.append(eye_mat)
    eye_objs.append(eye)

# Red glow pupils (hidden initially, scale up later)
for x in [-0.14, 0.14]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, location=(x, 0.46, 3.55))
    pupil = bpy.context.active_object
    pupil.name = f"Pupil_{x}"
    pupil.scale = (0, 0, 0)  # hidden
    p_mat = bpy.data.materials.new(name=f"PupilMat_{x}")
    p_mat.use_nodes = True
    p_bsdf = p_mat.node_tree.nodes["Principled BSDF"]
    p_bsdf.inputs['Base Color'].default_value = (0.8, 0.0, 0.0, 1)
    p_bsdf.inputs['Emission Color'].default_value = (1.0, 0.0, 0.0, 1)
    p_bsdf.inputs['Emission Strength'].default_value = 5.0
    pupil.data.materials.append(p_mat)

# Carrot nose (cone)
bpy.ops.mesh.primitive_cone_add(radius1=0.05, radius2=0.0, depth=0.4, location=(0, 0.48, 3.45))
nose = bpy.context.active_object
nose.rotation_euler = (math.radians(90), 0, 0)
nose_mat = bpy.data.materials.new(name="Nose")
nose_mat.use_nodes = True
nose_mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (1, 0.35, 0, 1)
nose.data.materials.append(nose_mat)

# Sharp teeth (small cones in grin)
for i, angle in enumerate(range(-30, 31, 12)):
    rad = math.radians(angle)
    x = 0.18 * math.sin(rad)
    z = 3.35 + 0.18 * math.cos(rad)
    bpy.ops.mesh.primitive_cone_add(radius1=0.02, radius2=0.0, depth=0.1, location=(x, 0.44, z))
    tooth = bpy.context.active_object
    tooth.name = f"Tooth_{i}"
    tooth.rotation_euler = (math.radians(85), 0, rad)
    t_mat = bpy.data.materials.new(name=f"ToothMat_{i}")
    t_mat.use_nodes = True
    t_mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.9, 0.9, 0.85, 1)
    tooth.data.materials.append(t_mat)

# Stick arms
for x in [-1.0, 1.0]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=1.4, location=(x, 0, 2.2))
    arm = bpy.context.active_object
    arm.name = f"Arm_{x}"
    arm.rotation_euler = (0, 0, math.radians(100 if x > 0 else -100))
    a_mat = bpy.data.materials.new(name=f"ArmMat_{x}")
    a_mat.use_nodes = True
    a_mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.15, 0.08, 0.02, 1)
    arm.data.materials.append(a_mat)

# ─── BACKGROUND (dark forest, far away, NOT in front of camera) ───
# Camera is at (0, -18, 5) looking at (0, 0, 3.2)
# Avoid placing trees at angle ~0 (directly in front)
for i in range(8):
    angle = ((i / 8) * math.pi * 1.5) + math.pi * 0.75  # 135 to 405 degrees, avoiding 0
    dist = 12 + (i % 3) * 2
    x = math.cos(angle) * dist
    y = math.sin(angle) * dist
    h = 3 + (i % 3)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=h, location=(x, y, h / 2))
    trunk = bpy.context.active_object
    trunk.name = f"Tree_{i}"
    trunk_mat = bpy.data.materials.new(name=f"TrunkMat_{i}")
    trunk_mat.use_nodes = True
    trunk_mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.05, 0.03, 0.02, 1)
    trunk.data.materials.append(trunk_mat)

# Ground (snow)
bpy.ops.mesh.primitive_plane_add(size=35, location=(0, 0, -0.1))
floor = bpy.context.active_object
floor.name = "Ground"
floor_mat = bpy.data.materials.new(name="SnowGround")
floor_mat.use_nodes = True
floor_mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.8, 0.88, 0.95, 1)
floor.data.materials.append(floor_mat)

# ─── ANIMATION ───

# Phase 1: Camera slowly approaches
for i in range(TOTAL_FRAMES + 1):
    scene.frame_set(i)
    t = i / TOTAL_FRAMES
    
    # Camera: slow creepy approach then fast jumpscare
    if t < 0.75:
        # Slow creepy approach
        cam_z = 5.5 + math.sin(t * math.pi * 2) * 0.5
        cam_y = -22 + t * 14  # from -22 to -8
    else:
        # Jumpscare fast approach
        cam_z = 5.0
        cam_y = -8 - (1 - t) * 20  # rush closer
    
    cam.location = (math.sin(t * math.pi * 0.5) * 1.0, cam_y, cam_z)
    cam.keyframe_insert(data_path="location")
    
    # Head slowly turns toward camera
    head_turn = math.radians(25) * min(t / 0.5, 1.0)
    head.rotation_euler = (0, head_turn * 0.3, head_turn)
    head.keyframe_insert(data_path="rotation_euler")

# Pupils appear and glow red at 8 sec (frame 240)
for frame in [1, 240]:
    scene.frame_set(frame)
    for obj in bpy.data.objects:
        if "Pupil" in obj.name:
            if frame == 1:
                obj.scale = (0.01, 0.01, 0.01)
            else:
                obj.scale = (1.0, 1.0, 1.0)
            obj.keyframe_insert(data_path="scale")

# Snowman "walks" toward camera after 15 sec (frame 450)
for frame in [1, 450]:
    scene.frame_set(frame)
    if frame == 450:
        for part in [bottom, middle, head]:
            part.location.y += 2.5
            part.keyframe_insert(data_path="location")
        for obj in bpy.data.objects:
            if any(x in obj.name for x in ["Eye", "Nose", "Tooth", "Arm", "Pupil"]):
                obj.location.y += 2.5
                obj.keyframe_insert(data_path="location")

# ─── RENDER ───
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.filepath = "//frames/frame_"
scene.render.image_settings.file_format = 'PNG'
scene.eevee.use_bloom = True
scene.eevee.bloom_intensity = 0.08
scene.eevee.taa_render_samples = 32

scene.frame_set(1)
bpy.ops.render.render(animation=True)
