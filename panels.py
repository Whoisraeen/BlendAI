import bpy

class AI_PT_MainPanel(bpy.types.Panel):
    """Main BlendAI panel in the 3D Viewport sidebar"""
    bl_label = "BlendAI"
    bl_idname = "AI_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlendAI'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        addon_prefs = context.preferences.addons[__package__].preferences

        # Header with current AI provider info
        box = layout.box()
        row = box.row()
        row.label(text="🤖 BlendAI Assistant", icon='RNA')
        
        # Provider status
        provider_info = f"{addon_prefs.ai_provider.upper()}"
        if addon_prefs.ai_provider == 'openai':
            provider_info += f" ({addon_prefs.openai_model})"
        elif addon_prefs.ai_provider == 'anthropic':
            provider_info += f" ({addon_prefs.anthropic_model})"
        elif addon_prefs.ai_provider == 'gemini':
            provider_info += f" ({addon_prefs.gemini_model})"
        elif addon_prefs.ai_provider == 'local':
            provider_info += f" ({addon_prefs.local_model})"
        
        box.label(text=f"Provider: {provider_info}", icon='NETWORK_DRIVE')

        # Input section
        box = layout.box()
        box.label(text="📝 Describe Your Request:", icon='OUTLINER_DATA_FONT')
        box.prop(scene, "ai_prompt", text="", placeholder="Create a cube, apply materials, animate...")

        # Action buttons
        col = box.column()
        row = col.row(align=True)
        row.scale_y = 1.5
        generate_op = row.operator("ai.generate_code", text="🎨 Generate", icon='PLAY')
        
        # Show additional options if code exists
        if scene.ai_generated_code:
            row = col.row(align=True)
            row.operator("ai.execute_code", text="▶️ Execute", icon='FILE_SCRIPT')
            row.operator("ai.refine_code", text="🔧 Refine", icon='MODIFIER')
            
            row = col.row(align=True)
            row.operator("ai.save_code", text="💾 Save", icon='FILE_TEXT')
            row.operator("ai.clear_code", text="🧹 Clear", icon='TRASH')

        # Quick Settings
        if addon_prefs.enable_viewport_screenshots or addon_prefs.enable_diff_summary:
            col = layout.column()
            box = col.box()
            box.label(text="⚙️ Active Features:", icon='SETTINGS')
            
            if addon_prefs.enable_viewport_screenshots:
                box.label(text="📸 Viewport Screenshots: ON", icon='CAMERA_DATA')
            
            if addon_prefs.enable_diff_summary:
                box.label(text="📊 Change Tracking: ON", icon='TRACKING')

class AI_PT_CodePanel(bpy.types.Panel):
    """Panel for displaying and editing generated code"""
    bl_label = "Generated Code"
    bl_idname = "AI_PT_code_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlendAI'
    bl_parent_id = "AI_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        if not scene.ai_generated_code:
            layout.label(text="No code generated yet", icon='INFO')
            return
        
        # Code display
        box = layout.box()
        box.label(text="🐍 Python Code:", icon='CONSOLE')
        
        # Show first few lines of code as preview
        code_lines = scene.ai_generated_code.split('\n')
        preview_lines = code_lines[:8]  # Show first 8 lines
        
        code_box = box.box()
        for line in preview_lines:
            if line.strip():  # Skip empty lines
                code_box.label(text=line[:60] + ("..." if len(line) > 60 else ""))
        
        if len(code_lines) > 8:
            code_box.label(text=f"... and {len(code_lines) - 8} more lines")
        
        # Statistics
        box.label(text=f"📏 {len(code_lines)} lines, {len(scene.ai_generated_code)} characters")

class AI_PT_DiffPanel(bpy.types.Panel):
    """Panel for displaying change summary after code execution"""
    bl_label = "Change Summary"
    bl_idname = "AI_PT_diff_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlendAI'
    bl_parent_id = "AI_PT_main_panel"

    @classmethod
    def poll(cls, context):
        # Only show if diff summary is enabled and exists
        addon_prefs = context.preferences.addons[__package__].preferences
        return addon_prefs.enable_diff_summary and context.scene.ai_diff_summary

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        if not scene.ai_diff_summary:
            return
        
        box = layout.box()
        box.label(text="📊 Scene Changes:", icon='TRACKING')
        
        # Parse and display diff summary
        diff_lines = scene.ai_diff_summary.split('\n')
        
        for line in diff_lines:
            if line.strip():
                if line.startswith('➕'):
                    box.label(text=line, icon='ADD')
                elif line.startswith('➖'):
                    box.label(text=line, icon='REMOVE')
                elif line.startswith('🎨'):
                    box.label(text=line, icon='MATERIAL')
                elif line.startswith('📁'):
                    box.label(text=line, icon='OUTLINER_COLLECTION')
                elif line.startswith('🎯'):
                    box.label(text=line, icon='RESTRICT_SELECT_OFF')
                elif line.startswith('🔍'):
                    box.label(text=line, icon='OBJECT_DATA')
                else:
                    box.label(text=line)

class AI_PT_HelpPanel(bpy.types.Panel):
    """Help and tips panel"""
    bl_label = "Help & Tips"
    bl_idname = "AI_PT_help_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlendAI'
    bl_parent_id = "AI_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        
        # Quick Tips
        box = layout.box()
        box.label(text="💡 Quick Tips:", icon='LIGHTBULB')
        
        tips = [
            "Be specific: 'Create a red cube at (0,0,2)'",
            "Use object names: 'Scale Cube.001 by 2x'", 
            "Include materials: 'Add blue metallic material'",
            "Animation: 'Rotate cube 360° over 60 frames'",
            "Modifiers: 'Add subdivision surface to mesh'",
            "Use 'current selection' for selected objects"
        ]
        
        for tip in tips:
            box.label(text=f"• {tip}")
        
        # Example Prompts
        box = layout.box()
        box.label(text="🎯 Example Prompts:", icon='COPYDOWN')
        
        examples = [
            "Create a material with noise texture",
            "Add keyframes to rotate the active object",  
            "Duplicate selected objects in a circle",
            "Create a simple character rig",
            "Add a particle system with cubes",
            "Generate a procedural landscape"
        ]
        
        for example in examples:
            row = box.row()
            row.label(text=f"• {example}")
        
        # Model Comparison
        box = layout.box()
        box.label(text="🏆 Model Recommendations:", icon='PREFERENCES')
        
        box.label(text="🥇 Best for Coding:")
        box.label(text="   • Claude 3.5 Sonnet (Anthropic)")
        box.label(text="   • GPT-4o (OpenAI)")
        
        box.label(text="🥈 Fastest & Affordable:")
        box.label(text="   • Gemini 2.5 Flash (Google)")
        box.label(text="   • GPT-4o Mini (OpenAI)")
        
        box.label(text="🥉 Most Capable:")
        box.label(text="   • Gemini 2.5 Pro (Google)")
        box.label(text="   • Claude 3 Opus (Legacy)")

# Scene context display panel
class AI_PT_ContextPanel(bpy.types.Panel):
    """Panel showing current scene context that will be sent to AI"""
    bl_label = "Scene Context"
    bl_idname = "AI_PT_context_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlendAI'
    bl_parent_id = "AI_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        
        # Selected objects
        if context.selected_objects:
            box = layout.box()
            box.label(text=f"🎯 Selected ({len(context.selected_objects)}):", icon='RESTRICT_SELECT_OFF')
            
            for obj in context.selected_objects[:5]:  # Show max 5
                row = box.row()
                row.label(text=f"• {obj.type}: {obj.name}")
            
            if len(context.selected_objects) > 5:
                box.label(text=f"... and {len(context.selected_objects) - 5} more")
        
        # Active object
        if context.active_object:
            box = layout.box()
            box.label(text="🔍 Active Object:", icon='OBJECT_DATA')
            obj = context.active_object
            box.label(text=f"• {obj.type}: {obj.name}")
            if obj.type == 'MESH' and obj.data:
                box.label(text=f"• Vertices: {len(obj.data.vertices)}")
                box.label(text=f"• Faces: {len(obj.data.polygons)}")
        
        # Scene overview
        box = layout.box()
        box.label(text="🌍 Scene Overview:", icon='SCENE_DATA')
        box.label(text=f"• Total Objects: {len(bpy.data.objects)}")
        box.label(text=f"• Materials: {len(bpy.data.materials)}")
        box.label(text=f"• Current Mode: {context.mode}")
        box.label(text=f"• Frame: {context.scene.frame_current}")

# Classes to register
classes = [
    AI_PT_MainPanel,
    AI_PT_CodePanel,
    AI_PT_DiffPanel,
    AI_PT_HelpPanel,
    AI_PT_ContextPanel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
