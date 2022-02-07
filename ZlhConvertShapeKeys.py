import bpy

bl_info = {
    "name": "ZlhShapeKeysDriverReplicator",
    "author": "Zlh",
    "version": (1, 0),
    "blender": (2, 83, 0),
    "location": "3DView > ToolShelf",
    "description": "Convert ShapeKeys Drivers to Shapekeys with same name",
    "support": "COMMUNITY",
    "category": "ZlhTools"
}


class ZlhVariable:
    def __init__(self, varname, bone, transform_type):
        self.varname = varname
        self.bone = bone
        self.transform_type = transform_type


class ZlhShapeKey:

    def __init__(self, name, expression, variables):
        self.name = name
        self.expression = expression
        self.variables = variables.copy()


zlhShapeKeys = {}
armature = None


class ZlhConvertShapeKeys(bpy.types.Panel):
    bl_label = "ShapeKeysDriverReplicator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Zlh Tools"

    def draw(self, context):
        layout = self.layout
        layout.label(text="仅传递同名形态键的骨骼驱动")
        layout.operator(CopyShapeKeys.bl_idname, text="复制drivers")
        layout.operator(PasteShapeKeys.bl_idname, text="粘贴drivers")


def register():
    bpy.utils.register_class(ZlhConvertShapeKeys)
    bpy.utils.register_class(CopyShapeKeys)
    bpy.utils.register_class(PasteShapeKeys)


def unregister():
    bpy.utils.unregister_class(ZlhConvertShapeKeys)
    bpy.utils.unregister_class(CopyShapeKeys)
    bpy.utils.unregister_class(PasteShapeKeys)


class CopyShapeKeys(bpy.types.Operator):
    bl_idname = "zlh_tools.copyshapekeys"
    bl_label = "Copy ShapeKeys"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        zlhShapeKeys.clear()
        currentObj = bpy.context.object.name
        global armature
        armature = bpy.context.object.modifiers['Armature'].object
        for ShapeKey in bpy.data.objects[currentObj].data.shape_keys.animation_data.drivers:
            ShapeKey_Name = ShapeKey.data_path.split('"')[1]
            ShapeKey_Expression = ShapeKey.driver.expression
            variables_temp = {}
            for variable in ShapeKey.driver.variables:
                variable_name = variable.name
                bone = variable.targets[0].bone_target
                transform_type = variable.targets[0].transform_type
                zlhVariable = ZlhVariable(variable_name, bone, transform_type)
                variables_temp[variable_name] = zlhVariable
            zlhShapeKey = ZlhShapeKey(ShapeKey_Name, ShapeKey_Expression, variables_temp)
            zlhShapeKeys[zlhShapeKey.name] = zlhShapeKey
        return {'FINISHED'}


class PasteShapeKeys(bpy.types.Operator):
    bl_idname = "zlh_tools.pasteshapekeys"
    bl_label = "Paste ShapeKeys"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        currentObj = bpy.context.object.name
        for shapeKey in zlhShapeKeys.values():
            dvr = bpy.data.objects[currentObj].data.shape_keys.key_blocks[shapeKey.name].driver_add('value')
            dvr.driver.type = 'SCRIPTED'
            for variable in shapeKey.variables.values():
                var = dvr.driver.variables.new()
                setDriverVariables(var, variable.varname, armature, variable.bone, variable.transform_type)
            dvr.driver.expression = shapeKey.expression
        return {'FINISHED'}


def setDriverVariables(var, varname, target_id, bone, transform_type):
    var.name = varname
    var.type = 'TRANSFORMS'
    target = var.targets[0]
    target.id = target_id
    target.bone_target = bone
    target.transform_space = 'LOCAL_SPACE'
    target.transform_type = transform_type
