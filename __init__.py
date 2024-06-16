import bpy

bl_info = {
    "name": "SKD_Keeper",
    "author": "Zlh",
    "version": (2, 0),
    "blender": (4, 1, 0),
    "location": "3DView > ToolShelf",
    "description": "maintain the drivers of shapekeys while apply modifiers",
    "support": "COMMUNITY",
    "category": "ZlhTools"
}
from bpy.types import Operator, PropertyGroup

def copy_object(obj, times=1, offset=0):
    # TODO: maybe get the collection of the source and link the object to
    # that collection instead of the scene main collection

    objects = []
    for i in range(0,times):
        copy_obj = obj.copy()
        copy_obj.data = obj.data.copy()
        copy_obj.name = obj.name + "_shapekey_" + str(i+1)
        copy_obj.location.x += offset*(i+1)

        bpy.context.collection.objects.link(copy_obj)
        objects.append(copy_obj)

    return objects

def apply_shapekey(obj, sk_keep):
    """ deletes all shapekeys except the one with the given index """
    shapekeys = obj.data.shape_keys.key_blocks

    # check for valid index
    if sk_keep < 0 or sk_keep > len(shapekeys):
        return

    # remove all other shapekeys
    for i in reversed(range(0, len(shapekeys))):
        if i != sk_keep:
            obj.shape_key_remove(shapekeys[i])

    # remove the chosen one and bake it into the object
    obj.shape_key_remove(shapekeys[0])

def apply_modifiers(obj):
    """ applies all modifiers in order """

    modifiers = obj.modifiers
    for modifier in modifiers:
        if modifier.type == 'SUBSURF':
            modifier.show_only_control_edges = False

    for o in bpy.context.scene.objects:
        o.select_set(False)

    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # uses object.convert to circumvent errors with disabled modifiers
    # bpy.ops.object.convert(target='MESH')

    for mod in modifiers:
        if mod.show_viewport:
            bpy.ops.object.modifier_apply(modifier=mod.name, report=False, merge_customdata=True, single_user=False)

def add_objs_shapekeys(destination, sources):
    """ takes an array of objects and adds them as shapekeys to the destination object """
    for o in bpy.context.scene.objects:
        o.select_set(False)

    for src in sources:
        src.select_set(True)

    bpy.context.view_layer.objects.active = destination
    bpy.ops.object.join_shapes()

class driver_value:
    shapeKeyName: str
    type: str
    expression: str
    variables: list

class variables_value:
    name: str
    type: str
    targets: list

class target_value:
    id_type: str
    id: str
    bone_target: str
    context_property: str
    data_path: str
    rotation_mode: str
    transform_space: str
    transform_type: str

def get_driver_value(driver):
    # COPY DRIVER
    a_driver = driver_value()
    a_driver.shapeKeyName = driver.data_path.split('"')[1]
    a_driver.type = driver.driver.type
    a_driver.expression = driver.driver.expression
    variables = driver.driver.variables

    variables_values = []
    for variable in variables:
        a_variable = variables_value()
        a_variable.name = variable.name
        a_variable.type = variable.type
        targets = variable.targets

        targets_values = []
        for target in targets:
            a_target = target_value()

            a_target.id_type = target.id_type
            a_target.id = target.id
            a_target.bone_target = target.bone_target
            a_target.context_property = target.context_property
            a_target.data_path = target.data_path
            a_target.rotation_mode = target.rotation_mode
            a_target.transform_space = target.transform_space
            a_target.transform_type = target.transform_type

            targets_values.append(a_target)

        a_variable.targets = targets_values
        variables_values.append(a_variable)
    a_driver.variables = variables_values
    return a_driver

def create_driver(obj, driver_value):
    driver = obj.data.shape_keys.key_blocks[driver_value.shapeKeyName].driver_add('value')
    driver = driver.driver
    # PASTE DRIVER
    driver.type = driver_value.type
    driver.expression = driver_value.expression

    for variable_value in driver_value.variables:
        variable = driver.variables.new()

        variable.name = variable_value.name
        variable.type = variable_value.type
        targets = variable.targets
        targets_value = variable_value.targets

        for j in range(0, len(targets_value)):
            target = targets[j]
            target_value_0 = targets_value[j]

            if target.id_type != target_value_0.id_type:
                target.id_type = target_value_0.id_type
            target.id = target_value_0.id
            target.bone_target = target_value_0.bone_target
            target.context_property = target_value_0.context_property
            target.data_path = target_value_0.data_path
            target.rotation_mode = target_value_0.rotation_mode
            target.transform_space = target_value_0.transform_space
            target.transform_type = target_value_0.transform_type

def main(obj):
    # save driver data
    drivers_data = []
    for driver in obj.data.shape_keys.animation_data.drivers:
        drivers_data.append(get_driver_value(driver))

    # get the shapekey names
    sk_names = []
    for block in obj.data.shape_keys.key_blocks:
        sk_names.append(block.name)

    # create receiving object that will contain all collapsed shapekeys
    receiver = copy_object(obj, times=1, offset=0)[0]
    receiver.name = "sk_receiver"
    apply_shapekey(receiver, 0)
    apply_modifiers(receiver)

    num_shapes = len(obj.data.shape_keys.key_blocks)

    # create a copy for each blendshape and transfer it to the receiver one after the other
    # start the loop at 1 so we skip the base shapekey
    # 开始进度条，总步数为100
    bpy.context.window_manager.progress_begin(0, num_shapes)

    for i in range(1, num_shapes):
        # copy of baseobject / blendshape donor
        blendshape = copy_object(obj, times=1, offset=0)[0]
        apply_shapekey(blendshape, i)
        apply_modifiers(blendshape)

        # add the copy as a blendshape to the receiver
        add_objs_shapekeys(receiver, [blendshape])

        # restore the shapekey name
        receiver.data.shape_keys.key_blocks[i].name = sk_names[i]

        # delete the blendshape donor and its mesh datablock (save memory)
        mesh_data = blendshape.data
        bpy.data.objects.remove(blendshape)
        bpy.data.meshes.remove(mesh_data)

        bpy.context.window_manager.progress_update(i)


    # delete the original and its mesh data
    orig_name = obj.name
    orig_data = obj.data
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(orig_data)

    # rename the receiver
    receiver.name = orig_name

    for driver_data in drivers_data:
        create_driver(receiver, driver_data)

    # 结束进度条
    bpy.context.window_manager.progress_end()
    return receiver

class SKD_apply_mods_without_armature(Operator):
    """ Applies modifiers and keeps shapekeys """
    bl_idname = "skd.apply_mods_without_armature"
    bl_label = "Apply All Visible Modifiers Without Armature (Keep Shapekeys)"
    bl_options = {'REGISTER', 'UNDO'}

    def validate_input(self, obj):
        # GUARD CLAUSES | USER ERROR

        # check for valid selection
        if not obj:
            self.report({'ERROR'}, "No Active object. Please select an object")
            return {'CANCELLED'}

        # check for valid obj-type
        if obj.type != 'MESH':
            self.report({'ERROR'}, "Wrong object type. Please select a MESH object")
            return {'CANCELLED'}

        # check for shapekeys
        if not obj.data.shape_keys:
            self.report({'ERROR'}, "The selected object doesn't have any shapekeys")
            return {'CANCELLED'}

        # check for multiple shapekeys
        if len(obj.data.shape_keys.key_blocks) == 1:
            self.report({'ERROR'}, "The selected object only has a base shapekey")
            return {'CANCELLED'}

        # check for modifiers
        if len(obj.modifiers) == 0:
            self.report({'ERROR'}, "The selected object doesn't have any modifiers")
            return {'CANCELLED'}

    def execute(self, context):
        obj = context.active_object
        a = []
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE':
                a.append(mod.show_viewport)
                mod.show_viewport = False

        # check for valid object
        if self.validate_input(obj) == {'CANCELLED'}:
            return {'CANCELLED'}

        obj = main(obj)
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE':
                mod.show_viewport = a.pop(0)
        return {'FINISHED'}


class SKD_apply_mods(Operator):
    """ Applies modifiers and keeps shapekeys """
    bl_idname = "skd.apply_mods"
    bl_label = "Apply All Visible Modifiers (Keep Shapekeys)"
    bl_options = {'REGISTER', 'UNDO'}

    def validate_input(self, obj):
        # GUARD CLAUSES | USER ERROR

        # check for valid selection
        if not obj:
            self.report({'ERROR'}, "No Active object. Please select an object")
            return {'CANCELLED'}

        # check for valid obj-type
        if obj.type != 'MESH':
            self.report({'ERROR'}, "Wrong object type. Please select a MESH object")
            return {'CANCELLED'}

        # check for shapekeys
        if not obj.data.shape_keys:
            self.report({'ERROR'}, "The selected object doesn't have any shapekeys")
            return {'CANCELLED'}

        # check for multiple shapekeys
        if len(obj.data.shape_keys.key_blocks) == 1:
            self.report({'ERROR'}, "The selected object only has a base shapekey")
            return {'CANCELLED'}

        # check for modifiers
        if len(obj.modifiers) == 0:
            self.report({'ERROR'}, "The selected object doesn't have any modifiers")
            return {'CANCELLED'}

    def execute(self, context):
        obj = context.active_object

        # check for valid object
        if self.validate_input(obj) == {'CANCELLED'}:
            return {'CANCELLED'}

        main(obj)
        return {'FINISHED'}

classes = (
    SKD_apply_mods_without_armature,
    SKD_apply_mods
)


def modifier_panel(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(SKD_apply_mods_without_armature.bl_idname)
    layout.operator(SKD_apply_mods.bl_idname)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.VIEW3D_MT_object.append(modifier_panel)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)

    bpy.types.VIEW3D_MT_object.remove(modifier_panel)