bl_info = {
    "name": "Point Cloud Display",
    "author": "Zicklag ( https://github.com/zicklag )",
    "version": (0, 1),
    "blender": (4, 1, 0),
    "location": "View3D > Sidebar -> View -> Point Cloud Display / Object Properties -> Viewport Display -> Point Cloud Display",
    "description": "Allows you to view point clouds in the 3D viewport.",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

##
# Create Shader
##

vert_out = gpu.types.GPUStageInterfaceInfo("my_interface")
vert_out.smooth('VEC3', "pos")
vert_out.smooth('VEC3', "col")

shader_info = gpu.types.GPUShaderCreateInfo()
shader_info.push_constant('MAT4', "transform")
shader_info.push_constant('MAT4', "viewProjectionMatrix")
shader_info.vertex_in(0, 'VEC3', "position")
shader_info.vertex_in(1, 'VEC3', "color")
shader_info.vertex_out(vert_out)
shader_info.fragment_out(0, 'VEC4', "FragColor")

shader_info.vertex_source(
    "void main()"
    "{"
    "  pos = position;"
    "  col = color;"
    "  gl_Position = viewProjectionMatrix * transform * vec4(position, 1.0f);"
    "}"
)

shader_info.fragment_source(
    "void main()"
    "{"
    "  FragColor = vec4(col, 1.0);"
    "}"
)

shader = gpu.shader.create_from_info(shader_info)
del vert_out
del shader_info

batches = {}

def enable_point_cloud_for_obj(obj):
    obj.display_type = 'BOUNDS'
    mesh = obj.data
    coords = [v.co for v in mesh.vertices]
    colors = [v.color for v in mesh.color_attributes[0].data]
    batches[obj.data.name_full] = batch_for_shader(shader, 'POINTS', {"position": coords, "color": colors})

def disable_point_cloud_for_obj(obj):
    obj.display_type = 'SOLID'
    batches[obj.data.name_full] = None

##
# Blender UI Integration
## 
    
def prop_update(self, context):
    if context.object.data.point_cloud_display.enabled:
        enable_point_cloud_for_obj(context.object)
    else:
        context.object.display_type = 'SOLID'
        batches[context.object.data.name_full] = None
        
class PointCloudDisplaySettings(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(name='Enabled', update=prop_update, default=False)
    point_size: bpy.props.FloatProperty(name='Point Size', default = 5, min = 0.01)
    
class PointCloudDisplaySettingsPanel(bpy.types.Panel):
    def draw(self, context):
        self.layout.enabled = type(context.object.data) == bpy.types.Mesh
        row = self.layout.row()
        row.alignment = 'LEFT'
        row.prop(context.object.data.point_cloud_display, "enabled")
        row.prop(context.object.data.point_cloud_display, "point_size")

class PointCloudDisplaySettingsPropertiesPanel(PointCloudDisplaySettingsPanel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "Point Cloud Display"
    bl_parent_id = "OBJECT_PT_display"
    bl_options = {'DEFAULT_CLOSED'}
    
class PointCloudDisplaySettings3DViewPanel(PointCloudDisplaySettingsPanel):    
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "View"
    bl_label = "Point Cloud Display"

##
# Rendering
##
    
def draw_point_clouds():
    scene = bpy.context.scene
    for obj in scene.objects:
        if obj.visible_get() and type(obj.data) == bpy.types.Mesh and obj.data.point_cloud_display.enabled:
            if not obj.data.name_full in batches:
                enable_point_cloud_for_obj(obj)
                continue
            
            batch = batches[obj.data.name_full]
            matrix = bpy.context.region_data.perspective_matrix
            shader.uniform_float("viewProjectionMatrix", matrix)
            shader.uniform_float("transform", obj.matrix_world)
            gpu.state.point_size_set(obj.data.point_cloud_display.point_size)
            gpu.state.depth_test_set('LESS')
            batch.draw(shader)

##
# Addon Registration
##

render_hook = None
    
def register():
    bpy.utils.register_class(PointCloudDisplaySettings)
    bpy.utils.register_class(PointCloudDisplaySettingsPropertiesPanel)
    bpy.utils.register_class(PointCloudDisplaySettings3DViewPanel)
    bpy.types.VIEW3D_PT_view3d_properties.append(PointCloudDisplaySettingsPanel)
    bpy.types.Mesh.point_cloud_display = bpy.props.PointerProperty(type=PointCloudDisplaySettings)
    render_hook = bpy.types.SpaceView3D.draw_handler_add(draw_point_clouds, (), 'WINDOW', 'POST_VIEW')
    
def unregister():
    bpy.utils.unregister_class(PointCloudDisplaySettings)
    bpy.utils.unregister_class(PointCloudDisplaySettingsPropertiesPanel)
    bpy.utils.unregister_class(PointCloudDisplaySettings3DViewPanel)
    bpy.types.Mesh.point_cloud_display = None
    bpy.types.SpaceView3D.draw_handler_remove(render_hook, 'WINDOW')
    
if __name__ == "__main__":
    register()
