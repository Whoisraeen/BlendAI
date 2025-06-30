import bpy
from .ai_client import AIClient
from .code_executor import CodeExecutor

# You may want these as singletons in __init__.py, but we'll instantiate here for clarity
ai_client = AIClient()
code_executor = CodeExecutor()

class AI_OT_GenerateCode(bpy.types.Operator):
    """Generate Python code from a natural prompt using AI"""
    bl_idname = "ai.generate_code"
    bl_label = "Generate AI Python Code"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        prompt = scene.ai_prompt

        # Ensure prompt exists
        if not prompt or not prompt.strip():
            self.report({'ERROR'}, "Please enter a prompt.")
            return {'CANCELLED'}

        # Get AI provider from preferences
        addon_prefs = context.preferences.addons[__package__].preferences
        provider = addon_prefs.ai_provider
        
        # Check if API key is configured for the selected provider
        api_key = None
        if provider == 'openai':
            api_key = addon_prefs.openai_api_key
        elif provider == 'anthropic':
            api_key = addon_prefs.anthropic_api_key
        elif provider == 'gemini':
            api_key = addon_prefs.gemini_api_key
        # Local doesn't need API key
        
        if provider != 'local' and (not api_key or not api_key.strip()):
            self.report({'ERROR'}, f"Please configure your {provider.upper()} API key in preferences.")
            return {'CANCELLED'}

        try:
            # Set AI client backend
            ai_client.backend = provider
            
            # Generate code using AI
            self.report({'INFO'}, f"🤖 Generating code using {provider.upper()}...")
            generated_code = ai_client.generate_code(prompt)
            
            if not generated_code or not generated_code.strip():
                self.report({'ERROR'}, "AI generated empty code. Please try rephrasing your prompt.")
                return {'CANCELLED'}
            
            # Store the generated code in scene
            scene.ai_generated_code = generated_code
            
            # Show success message with provider info
            model_name = "Unknown"
            if provider == 'openai':
                model_name = addon_prefs.openai_model
            elif provider == 'anthropic':
                model_name = addon_prefs.anthropic_model
            elif provider == 'gemini':
                model_name = addon_prefs.gemini_model
            elif provider == 'local':
                model_name = addon_prefs.local_model
            
            self.report({'INFO'}, f"✅ Code generated successfully using {provider.upper()} ({model_name})")
            
            # Auto-execute if enabled in preferences
            if hasattr(addon_prefs, 'auto_execute_code') and addon_prefs.auto_execute_code:
                return bpy.ops.ai.execute_code()
            
            return {'FINISHED'}

        except Exception as e:
            error_msg = str(e)
            
            # Provide more specific error messages
            if "API key" in error_msg:
                self.report({'ERROR'}, f"❌ API Key Error: {error_msg}")
            elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
                self.report({'ERROR'}, f"💳 Billing/Quota Error: {error_msg}")
            elif "timeout" in error_msg.lower():
                self.report({'ERROR'}, "⏱️ Request timed out. Please try again.")
            elif "connection" in error_msg.lower():
                self.report({'ERROR'}, "🌐 Connection error. Check your internet connection.")
            else:
                self.report({'ERROR'}, f"❌ AI Error: {error_msg}")
            
            return {'CANCELLED'}

class AI_OT_ExecuteCode(bpy.types.Operator):
    """Execute the generated AI code safely"""
    bl_idname = "ai.execute_code"
    bl_label = "Execute AI Code"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        code = scene.ai_generated_code

        if not code or not code.strip():
            self.report({'ERROR'}, "No code to execute. Generate code first.")
            return {'CANCELLED'}

        try:
            # Execute the code safely
            self.report({'INFO'}, "🚀 Executing AI-generated code...")
            success, message, output = code_executor.execute_code(code)
            
            if success:
                self.report({'INFO'}, "✅ Code executed successfully!")
                
                # Show diff summary if enabled
                addon_prefs = context.preferences.addons[__package__].preferences
                if addon_prefs.enable_diff_summary:
                    diff_summary = ai_client.get_diff_summary()
                    if diff_summary and diff_summary != "No significant changes detected.":
                        # Store diff summary for display in UI
                        scene.ai_diff_summary = diff_summary
                        
                        # Show brief summary in status
                        lines = diff_summary.split('\n')
                        if len(lines) > 1:
                            summary_line = f"Changes: {len(lines)-1} operations"
                        else:
                            summary_line = "Scene modified"
                        self.report({'INFO'}, f"📊 {summary_line}")
                
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"❌ Execution failed: {message}")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"❌ Execution error: {str(e)}")
            return {'CANCELLED'}

class AI_OT_ClearCode(bpy.types.Operator):
    """Clear the generated code and diff summary"""
    bl_idname = "ai.clear_code"
    bl_label = "Clear Code"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        scene.ai_generated_code = ""
        scene.ai_diff_summary = ""
        scene.ai_prompt = ""
        self.report({'INFO'}, "🧹 Cleared code and prompt")
        return {'FINISHED'}

class AI_OT_RefineCode(bpy.types.Operator):
    """Refine the generated code based on user feedback"""
    bl_idname = "ai.refine_code"
    bl_label = "Refine Code"
    bl_options = {'REGISTER', 'UNDO'}

    feedback: bpy.props.StringProperty(
        name="Feedback",
        description="Feedback for refining the code",
        default=""
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "feedback")

    def execute(self, context):
        scene = context.scene
        
        if not scene.ai_generated_code or not scene.ai_generated_code.strip():
            self.report({'ERROR'}, "No code to refine. Generate code first.")
            return {'CANCELLED'}
        
        if not self.feedback or not self.feedback.strip():
            self.report({'ERROR'}, "Please provide feedback for refinement.")
            return {'CANCELLED'}

        try:
            # Get AI provider from preferences
            addon_prefs = context.preferences.addons[__package__].preferences
            provider = addon_prefs.ai_provider
            
            # Create refinement prompt
            refinement_prompt = (
                f"The previous code generated was:\n```python\n{scene.ai_generated_code}\n```\n\n"
                f"User feedback: {self.feedback}\n\n"
                f"Please generate improved code that addresses this feedback. "
                f"Original request: {scene.ai_prompt}"
            )
            
            # Set AI client backend
            ai_client.backend = provider
            
            # Generate refined code
            self.report({'INFO'}, f"🔄 Refining code using {provider.upper()}...")
            refined_code = ai_client.generate_code(refinement_prompt)
            
            if not refined_code or not refined_code.strip():
                self.report({'ERROR'}, "AI generated empty refined code.")
                return {'CANCELLED'}
            
            # Update the generated code
            scene.ai_generated_code = refined_code
            
            self.report({'INFO'}, "✅ Code refined successfully!")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"❌ Refinement failed: {str(e)}")
            return {'CANCELLED'}

class AI_OT_SaveCode(bpy.types.Operator):
    """Save the generated code to a .py file"""
    bl_idname = "ai.save_code"
    bl_label = "Save Code"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Path to save the code file",
        default="blendai_generated.py",
        subtype='FILE_PATH'
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        scene = context.scene
        code = scene.ai_generated_code

        if not code or not code.strip():
            self.report({'ERROR'}, "No code to save. Generate code first.")
            return {'CANCELLED'}

        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                # Add header comment
                f.write("# BlendAI Generated Code\n")
                f.write(f"# Prompt: {scene.ai_prompt}\n")
                f.write("# Generated by BlendAI addon\n\n")
                f.write("import bpy\n\n")
                f.write(code)
            
            self.report({'INFO'}, f"💾 Code saved to: {self.filepath}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"❌ Save failed: {str(e)}")
            return {'CANCELLED'}

# Register scene properties
def register_properties():
    bpy.types.Scene.ai_prompt = bpy.props.StringProperty(
        name="AI Prompt",
        description="Describe what you want to create or modify in Blender",
        default="",
        maxlen=1000
    )
    
    bpy.types.Scene.ai_generated_code = bpy.props.StringProperty(
        name="Generated Code",
        description="AI-generated Python code",
        default=""
    )
    
    bpy.types.Scene.ai_diff_summary = bpy.props.StringProperty(
        name="Diff Summary",
        description="Summary of changes made to the scene",
        default=""
    )

def unregister_properties():
    del bpy.types.Scene.ai_prompt
    del bpy.types.Scene.ai_generated_code
    del bpy.types.Scene.ai_diff_summary

# Classes to register
classes = [
    AI_OT_GenerateCode,
    AI_OT_ExecuteCode,
    AI_OT_ClearCode,
    AI_OT_RefineCode,
    AI_OT_SaveCode,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_properties()

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    unregister_properties()

