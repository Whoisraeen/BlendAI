bl_info = {
    "name": "BlendAI",
    "author": "Raeen",
    "version": (2, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > BlendAI",
    "description": "AI-powered 3D content generation using OpenAI GPT, Anthropic Claude, Google Gemini, and Local LLMs",
    "category": "Development",
    "doc_url": "https://github.com/your-repo/blendai",
    "tracker_url": "https://github.com/your-repo/blendai/issues",
}

import bpy
from . import operators, panels, preferences

def register():
    # Register preferences first
    bpy.utils.register_class(preferences.AICodePreferences)
    
    # Register operators
    operators.register()
    
    # Register panels
    panels.register()

def unregister():
    # Unregister in reverse order
    panels.unregister()
    operators.unregister()
    bpy.utils.unregister_class(preferences.AICodePreferences)

if __name__ == "__main__":
    register()
