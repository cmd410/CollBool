import bpy


bl_info = {
    "name": "CollBool",
    "description": "Addon that allows to do auto booleans with collections",
    "author": "Crystal Melting Dot",
    "version": (1, 1, 0),
    "blender": (2, 80, 0),
    "category": "Mesh",
    "location": "Object properties -> CollBool"
}


dont_change = False   # To not add/remove any modifiers while they are applied


def validate_collection(self, coll):
    obj = bpy.context.object
    coll_contents = coll.objects
    if obj.name in coll_contents or \
        any([
            obj.collbool_settings.diff == coll,
            obj.collbool_settings.unio == coll,
            obj.collbool_settings.inte == coll
            ]):
        return False
    return True


def usage_update(self, context):
    global dont_change
    if self.use or dont_change: return
    modifiers = context.object.modifiers
    for i in modifiers:
        if i.type == 'BOOLEAN' and i.name.startswith('collbool_'):
            modifiers.remove(i)


def unique_mod(obj, target, name, coll):
    modifires = obj.modifiers
    for mod in modifires.values():
        if mod.type != 'BOOLEAN':
            continue
        if not mod.object:
            modifires.remove(mod)
            continue
        if mod.name.startswith('collbool_') and mod.object.name not in coll.all_objects:
            mod.object.display_type = 'TEXTURED'
            mod.object.hide_render = False
            modifires.remove(mod)
            continue
        if mod.object == target:
            if mod.name != name:
                mod.name = name
            return mod
    mod = modifires.new(name, 'BOOLEAN')
    mod.show_expanded = False
    mod.object = target
    return mod


def handle_collbool(obj, coll, operation):
    if not all([obj, coll, operation]): 
        return
    targets = [i for i in coll.all_objects if i.type == 'MESH']
    for t in targets:
        if t.collbool_settings.use:
            t.collbool_settings.use = False
        t.display_type = 'BOUNDS'
        t.hide_render = True
        modifier = unique_mod(obj, t, f'collbool_{operation[:4].lower()}_{t.name}_{coll.name}', coll)
        modifier.operation = operation


@bpy.app.handlers.persistent
def scene_update(scene):
    global dont_change
    if dont_change: return
    for obj in scene.objects:
        if obj.type != 'MESH': continue
        if not obj.collbool_settings.use: continue

        if obj.collbool_settings.diff:
            handle_collbool(obj, obj.collbool_settings.diff, 'DIFFERENCE')
        if obj.collbool_settings.unio:
            handle_collbool(obj, obj.collbool_settings.unio, 'UNION')
        if obj.collbool_settings.inte:
            handle_collbool(obj, obj.collbool_settings.inte, 'INTERSECT')
        
        names = [i.name for i in [
            obj.collbool_settings.diff,
            obj.collbool_settings.unio,
            obj.collbool_settings.inte] if i]
        for mod in obj.modifiers:
            if not mod.name.startswith('collbool_'):
                continue
            if any([mod.name.endswith(f'_{name}') for name in names]):
                continue
            obj.modifiers.remove(mod)


class ApplyCollBoolOperator(bpy.types.Operator):
    '''Apply collection booleans. 
    WARNING: First manually apply all modifiers above boolean or result might be very wrong'''
    bl_idname = "object.collbool"
    bl_label = "Apply"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return \
            all([context.mode == 'OBJECT',
                 context.active_object,
                 context.active_object.type == 'MESH',
                 context.active_object.collbool_settings.use])

    def execute(self, context):
        global dont_change
        obj = context.active_object
        dont_change = True
        obj.collbool_settings.use = False
        for mod in obj.modifiers:
            if not mod.name.startswith('collbool_'):
                continue
            if not mod.object:
                obj.modifiers.remove(mod)
                continue
            bpy.ops.object.modifier_apply(modifier=mod.name)
        dont_change = False
        self.report({'INFO'}, "Collection boolean applied!")
        return {'FINISHED'}


class CollBoolSettings(bpy.types.PropertyGroup):
    use: bpy.props.BoolProperty(
        name='Use Collection Boolean',
        default=False,
        update=usage_update
    )
    diff: bpy.props.PointerProperty(
        name='Difference',
        type=bpy.types.Collection,
        description='Collection to apply as difference boolean',
        poll=validate_collection)
    unio: bpy.props.PointerProperty(
        name='Union',
        type=bpy.types.Collection,
        description='Collection to apply as union boolean',
        poll=validate_collection)
    inte: bpy.props.PointerProperty(
        name='Intersection',
        type=bpy.types.Collection,
        description='Collection to apply as intersection boolean',
        poll=validate_collection)


class ObjectSelectPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_collbool"
    bl_label = "Collbool"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == 'MESH'

    def draw(self, context):
        settings = context.object.collbool_settings
        layout = self.layout
        row = layout.row()
        row.prop(settings, 'use')
        row.operator(ApplyCollBoolOperator.bl_idname)
        if settings.use:
            layout.prop(settings, 'diff')
            layout.prop(settings, 'unio')
            layout.prop(settings, 'inte')


classes = [
    CollBoolSettings,
    ApplyCollBoolOperator,
    ObjectSelectPanel
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Object.collbool_settings = bpy.props.PointerProperty(type=CollBoolSettings)
    bpy.app.handlers.depsgraph_update_post.append(scene_update)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    try:
        bpy.app.handlers.depsgraph_update_post.remove(scene_update)
    except ValueError:
        pass


if __name__ == '__main__':
    register()