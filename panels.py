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
            
            # Refine feedback input
            if getattr(scene, 'ai_show_refine_input', False):
                refine_box = col.box()
                refine_box.label(text="🔧 Refine Instructions:", icon='MODIFIER')
                refine_box.prop(scene, "ai_refine_feedback", text="", placeholder="Describe what to change or improve...")
                refine_row = refine_box.row(align=True)
                refine_row.operator("ai.apply_refine", text="✓ Apply Refinement", icon='CHECKMARK')
                refine_row.operator("ai.cancel_refine", text="✗ Cancel", icon='CANCEL')
            
            row = col.row(align=True)
            row.operator("ai.regenerate_code", text="🔄 Regenerate", icon='FILE_REFRESH')
            row.operator("ai.copy_code", text="📋 Copy", icon='COPYDOWN')
            
            row = col.row(align=True)
            row.operator("ai.save_code", text="💾 Save", icon='FILE_TEXT')
            row.operator("ai.clear_all", text="🧹 Clear All", icon='TRASH')
        
        # AI Status/Progress indicator
        if hasattr(scene, 'ai_is_generating') and scene.ai_is_generating:
            status_box = layout.box()
            status_box.label(text="🤖 AI is thinking...", icon='TIME')
            # Add a simple progress indicator
            row = status_box.row()
            row.scale_y = 0.5
            row.label(text="● ● ● Processing your request ● ● ●")

        # Quick Settings
        if addon_prefs.enable_viewport_screenshot or addon_prefs.enable_diff_summary:
            col = layout.column()
            box = col.box()
            box.label(text="⚙️ Active Features:", icon='SETTINGS')
            
            if addon_prefs.enable_viewport_screenshot:
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
        
        # Code display and editing
        box = layout.box()
        box.label(text="🐍 Python Code (Editable):", icon='CONSOLE')
        
        # Editable code area
        col = box.column()
        col.prop(scene, "ai_generated_code", text="")
        
        # Statistics
        code_lines = scene.ai_generated_code.split('\n')
        box.label(text=f"📏 {len(code_lines)} lines, {len(scene.ai_generated_code)} characters")
        
        # Quick actions for code
        row = box.row(align=True)
        row.operator("ai.execute_code", text="▶️ Execute", icon='FILE_SCRIPT')
        row.operator("ai.copy_code", text="📋 Copy", icon='COPYDOWN')
        row.operator("ai.save_code", text="💾 Save", icon='FILE_TEXT')

class AI_PT_OutputPanel(bpy.types.Panel):
    """Panel for displaying AI output logs and execution results"""
    bl_label = "Output & Logs"
    bl_idname = "AI_PT_output_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlendAI'
    bl_parent_id = "AI_PT_main_panel"

    @classmethod
    def poll(cls, context):
        # Show if there's any output to display
        scene = context.scene
        return hasattr(scene, 'ai_last_output') and scene.ai_last_output

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        if not hasattr(scene, 'ai_last_output') or not scene.ai_last_output:
            layout.label(text="No output logs yet", icon='INFO')
            return
        
        # Output display in scrollable box
        box = layout.box()
        box.label(text="📋 Execution Output:", icon='CONSOLE')
        
        # Create scrollable area for logs
        output_lines = scene.ai_last_output.split('\n')
        
        # Show recent lines (last 20) in a scrollable format
        scroll_box = box.box()
        scroll_box.scale_y = 0.8  # Make text smaller for more content
        
        # Display output lines with different icons for different types
        for line in output_lines[-20:]:  # Show last 20 lines
            if line.strip():
                row = scroll_box.row()
                row.scale_y = 0.7
                
                # Add icons based on content
                if "ERROR" in line.upper() or "EXCEPTION" in line.upper():
                    row.label(text=line[:80], icon='ERROR')
                elif "WARNING" in line.upper():
                    row.label(text=line[:80], icon='INFO')
                elif "SUCCESS" in line.upper() or "COMPLETED" in line.upper():
                    row.label(text=line[:80], icon='CHECKMARK')
                else:
                    row.label(text=line[:80])
        
        if len(output_lines) > 20:
            box.label(text=f"... showing last 20 of {len(output_lines)} lines")
        
        # Clear output button
        row = box.row()
        row.operator("ai.clear_output", text="🧹 Clear Output", icon='TRASH')

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
    """Help and tips panel with prompt examples"""
    bl_label = "Help & Examples"
    bl_idname = "AI_PT_help_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlendAI'
    bl_parent_id = "AI_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        addon_prefs = context.preferences.addons[__package__].preferences
        
        # Viewport Screenshot Toggle
        if hasattr(addon_prefs, 'enable_viewport_screenshot'):
            box = layout.box()
            box.label(text="📸 Viewport Context:", icon='CAMERA_DATA')
            row = box.row()
            row.prop(addon_prefs, "enable_viewport_screenshot", text="Include Screenshot")
            if addon_prefs.enable_viewport_screenshot:
                box.label(text="✓ AI will see current viewport", icon='CHECKMARK')
        
        # Quick Example Prompts (clickable)
        box = layout.box()
        box.label(text="🎯 Quick Start Examples:", icon='COPYDOWN')
        
        examples = [
            ("Create a red cube at origin", "Create a red cube at (0,0,0) with a metallic material"),
            ("Animate rotation", "Add keyframes to rotate the active object 360 degrees over 60 frames"),
            ("Add subdivision", "Add a subdivision surface modifier to the selected mesh"),
            ("Duplicate in circle", "Duplicate the selected objects in a circle pattern with 8 copies"),
            ("Procedural material", "Create a procedural wood material with noise texture"),
            ("Simple rig", "Create a basic armature rig for the selected mesh")
        ]
        
        for short_desc, full_prompt in examples:
            row = box.row()
            op = row.operator("ai.set_prompt_example", text=f"• {short_desc}")
            op.prompt_text = full_prompt
        
        # Advanced Tips
        box = layout.box()
        box.label(text="💡 Pro Tips:", icon='LIGHTBULB')
        
        tips = [
            "Be specific with coordinates and values",
            "Reference objects by name: 'Cube.001'",
            "Use 'selected objects' or 'active object'",
            "Specify frame ranges for animations",
            "Include material properties and colors",
            "Mention modifiers and their settings"
        ]
        
        for tip in tips:
            row = box.row()
            row.scale_y = 0.8
            row.label(text=f"• {tip}")
        
        # Model Comparison (collapsed by default)
        box = layout.box()
        row = box.row()
        row.prop(scene, "ai_show_model_info", icon='TRIA_DOWN' if getattr(scene, 'ai_show_model_info', False) else 'TRIA_RIGHT', emboss=False)
        row.label(text="🏆 Model Recommendations")
        
        if getattr(scene, 'ai_show_model_info', False):
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
    AI_PT_OutputPanel,
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
