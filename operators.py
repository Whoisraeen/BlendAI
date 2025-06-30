import bpy
import datetime
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
            # Set generation status
            scene.ai_is_generating = True
            
            # Set AI client backend
            ai_client.backend = provider
            
            # Get model name for the selected provider
            model_name = "Unknown"
            model_param = None
            if provider == 'openai':
                model_name = addon_prefs.openai_model
                model_param = model_name
            elif provider == 'anthropic':
                model_name = addon_prefs.anthropic_model
                model_param = model_name
            elif provider == 'gemini':
                model_name = addon_prefs.gemini_model
                model_param = model_name
            elif provider == 'local':
                model_name = addon_prefs.local_model
                model_param = model_name
            
            # Log generation start
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] GENERATION STARTED: {provider.upper()} ({model_name})\nPrompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n"
            if hasattr(scene, 'ai_last_output'):
                scene.ai_last_output += log_entry + "\n"
            
            # Generate code using AI with model parameter
            self.report({'INFO'}, f"🤖 Generating code using {provider.upper()} ({model_name})...")
            generated_code = ai_client.generate_code(prompt, backend=provider, model=model_param)
            
            # Clear generation status
            scene.ai_is_generating = False
            
            if not generated_code or not generated_code.strip():
                # Log failure
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                log_entry = f"[{timestamp}] GENERATION FAILED: Empty code returned\n"
                if hasattr(scene, 'ai_last_output'):
                    scene.ai_last_output += log_entry + "\n"
                
                self.report({'ERROR'}, "AI generated empty code. Please try rephrasing your prompt.")
                return {'CANCELLED'}
            
            # Store the generated code in scene
            scene.ai_generated_code = generated_code
            
            # Log success
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] GENERATION SUCCESS: {len(generated_code)} characters generated\n"
            if hasattr(scene, 'ai_last_output'):
                scene.ai_last_output += log_entry + "\n"
            
            self.report({'INFO'}, f"✅ Code generated successfully using {provider.upper()} ({model_name})")
            
            # Auto-execute if enabled in preferences
            if hasattr(addon_prefs, 'auto_execute_code') and addon_prefs.auto_execute_code:
                return bpy.ops.ai.execute_code()
            
            return {'FINISHED'}

        except Exception as e:
            # Clear generation status on error
            scene.ai_is_generating = False
            
            error_msg = str(e)
            
            # Log the error
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] GENERATION ERROR: {error_msg}\n"
            if hasattr(scene, 'ai_last_output'):
                scene.ai_last_output += log_entry + "\n"
            
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
            
            # Log the execution output
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] Execution {'SUCCESS' if success else 'FAILED'}\n"
            if output:
                log_entry += f"Output: {output}\n"
            if message:
                log_entry += f"Message: {message}\n"
            
            # Append to existing logs
            if hasattr(scene, 'ai_last_output'):
                scene.ai_last_output += log_entry + "\n"
            
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
            error_msg = str(e)
            # Log the error
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] EXCEPTION: {error_msg}\n"
            if hasattr(scene, 'ai_last_output'):
                scene.ai_last_output += log_entry + "\n"
            
            self.report({'ERROR'}, f"❌ Execution error: {error_msg}")
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

class AI_OT_ClearAll(bpy.types.Operator):
    """Clear all AI data including code, logs, and prompts"""
    bl_idname = "ai.clear_all"
    bl_label = "Clear All"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        scene.ai_generated_code = ""
        scene.ai_diff_summary = ""
        scene.ai_prompt = ""
        if hasattr(scene, 'ai_last_output'):
            scene.ai_last_output = ""
        if hasattr(scene, 'ai_refine_feedback'):
            scene.ai_refine_feedback = ""
        if hasattr(scene, 'ai_show_refine_input'):
            scene.ai_show_refine_input = False
        self.report({'INFO'}, "🧹 Cleared all AI data")
        return {'FINISHED'}

class AI_OT_ClearOutput(bpy.types.Operator):
    """Clear the AI output logs"""
    bl_idname = "ai.clear_output"
    bl_label = "Clear Output"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        if hasattr(scene, 'ai_last_output'):
            scene.ai_last_output = ""
        self.report({'INFO'}, "🧹 Cleared output logs")
        return {'FINISHED'}

class AI_OT_SetPromptExample(bpy.types.Operator):
    """Set an example prompt in the input field"""
    bl_idname = "ai.set_prompt_example"
    bl_label = "Set Example Prompt"
    bl_options = {'REGISTER'}
    
    prompt_text: bpy.props.StringProperty(
        name="Prompt Text",
        description="The example prompt to set",
        default=""
    )

    def execute(self, context):
        scene = context.scene
        scene.ai_prompt = self.prompt_text
        self.report({'INFO'}, f"📝 Set example prompt: {self.prompt_text[:50]}...")
        return {'FINISHED'}

class AI_OT_ApplyRefine(bpy.types.Operator):
    """Apply refinement with the provided feedback"""
    bl_idname = "ai.apply_refine"
    bl_label = "Apply Refinement"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        
        if not hasattr(scene, 'ai_refine_feedback') or not scene.ai_refine_feedback.strip():
            self.report({'ERROR'}, "Please provide refinement feedback")
            return {'CANCELLED'}
        
        # Use the existing refine code logic but with the feedback from the scene property
        feedback = scene.ai_refine_feedback
        
        # Hide the refine input
        scene.ai_show_refine_input = False
        
        # Call the refine code operator with the feedback
        bpy.ops.ai.refine_code('INVOKE_DEFAULT', feedback=feedback)
        
        # Clear the feedback
        scene.ai_refine_feedback = ""
        
        return {'FINISHED'}

class AI_OT_CancelRefine(bpy.types.Operator):
    """Cancel the refinement process"""
    bl_idname = "ai.cancel_refine"
    bl_label = "Cancel Refinement"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        scene.ai_show_refine_input = False
        if hasattr(scene, 'ai_refine_feedback'):
            scene.ai_refine_feedback = ""
        self.report({'INFO'}, "❌ Cancelled refinement")
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
        scene = context.scene
        
        # If feedback is provided (from apply_refine), use it directly
        if self.feedback:
            return self.execute(context)
        
        # Otherwise, show the refine input UI in the panel
        scene.ai_show_refine_input = True
        self.report({'INFO'}, "💬 Enter refinement feedback in the panel below")
        return {'FINISHED'}

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
            
            # Get model name for the selected provider
            model_name = "Unknown"
            model_param = None
            if provider == 'openai':
                model_name = addon_prefs.openai_model
                model_param = model_name
            elif provider == 'anthropic':
                model_name = addon_prefs.anthropic_model
                model_param = model_name
            elif provider == 'gemini':
                model_name = addon_prefs.gemini_model
                model_param = model_name
            elif provider == 'local':
                model_name = addon_prefs.local_model
                model_param = model_name
            
            # Generate refined code
            self.report({'INFO'}, f"🔄 Refining code using {provider.upper()} ({model_name})...")
            refined_code = ai_client.generate_code(refinement_prompt, backend=provider, model=model_param)
            
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

class AI_OT_CopyCode(bpy.types.Operator):
    """Copy the generated code to clipboard"""
    bl_idname = "ai.copy_code"
    bl_label = "Copy to Clipboard"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        code = scene.ai_generated_code

        if not code or not code.strip():
            self.report({'ERROR'}, "No code to copy. Generate code first.")
            return {'CANCELLED'}

        try:
            # Copy to clipboard using Blender's built-in functionality
            context.window_manager.clipboard = code
            self.report({'INFO'}, "📋 Code copied to clipboard")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"❌ Copy failed: {str(e)}")
            return {'CANCELLED'}

class AI_OT_RegenerateCode(bpy.types.Operator):
    """Regenerate code with the same prompt for rapid iteration"""
    bl_idname = "ai.regenerate_code"
    bl_label = "Regenerate"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        prompt = scene.ai_prompt

        if not prompt or not prompt.strip():
            self.report({'ERROR'}, "No prompt to regenerate from. Enter a prompt first.")
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
            
            # Get model name for the selected provider
            model_name = "Unknown"
            model_param = None
            if provider == 'openai':
                model_name = addon_prefs.openai_model
                model_param = model_name
            elif provider == 'anthropic':
                model_name = addon_prefs.anthropic_model
                model_param = model_name
            elif provider == 'gemini':
                model_name = addon_prefs.gemini_model
                model_param = model_name
            elif provider == 'local':
                model_name = addon_prefs.local_model
                model_param = model_name
            
            # Regenerate code using AI with model parameter
            self.report({'INFO'}, f"🔄 Regenerating code using {provider.upper()} ({model_name})...")
            generated_code = ai_client.generate_code(prompt, backend=provider, model=model_param)
            
            if not generated_code or not generated_code.strip():
                self.report({'ERROR'}, "AI generated empty code. Please try rephrasing your prompt.")
                return {'CANCELLED'}
            
            # Store the regenerated code in scene
            scene.ai_generated_code = generated_code
            
            self.report({'INFO'}, f"🔄 Code regenerated successfully using {provider.upper()} ({model_name})")
            
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
    
    bpy.types.Scene.ai_last_output = bpy.props.StringProperty(
        name="Last Output",
        description="Last execution output and logs",
        default=""
    )
    
    bpy.types.Scene.ai_refine_feedback = bpy.props.StringProperty(
        name="Refine Feedback",
        description="User feedback for code refinement",
        default=""
    )
    
    bpy.types.Scene.ai_show_refine_input = bpy.props.BoolProperty(
        name="Show Refine Input",
        description="Whether to show the refine input UI",
        default=False
    )
    
    bpy.types.Scene.ai_is_generating = bpy.props.BoolProperty(
        name="AI Is Generating",
        description="Whether AI is currently generating code",
        default=False
    )
    
    bpy.types.Scene.ai_show_model_info = bpy.props.BoolProperty(
        name="Show Model Info",
        description="Whether to show model recommendations",
        default=False
    )

def unregister_properties():
    del bpy.types.Scene.ai_prompt
    del bpy.types.Scene.ai_generated_code
    del bpy.types.Scene.ai_diff_summary
    del bpy.types.Scene.ai_last_output
    del bpy.types.Scene.ai_refine_feedback
    del bpy.types.Scene.ai_show_refine_input
    del bpy.types.Scene.ai_is_generating
    del bpy.types.Scene.ai_show_model_info

class AI_OT_TestConnection(bpy.types.Operator):
    """Test the connection to the selected AI provider"""
    bl_idname = "ai.test_connection"
    bl_label = "Test AI Connection"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        prefs = context.preferences.addons[__name__.split('.')[0]].preferences
        
        # Set generating status
        scene.ai_is_generating = True
        
        # Log test start
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        scene.ai_last_output += f"[{timestamp}] Testing connection to {prefs.ai_provider}...\n"
        
        try:
            # Create a simple test prompt
            test_prompt = "Reply with exactly: 'Connection successful'"
            
            # Get the AI client and test
            response = ai_client.generate_code(test_prompt, context)
            
            if response and "successful" in response.lower():
                scene.ai_last_output += f"[{timestamp}] ✅ Connection test passed\n"
                self.report({'INFO'}, "Connection test successful")
            else:
                scene.ai_last_output += f"[{timestamp}] ⚠️ Connection established but unexpected response\n"
                self.report({'WARNING'}, "Connection established but response was unexpected")
                
        except Exception as e:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            error_msg = str(e)
            scene.ai_last_output += f"[{timestamp}] ❌ Connection test failed: {error_msg}\n"
            
            # Provide helpful error messages
            if "api key" in error_msg.lower():
                self.report({'ERROR'}, "Invalid API key. Please check your configuration.")
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                self.report({'ERROR'}, "Network error. Check your internet connection.")
            elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
                self.report({'ERROR'}, "API quota exceeded or billing issue.")
            else:
                self.report({'ERROR'}, f"Connection failed: {error_msg}")
        
        finally:
            # Clear generating status
            scene.ai_is_generating = False
            
        return {'FINISHED'}

# Classes to register
classes = [
    AI_OT_GenerateCode,
    AI_OT_ExecuteCode,
    AI_OT_ClearCode,
    AI_OT_ClearAll,
    AI_OT_ClearOutput,
    AI_OT_SetPromptExample,
    AI_OT_ApplyRefine,
    AI_OT_CancelRefine,
    AI_OT_RefineCode,
    AI_OT_SaveCode,
    AI_OT_CopyCode,
    AI_OT_RegenerateCode,
    AI_OT_TestConnection,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_properties()

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    unregister_properties()

