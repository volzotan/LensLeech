import bpy
from bpy_extras import image_utils

import argparse
import sys
import os
import json
import math

import random


LUXCORE                     = False             # use luxcore rendering engine
SHOW_RENDER_PREVIEW         = False             # put blender in render mode when started
USE_SMOOTH_SHADING          = True              # apply smooth shading to all imported STL bodies

UNITS                       = "METRIC"

SAVE_FILE                   = True

START_FRAME                 = 1
END_FRAME                   = 360

POINT_DISTANCE              = 1.5
POINT_RADIUS                = 0.2
RANDOM_OFFSET               = 0.01

RENDER_OUTPUT               = "frames/######.png"
GROUND_TRUTH_OUTPUT         = "ground_truth.json"

WORLD_TEXTURE               = "artist_workshop_4k.exr"

# ----------------------------------------------------------------------------------------------------

# src: https://blender.stackexchange.com/a/134596/118415
class ArgumentParserForBlender(argparse.ArgumentParser):

    def _get_argv_after_doubledash(self):
        try:
            idx = sys.argv.index("--")
            return sys.argv[idx+1:] # the list after '--'
        except ValueError as e: # '--' not in the list:
            return []

    # overrides superclass
    def parse_args(self):
        return super().parse_args(args=self._get_argv_after_doubledash())


def showMessageBox(message, title="Message Box", icon='INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def importStl(filename):

    # scaling: 
    # STL input is in default fusion unit: cm
    # blender interprets this as cm->m: *10
    # scene should be rendered in cm->m->mm: *10 *0.1 *0.01
        
    bpy.ops.import_mesh.stl(files=[{"name":filename}], global_scale=0.001)

    object_names = []
    sel = bpy.context.selected_objects
    for obj in sel:
        object_names.append(obj.name)

    if not len(object_names) == 1:
        raise Exception("unexpected object names during import: {}".format(object_names))
    name = object_names[0]

    print("imported: {}".format(name))

    return bpy.data.objects[name]


# find the 3D view panel and its screen space
def find_3dview_space():
    area = None
    for a in bpy.data.window_managers[0].windows[0].screen.areas:
        if a.type == "VIEW_3D":
            area = a
            break
    return area.spaces[0] if area else bpy.context.space_data


# src: http://forums.luxcorerender.org/viewtopic.php?t=2183
def assignMaterial(obj):

    mat = bpy.data.materials.new(name="Material")
    tree_name = "Nodes_" + mat.name
    node_tree = bpy.data.node_groups.new(name=tree_name, type="luxcore_material_nodes")
    mat.luxcore.node_tree = node_tree

    # User counting does not work reliably with Python PointerProperty.
    # Sometimes, the material this tree is linked to is not counted as user.
    node_tree.use_fake_user = True

    nodes = node_tree.nodes

    output = nodes.new("LuxCoreNodeMatOutput")
    output.location = 300, 200
    output.select = False

    matmirror = nodes.new("LuxCoreNodeMatMirror")
    matmirror.location = 50, 200

    node_tree.links.new(matmirror.outputs[0], output.inputs[0])

    if obj.material_slots:
        obj.material_slots[obj.active_material_index].material = mat
    else:
        obj.data.materials.append(mat)

    # For viewport render, we have to update the luxcore object
    # because the newly created material is not yet assigned there
    obj.update_tag()


# blender unit conversion from Fusion360 cm to blender m
def convert_unit_cm(val):
    return val * 0.01


# blender unit conversion from mm to blender m
def convert_unit_mm(val):
    return val * 0.001


def orientation_to_rot(origin, direction):
    vec = [0, 0, 0]
        
    for i in range(0, 3):
        vec[i] = origin[i] - direction[i]
    x, y, z = vec

    return (
        math.atan2(z, math.sqrt(x**2 + y**2)) + math.pi/2,
        0,
        math.atan2(x, y) * -1,
    )


def pointy_hex_to_pixel(q, r, s, center=[0, 0], hex_size=1):
    x = hex_size * (math.sqrt(3) * q + math.sqrt(3)/2 * r)
    y = hex_size * (3./2 * r)
    return (x + center[0], y + center[1])


# ----------------------------------------------------------------------------------------------------

parser = ArgumentParserForBlender()

parser.add_argument("-i", "--input",
                    type=str,
                    default="example.json",
                    help="JSON scene description file (output of mirrorforge Fusion360 plugin)")

args = parser.parse_args()

# ----------------------------------------------------------------------------------------------------

# preflight checks

passed_checks = True

if LUXCORE and "BlendLuxCore" not in bpy.context.preferences.addons:
# if True:
    showMessageBox("BlendLuxCore plugin not found. Please install the plugin and reload. See luxcorerender.org/download/")
    passed_checks = False

if passed_checks:

    # General scene settings

    scene = bpy.context.scene

    if LUXCORE:
        scene.render.engine             = "LUXCORE"
        scene.luxcore.config.engine     = "BIDIR"
    else:
        scene.render.engine             = "BLENDER_EEVEE"

    scene.unit_settings.system          = UNITS
    scene.unit_settings.length_unit     = "MILLIMETERS"

    scene.render.resolution_x = 960
    scene.render.resolution_y = 540

    script_directory = os.path.dirname(os.path.realpath(__file__))
    scene.render.filepath = os.path.join(script_directory, RENDER_OUTPUT)

    # put blender in render preview mode

    if SHOW_RENDER_PREVIEW:
        for area in bpy.context.workspace.screens[0].areas:
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'RENDERED'

    # world setup

    # bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)

    # create background image
    world = bpy.data.worlds['World']
    world.use_nodes = True
    enode = world.node_tree.nodes.new("ShaderNodeTexEnvironment")
    enode.image = bpy.data.images.load(WORLD_TEXTURE)
    world.node_tree.links.new(enode.outputs['Color'], world.node_tree.nodes['Background'].inputs['Color'])

    space = find_3dview_space()
    # space.overlay.show_floor = False
    # space.overlay.show_axis_x = False
    # space.overlay.show_axis_y = False
    # space.overlay.show_cursor = False
    # space.overlay.show_object_origins = False

    scene.frame_start = START_FRAME
    scene.frame_end = END_FRAME
    scene.frame_current = START_FRAME

    # parse JSON

    basepath = os.path.dirname(args.input)

    hexdata = None
    try:
        with open(args.input) as json_file:
            hexdata = json.load(json_file)
    except Exception as e:
        print("opening JSON file failed: {}".format(e))

    # remove default scene objects
 
    # bpy.ops.object.select_all(action='DESELECT')
    for o in scene.objects:
        o.select_set(True)
    bpy.ops.object.delete() 

    # create camera

    camera_data = bpy.data.cameras.new(name='Camera')
    camera_object = bpy.data.objects.new('Camera', camera_data)     
    scene.collection.objects.link(camera_object)

    camera_object.rotation_euler = (math.radians(90), 0, 0)
    camera_object.location = [0, 0, 0]
    camera_object.scale = (.01, .01, .01)

    camera_object.data.clip_start = 0.001

    camera_object.data.lens_unit = "MILLIMETERS"
    camera_object.data.lens = 50

    # use a limited Depth of Field
    camera_object.data.dof.use_dof = True
    camera_object.data.dof.aperture_fstop = 2.0
    camera_object.data.dof.focus_distance = convert_unit_mm(35+0.2)

    # make the new camera the main camera
    scene.camera = camera_object

    # add global lights for the camera

    light_data = bpy.data.lights.new(name="light", type="AREA")     
    light_data.energy = 5000

    light_object = bpy.data.objects.new(name="light", object_data=light_data)
    bpy.context.collection.objects.link(light_object)
    bpy.context.view_layer.objects.active = light_object

    light_object.location = [0, 0, convert_unit_mm(500)]
    light_object.scale = [100, 100, 0]

    # create planes

    # bpy.ops.mesh.primitive_plane_add(location=(0, 0, -.001))
    # plane = bpy.context.active_object
    # plane.scale = (1, 1, .01)

    # add the parent object

    bpy.ops.object.empty_add(location=(0, 0, 0))
    parent = bpy.context.active_object
    parent.name = "BlobParent"

    # add pinhole mask

    pinhole = importStl(os.path.join(basepath, "pinhole.stl"))
    pinhole.location = (0, convert_unit_mm(25), 0)
    pinhole.parent = parent

    # smooth shading:
    # surface smoothing prior to raytracing
    if USE_SMOOTH_SHADING:
        mesh = pinhole.data
        for f in mesh.polygons:
            f.use_smooth = True

    # assign material
    mat_pinhole = bpy.data.materials.new(name="Pinhole")
    bpy.data.materials["Pinhole"].diffuse_color = (0, 0, 0, 1)
    if pinhole.data.materials:
        pinhole.data.materials[0] = mat_pinhole
    else:
        pinhole.data.materials.append(mat_pinhole)

    # setup the animation data

    parent.animation_data_create()

    parent.animation_data.action = bpy.data.actions.new(name="MovementAction")

    # translate

    # EXTENT = 5

    # # X, Y, Frame
    # positions = [
    #     [0,         0,          1],
    #     [-EXTENT,   -EXTENT,    END_FRAME/6*1],
    #     [EXTENT,    -EXTENT,    END_FRAME/6*2],
    #     [EXTENT,    EXTENT,     END_FRAME/6*3],
    #     [-EXTENT,   EXTENT,     END_FRAME/6*4],
    #     [0,         0,          END_FRAME/6*5]
    # ]

    # fcurve_x = parent.animation_data.action.fcurves.new(
    #     data_path="location", index=0
    # )

    # fcurve_y = parent.animation_data.action.fcurves.new(
    #     data_path="location", index=2
    # )

    # for i in range(0, len(positions)):

    #     k1 = fcurve_x.keyframe_points.insert(
    #         frame=positions[i][2],
    #         value=convert_unit_mm(positions[i][0])
    #     )
    #     k1.interpolation = "LINEAR"

    #     k2 = fcurve_y.keyframe_points.insert(
    #         frame=positions[i][2],
    #         value=convert_unit_mm(positions[i][1])
    #     )
    #     k2.interpolation = "LINEAR"

    # ---

    # rotate

    fcurve_r = parent.animation_data.action.fcurves.new(
        data_path="rotation_euler", index=1
    )

    k3 = fcurve_r.keyframe_points.insert(
        frame=START_FRAME,
        value=math.radians(0)
    )
    k3.interpolation = "LINEAR"

    k3 = fcurve_r.keyframe_points.insert(
        frame=END_FRAME,
        value=math.radians(360)
    )
    k3.interpolation = "LINEAR"

    # get ground truth data
    ground_truth = []
    for frame_number in range(START_FRAME, END_FRAME+1): # blender includes the END_FRAME

        data = {}
        data["frame"] = frame_number-1 # blender starts at START_FRAME = 1
        data["rotation"] = fcurve_r.evaluate(frame_number)

        ground_truth.append(data)

    with open(GROUND_TRUTH_OUTPUT, "w") as f:
        json.dump(ground_truth, f, indent=4)

    # add blobs

    # create material
    mat_0 = bpy.data.materials.new(name="Blob0")
    mat_1 = bpy.data.materials.new(name="Blob1")
    mat_2= bpy.data.materials.new(name="Blob2")
    materials = [mat_0, mat_1, mat_2]

    bpy.data.materials["Blob0"].diffuse_color = (0, 0, 1, 1)
    bpy.data.materials["Blob1"].diffuse_color = (0, 1, 0, 1)
    bpy.data.materials["Blob2"].diffuse_color = (1, 0, 0, 1)

    # create the torus collection
    collection = bpy.data.collections.new("blobs")
    bpy.context.scene.collection.children.link(collection)

    for key in hexdata["data"].keys():
        q, r, s = [int(c) for c in key.split("|")]

        x, y = pointy_hex_to_pixel(q, r, s, hex_size=POINT_DISTANCE/2)

        # mirror the pattern horizontally so origin is _top_ left.
        y *= -1
        
        # blender-native object
        
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=convert_unit_mm(POINT_RADIUS),
        )        
        # bpy.ops.mesh.primitive_cylinder_add(
        #     radius=convert_unit_mm(0.5),
        #     depth=convert_unit_mm(0.1)
        # )
        obj = bpy.context.object

        random_x = 0
        random_y = 0

        if RANDOM_OFFSET is not None:
            random_x = random.uniform(-1, 1) * RANDOM_OFFSET
            random_y = random.uniform(-1, 1) * RANDOM_OFFSET

        obj.location = (
            convert_unit_mm(x + random_x), 
            convert_unit_mm(25+10), 
            convert_unit_mm(y + random_y), 
        )

        mat = None

        value = int(hexdata["data"][key])
        if value == 0:
            mat = mat_0
        elif value == 1:
            mat = mat_1
        elif value == 2:
            mat = mat_2
        else:
            raise Exception("unknown color in JSON file: {}".format(value))

        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        bpy.ops.collection.objects_remove_all()
        bpy.data.collections['blobs'].objects.link(obj)
        obj.parent = parent

    # save file

    if SAVE_FILE:
        bpy.ops.wm.save_as_mainfile(filepath="output.blend")