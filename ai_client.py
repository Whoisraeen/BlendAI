import bpy
import requests
import json
import time
import base64
import os
import tempfile
from mathutils import Vector
from bpy.props import StringProperty

class AIBackendError(Exception):
    pass

class AIClient:
    def __init__(self, backend='openai'):
        self.backend = backend
        self.response_log = []
        self.previous_scene_state = None
        self._max_context_tokens = {
            'openai': 128000,  # GPT-4 context limit
            'anthropic': 200000,  # Claude context limit
            'gemini': 1000000,  # Gemini context limit
            'local': 32000  # Conservative default for local models
        }

    def sync_backend_with_prefs(self):
        """Ensure backend is in sync with user preferences"""
        try:
            addon_prefs = bpy.context.preferences.addons[__package__].preferences
            preferred_backend = addon_prefs.ai_provider.lower()
            if preferred_backend != self.backend:
                self.backend = preferred_backend
        except Exception as e:
            print(f"Warning: Could not sync backend with preferences: {e}")
    
    def get_api_key(self):
        """Securely get API key from Blender's preferences"""
        try:
            addon_prefs = bpy.context.preferences.addons[__package__].preferences
            if self.backend == 'openai':
                return addon_prefs.openai_api_key
            elif self.backend == 'anthropic':
                return addon_prefs.anthropic_api_key
            elif self.backend == 'gemini':
                return addon_prefs.gemini_api_key
            elif self.backend == 'local':
                return "local"  # Local doesn't need API key
            else:
                raise AIBackendError(f"Unknown backend: {self.backend}")
        except Exception as e:
            raise AIBackendError(f"Failed to retrieve API key for {self.backend}: {str(e)}")

    def map_model_name(self, model_name, backend):
        """Map internal model names to API model names"""
        # OpenAI model mapping
        if backend == 'openai':
            model_map = {
                'gpt-4.1': 'gpt-4.1-2025-04-14',
                'gpt-4.1-mini': 'gpt-4.1-mini-2025-04-14', 
                'gpt-4.1-nano': 'gpt-4.1-nano-2025-04-14',
                'o3': 'o3-2025-01-31',
                'o3-mini': 'o3-mini-2025-01-31',
                'o4-mini': 'o4-mini-2025-01-31',
                'gpt-4o': 'gpt-4o-2024-11-20',
                'gpt-4o-mini': 'gpt-4o-mini-2024-07-18',
                'o1': 'o1-preview-2024-09-12',
                'o1-mini': 'o1-mini-2024-09-12'
            }
            return model_map.get(model_name, model_name)
            
        # Anthropic model mapping  
        elif backend == 'anthropic':
            model_map = {
                'claude-4-opus': 'claude-opus-4-20250514',
                'claude-4-sonnet': 'claude-sonnet-4-20250514',
                'claude-3.7-sonnet': 'claude-3-7-sonnet-20250219',
                'claude-3.5-sonnet': 'claude-3-5-sonnet-20241022',
                'claude-3.5-haiku': 'claude-3-5-haiku-20241022',
                'claude-3-opus': 'claude-3-opus-20240229',
                'claude-3-sonnet': 'claude-3-sonnet-20240229',
                'claude-3-haiku': 'claude-3-haiku-20240307'
            }
            return model_map.get(model_name, model_name)
            
        # Gemini model mapping
        elif backend == 'gemini':
            model_map = {
                'gemini-2.5-pro': 'gemini-2.5-pro',
                'gemini-2.5-flash': 'gemini-2.5-flash',
                'gemini-2.5-flash-lite': 'gemini-2.5-flash-lite-preview-06-17',
                'gemini-2.0-flash': 'gemini-2.0-flash-001',
                'gemini-2.0-flash-lite': 'gemini-2.0-flash-lite-001',
                'gemini-1.5-pro': 'gemini-1.5-pro-latest',
                'gemini-1.5-flash': 'gemini-1.5-flash-latest',
                'gemini-1.5-flash-8b': 'gemini-1.5-flash-8b-latest'
            }
            return model_map.get(model_name, model_name)
            
        return model_name

    def capture_viewport_screenshot(self):
        """Capture a screenshot of the 3D viewport and return base64 encoded image"""
        try:
            addon_prefs = bpy.context.preferences.addons[__package__].preferences
            resolution = int(addon_prefs.max_screenshot_resolution)
            
            # Save current render settings
            scene = bpy.context.scene
            render = scene.render
            original_resolution_x = render.resolution_x
            original_resolution_y = render.resolution_y
            original_filepath = render.filepath
            
            # Set screenshot resolution
            render.resolution_x = resolution
            render.resolution_y = resolution
            
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            screenshot_path = os.path.join(temp_dir, "blendai_viewport.png")
            render.filepath = screenshot_path
            
            # Take screenshot
            bpy.ops.render.opengl(write_still=True)
            
            # Restore original settings
            render.resolution_x = original_resolution_x
            render.resolution_y = original_resolution_y
            render.filepath = original_filepath
            
            # Read and encode image
            if os.path.exists(screenshot_path):
                with open(screenshot_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                    os.remove(screenshot_path)  # Clean up
                    return encoded_image
                    
        except Exception as e:
            print(f"Error capturing viewport screenshot: {e}")
            
        return None

    def estimate_token_count(self, text):
        """Rough estimation of token count (approximately 4 characters per token)"""
        return len(text) // 4
    
    def trim_context_if_needed(self, context, max_tokens):
        """Trim context to fit within token limits while preserving essential information"""
        # Always preserve essential context
        essential_keys = ['scene_name', 'mode', 'blender_version', 'render_engine', 
                         'selected_objects', 'active_object', 'total_objects']
        
        # Start with essential context
        trimmed_context = {key: context[key] for key in essential_keys if key in context}
        
        # Add other context items if space allows
        optional_keys = ['all_objects', 'materials', 'lights', 'cameras', 'collections']
        
        for key in optional_keys:
            if key in context:
                # Limit large lists to prevent token overflow
                if key == 'all_objects' and len(context[key]) > 50:
                    trimmed_context[key] = context[key][:50]  # Limit to 50 objects
                elif key == 'materials' and len(context[key]) > 20:
                    trimmed_context[key] = context[key][:20]  # Limit to 20 materials
                else:
                    trimmed_context[key] = context[key]
        
        return trimmed_context
    
    def get_detailed_scene_context(self, trim_for_backend=None):
        """Get comprehensive scene context including all objects, materials, etc."""
        scene = bpy.context.scene
        context = {
            'scene_name': scene.name if scene else None,
            'selected_objects': [],
            'active_object': None,
            'all_objects': [],
            'total_objects': len(bpy.data.objects),
            'materials': [],
            'lights': [],
            'cameras': [],
            'collections': [],
            'mode': bpy.context.mode,
            'blender_version': f"{bpy.app.version[0]}.{bpy.app.version[1]}.{bpy.app.version[2]}",
            'render_engine': scene.render.engine if scene else None,
            'frame_current': scene.frame_current if scene else None,
            'frame_range': f"{scene.frame_start}-{scene.frame_end}" if scene else None
        }
        
        # Selected objects with detailed info
        for obj in bpy.context.selected_objects:
            obj_info = {
                'name': obj.name,
                'type': obj.type,
                'location': [round(x, 3) for x in obj.location],
                'rotation': [round(x, 3) for x in obj.rotation_euler],
                'scale': [round(x, 3) for x in obj.scale]
            }
            
            if obj.type == 'MESH' and obj.data:
                obj_info.update({
                    'vertices': len(obj.data.vertices),
                    'edges': len(obj.data.edges),
                    'faces': len(obj.data.polygons),
                    'materials': [mat.name for mat in obj.data.materials if mat]
                })
                
            context['selected_objects'].append(obj_info)
        
        # Active object
        if bpy.context.active_object:
            context['active_object'] = bpy.context.active_object.name
            
        # All objects summary
        for obj in bpy.data.objects:
            obj_summary = {
                'name': obj.name,
                'type': obj.type,
                'visible': obj.visible_get(),
                'location': [round(x, 3) for x in obj.location]
            }
            context['all_objects'].append(obj_summary)
            
        # Materials
        for mat in bpy.data.materials:
            mat_info = {
                'name': mat.name,
                'use_nodes': mat.use_nodes,
                'users': mat.users
            }
            context['materials'].append(mat_info)
            
        # Lights
        context['lights'] = [
            {'name': obj.name, 'type': obj.data.type, 'energy': obj.data.energy}
            for obj in bpy.data.objects if obj.type == 'LIGHT'
        ]
        
        # Cameras
        context['cameras'] = [
            {'name': obj.name, 'lens': obj.data.lens}
            for obj in bpy.data.objects if obj.type == 'CAMERA'
        ]
        
        # Collections
        context['collections'] = [
            {'name': col.name, 'objects': len(col.objects)}
            for col in bpy.data.collections
        ]
        
        # Apply token management if backend specified
        if trim_for_backend and trim_for_backend in self._max_context_tokens:
            max_tokens = self._max_context_tokens[trim_for_backend] // 4  # Reserve 3/4 for response
            context = self.trim_context_if_needed(context, max_tokens)
        
        return context

    def build_prompt(self, user_request):
        """Build comprehensive prompt with scene context and optional screenshot"""
        # Sync backend with preferences before building prompt
        self.sync_backend_with_prefs()
        
        context = self.get_detailed_scene_context(trim_for_backend=self.backend)
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        
        # Enhanced system prompt
        system_prompt = (
            "You are BlendAI, an expert Blender Python (bpy) code generator specialized in creating high-quality 3D content.\n"
            "You have deep knowledge of Blender's API, best practices, and 3D modeling workflows.\n\n"
            "CORE RULES:\n"
            "1. Generate ONLY clean, executable Python code using the Blender API (bpy)\n"
            "2. Include comprehensive error handling with try-except blocks\n" 
            "3. Add clear, helpful comments explaining each step\n"
            "4. Ensure code is safe and won't crash Blender\n"
            "5. Use proper Blender conventions and best practices\n"
            "6. Do NOT include markdown, explanations, or anything except Python code\n"
            "7. Test for object existence before manipulating\n"
            "8. Use appropriate selection and active object management\n\n"
            "DETAILED SCENE CONTEXT:\n"
            f"Scene: '{context['scene_name']}' | Mode: {context['mode']} | Blender: {context['blender_version']}\n"
            f"Render Engine: {context['render_engine']} | Frame: {context['frame_current']} ({context['frame_range']})\n\n"
        )
        
        # Selected Objects Details
        if context['selected_objects']:
            system_prompt += "SELECTED OBJECTS:\n"
            for obj in context['selected_objects']:
                system_prompt += f"• {obj['name']} ({obj['type']})\n"
                system_prompt += f"  Location: {obj['location']}, Rotation: {obj['rotation']}, Scale: {obj['scale']}\n"
                if 'vertices' in obj:
                    system_prompt += f"  Mesh: {obj['vertices']} verts, {obj['faces']} faces\n"
                if obj.get('materials'):
                    system_prompt += f"  Materials: {', '.join(obj['materials'])}\n"
        else:
            system_prompt += "SELECTED OBJECTS: None\n"
            
        # Active Object
        system_prompt += f"ACTIVE OBJECT: {context['active_object'] or 'None'}\n\n"
        
        # Scene Statistics
        system_prompt += "SCENE OVERVIEW:\n"
        object_types = {}
        for obj in context['all_objects']:
            obj_type = obj['type']
            object_types[obj_type] = object_types.get(obj_type, 0) + 1
            
        for obj_type, count in object_types.items():
            system_prompt += f"• {obj_type}: {count}\n"
            
        system_prompt += f"• Total Objects: {context['total_objects']}\n"
        system_prompt += f"• Materials: {len(context['materials'])}\n"
        system_prompt += f"• Collections: {len(context['collections'])}\n\n"
        
        # Collections Info
        if context['collections']:
            system_prompt += "COLLECTIONS:\n"
            for col in context['collections']:
                system_prompt += f"• {col['name']}: {col['objects']} objects\n"
            system_prompt += "\n"
            
        # Materials Info
        if context['materials']:
            system_prompt += "MATERIALS:\n"
            for mat in context['materials'][:10]:  # Limit to first 10
                system_prompt += f"• {mat['name']} (nodes: {mat['use_nodes']}, users: {mat['users']})\n"
            if len(context['materials']) > 10:
                system_prompt += f"• ... and {len(context['materials']) - 10} more materials\n"
            system_prompt += "\n"
            
        # User Request
        system_prompt += f"USER REQUEST:\n{user_request}\n\n"
        
        system_prompt += (
            "Generate Python code that fulfills this request. The code should:\n"
            "- Work with the current scene context\n"
            "- Be production-ready and efficient\n"
            "- Include error handling and validation\n"
            "- Follow Blender best practices\n"
            "- Return ONLY executable Python code\n"
        )
        
        # Add screenshot if enabled
        screenshot_data = None
        if addon_prefs.enable_viewport_screenshot:
            screenshot_data = self.capture_viewport_screenshot()
            if screenshot_data:
                system_prompt += "\n[VIEWPORT SCREENSHOT INCLUDED - Use this visual context to better understand the current scene]\n"
        
        return system_prompt, screenshot_data

    def store_scene_state(self):
        """Store current scene state for diff comparison"""
        self.previous_scene_state = {
            'objects': [obj.name for obj in bpy.data.objects],
            'materials': [mat.name for mat in bpy.data.materials],
            'collections': [col.name for col in bpy.data.collections],
            'selected': [obj.name for obj in bpy.context.selected_objects],
            'active': bpy.context.active_object.name if bpy.context.active_object else None
        }

    def get_diff_summary(self):
        """Generate a summary of changes since last operation"""
        if not self.previous_scene_state:
            return "No previous state to compare."
            
        current_state = {
            'objects': [obj.name for obj in bpy.data.objects],
            'materials': [mat.name for mat in bpy.data.materials],
            'collections': [col.name for col in bpy.data.collections],
            'selected': [obj.name for obj in bpy.context.selected_objects],
            'active': bpy.context.active_object.name if bpy.context.active_object else None
        }
        
        changes = []
        
        # Objects
        added_objects = set(current_state['objects']) - set(self.previous_scene_state['objects'])
        removed_objects = set(self.previous_scene_state['objects']) - set(current_state['objects'])
        
        if added_objects:
            changes.append(f"✅ Added objects: {', '.join(added_objects)}")
        if removed_objects:
            changes.append(f"❌ Removed objects: {', '.join(removed_objects)}")
            
        # Materials
        added_materials = set(current_state['materials']) - set(self.previous_scene_state['materials'])
        if added_materials:
            changes.append(f"🎨 Added materials: {', '.join(added_materials)}")
            
        # Collections
        added_collections = set(current_state['collections']) - set(self.previous_scene_state['collections'])
        if added_collections:
            changes.append(f"📁 Added collections: {', '.join(added_collections)}")
            
        # Selection changes
        if current_state['selected'] != self.previous_scene_state['selected']:
            if current_state['selected']:
                changes.append(f"🎯 Selected: {', '.join(current_state['selected'])}")
            else:
                changes.append("🎯 Selection cleared")
                
        # Active object changes
        if current_state['active'] != self.previous_scene_state['active']:
            if current_state['active']:
                changes.append(f"🎯 Active object: {current_state['active']}")
            else:
                changes.append("🎯 No active object")
        
        if not changes:
            return "No significant changes detected."
            
        return "CHANGES SUMMARY:\n" + "\n".join(changes)

    def call_openai(self, prompt, screenshot_data=None, **kwargs):
        """Call OpenAI API with enhanced support and error handling"""
        try:
            api_key = self.get_api_key()
            if not api_key:
                raise AIBackendError("OpenAI API key not set in preferences")
            
            addon_prefs = bpy.context.preferences.addons[__package__].preferences
            model = self.map_model_name(kwargs.get('model', addon_prefs.openai_model), 'openai')
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Build messages
            messages = [{"role": "user", "content": prompt}]
            
            # Add screenshot if available (for vision models)
            if screenshot_data and model in ['gpt-4o', 'gpt-4o-mini', 'gpt-4o-2024-11-20', 'gpt-4o-mini-2024-07-18']:
                messages = [{
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_data}"}}
                    ]
                }]
                print(f"OpenAI: Including viewport screenshot for vision model {model}")
            
            data = {
                "model": model,
                "messages": messages,
                "max_tokens": kwargs.get('max_tokens', 4000),
                "temperature": kwargs.get('temperature', 0.1)
            }
            
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            if 'choices' in result and result['choices']:
                return result['choices'][0]['message']['content']
            elif 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                raise AIBackendError(f"OpenAI API error: {error_msg}")
            else:
                raise AIBackendError("OpenAI API returned no choices in response")
                
        except requests.exceptions.Timeout:
            raise AIBackendError("OpenAI API request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            raise AIBackendError("Failed to connect to OpenAI API. Check your internet connection.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AIBackendError("Invalid OpenAI API key. Please check your API key in preferences.")
            elif e.response.status_code == 429:
                raise AIBackendError("OpenAI API rate limit exceeded. Please wait and try again.")
            elif e.response.status_code == 400:
                raise AIBackendError("Invalid request to OpenAI API. Check your model selection and parameters.")
            else:
                raise AIBackendError(f"OpenAI API HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise AIBackendError(f"Unexpected error calling OpenAI API: {str(e)}")

    def call_anthropic(self, prompt, screenshot_data=None, **kwargs):
        """Call Anthropic API with enhanced support and error handling"""
        try:
            api_key = self.get_api_key()
            if not api_key:
                raise AIBackendError("Anthropic API key not set in preferences")
                
            addon_prefs = bpy.context.preferences.addons[__package__].preferences
            model = self.map_model_name(kwargs.get('model', addon_prefs.anthropic_model), 'anthropic')
            
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Build content
            content = [{"type": "text", "text": prompt}]
            
            # Add screenshot if available
            if screenshot_data:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_data
                    }
                })
                print(f"Anthropic: Including viewport screenshot for enhanced context understanding")
            
            data = {
                "model": model,
                "max_tokens": kwargs.get('max_tokens', 4000),
                "temperature": kwargs.get('temperature', 0.1),
                "messages": [{"role": "user", "content": content}]
            }
            
            # Add thinking budget for supported models
            if any(x in model for x in ['claude-4', 'claude-3-7', 'claude-3.7']):
                thinking_budget = getattr(addon_prefs, 'thinking_budget', 'auto')
                if thinking_budget != 'auto':
                    thinking_map = {
                        'low': 2000,
                        'medium': 8000, 
                        'high': 32000,
                        'max': 64000
                    }
                    if thinking_budget in thinking_map:
                        data['max_completion_tokens'] = thinking_map[thinking_budget]
            
            response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            if 'content' in result and result['content']:
                return result['content'][0]['text']
            elif 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                raise AIBackendError(f"Anthropic API error: {error_msg}")
            else:
                raise AIBackendError("Anthropic API returned no content in response")
                
        except requests.exceptions.Timeout:
            raise AIBackendError("Anthropic API request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            raise AIBackendError("Failed to connect to Anthropic API. Check your internet connection.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AIBackendError("Invalid Anthropic API key. Please check your API key in preferences.")
            elif e.response.status_code == 429:
                raise AIBackendError("Anthropic API rate limit exceeded. Please wait and try again.")
            elif e.response.status_code == 400:
                raise AIBackendError("Invalid request to Anthropic API. Check your model selection and parameters.")
            else:
                raise AIBackendError(f"Anthropic API HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise AIBackendError(f"Unexpected error calling Anthropic API: {str(e)}")

    def call_gemini(self, prompt, screenshot_data=None, **kwargs):
        """Call Google Gemini API with enhanced multimodal support"""
        try:
            api_key = self.get_api_key()
            if not api_key:
                raise AIBackendError("Gemini API key not set in preferences")
                
            addon_prefs = bpy.context.preferences.addons[__package__].preferences
            model = self.map_model_name(kwargs.get('model', addon_prefs.gemini_model), 'gemini')
            
            # Build content parts - Gemini supports multimodal input
            parts = [{"text": prompt}]
            
            # Add screenshot if available - Gemini has excellent vision capabilities
            if screenshot_data:
                parts.append({
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": screenshot_data
                    }
                })
                print(f"Gemini: Including viewport screenshot for enhanced context understanding")
            
            data = {
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "temperature": kwargs.get('temperature', 0.1),
                    "maxOutputTokens": kwargs.get('max_tokens', 4000)
                }
            }
            
            # Add thinking configuration for supported models
            if any(x in model for x in ['2.5', '2.0']):
                thinking_budget = getattr(addon_prefs, 'thinking_budget', 'auto')
                if thinking_budget != 'auto':
                    thinking_map = {
                        'low': 2000,
                        'medium': 8000,
                        'high': 32000, 
                        'max': 64000
                    }
                    if thinking_budget in thinking_map:
                        data['generationConfig']['maxOutputTokens'] = thinking_map[thinking_budget]
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            
            response = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            # Enhanced error handling for Gemini responses
            if 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    return candidate['content']['parts'][0]['text']
                else:
                    raise AIBackendError("Gemini API returned malformed response structure")
            elif 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                raise AIBackendError(f"Gemini API error: {error_msg}")
            else:
                raise AIBackendError("Gemini API returned no candidates in response")
                
        except requests.exceptions.Timeout:
            raise AIBackendError("Gemini API request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            raise AIBackendError("Failed to connect to Gemini API. Check your internet connection.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AIBackendError("Invalid Gemini API key. Please check your API key in preferences.")
            elif e.response.status_code == 429:
                raise AIBackendError("Gemini API rate limit exceeded. Please wait and try again.")
            elif e.response.status_code == 400:
                try:
                    error_detail = e.response.json()
                    if 'error' in error_detail:
                        error_msg = error_detail['error'].get('message', 'Bad request')
                        raise AIBackendError(f"Gemini API error: {error_msg}")
                except:
                    pass
                raise AIBackendError("Invalid request to Gemini API. Check your model selection and parameters.")
            else:
                raise AIBackendError(f"Gemini API HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise AIBackendError(f"Unexpected error calling Gemini API: {str(e)}")

    def call_local(self, prompt, **kwargs):
        """Call local LLM server with enhanced error handling"""
        try:
            addon_prefs = bpy.context.preferences.addons[__package__].preferences
            api_url = addon_prefs.local_api_url
            model_name = getattr(addon_prefs, 'local_model', 'local-model')
            
            if not api_url:
                raise AIBackendError("Local API URL not set in preferences")
            
            headers = {"Content-Type": "application/json"}
            
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get('max_tokens', 4000),
                "temperature": kwargs.get('temperature', 0.1)
            }
            
            # Ensure URL ends with /chat/completions
            if not api_url.endswith('/chat/completions'):
                if api_url.endswith('/'):
                    api_url += 'chat/completions'
                else:
                    api_url += '/chat/completions'
            
            response = requests.post(api_url, headers=headers, json=data, timeout=120)  # Longer timeout for local
            response.raise_for_status()
            
            result = response.json()
            
            if 'choices' in result and result['choices']:
                return result['choices'][0]['message']['content']
            elif 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                raise AIBackendError(f"Local API error: {error_msg}")
            else:
                raise AIBackendError("Local API returned no choices in response")
                
        except requests.exceptions.Timeout:
            raise AIBackendError("Local API request timed out. Check if your local server is running and responsive.")
        except requests.exceptions.ConnectionError:
            raise AIBackendError(f"Failed to connect to local API at {api_url}. Check if your local server is running.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise AIBackendError("Local API endpoint not found. Check your API URL configuration.")
            elif e.response.status_code == 500:
                raise AIBackendError("Local API server error. Check your local server logs.")
            else:
                raise AIBackendError(f"Local API HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise AIBackendError(f"Unexpected error calling local API: {str(e)}")

    def generate_code(self, user_request, backend=None, **kwargs):
        """Enhanced code generation with comprehensive context and visual input"""
        # Ensure backend consistency
        if backend:
            self.backend = backend
        else:
            self.sync_backend_with_prefs()
            backend = self.backend
        
        # Store current state for diff
        self.store_scene_state()
        
        # Build enhanced prompt with context
        prompt, screenshot_data = self.build_prompt(user_request)
        
        try:
            # Call appropriate backend with enhanced error handling
            if backend == 'openai':
                response = self.call_openai(prompt, screenshot_data, **kwargs)
            elif backend == 'anthropic':
                response = self.call_anthropic(prompt, screenshot_data, **kwargs)
            elif backend == 'gemini':
                response = self.call_gemini(prompt, screenshot_data, **kwargs)
            elif backend == 'local':
                response = self.call_local(prompt, **kwargs)
            else:
                raise AIBackendError(f"Unsupported backend '{backend}'. Available backends: openai, anthropic, gemini, local")
            
            # Log the interaction
            self.response_log.append({
                'timestamp': time.time(),
                'backend': backend,
                'user_request': user_request,
                'response': response,
                'has_screenshot': screenshot_data is not None,
                'prompt_tokens': self.estimate_token_count(prompt),
                'response_tokens': self.estimate_token_count(response)
            })
            
            return response
            
        except AIBackendError:
            # Re-raise AIBackendError as-is for proper UI display
            raise
        except requests.exceptions.RequestException as e:
            # Network-related errors
            raise AIBackendError(f"Network error with {backend}: {str(e)}")
        except Exception as e:
            # Catch-all for unexpected errors
            raise AIBackendError(f"Unexpected error with {backend}: {str(e)}")

    def get_conversation_history(self, limit=5):
        """Get recent conversation history"""
        recent_logs = self.response_log[-limit:] if self.response_log else []
        history = []
        
        for log in recent_logs:
            timestamp = time.strftime("%H:%M:%S", time.localtime(log['timestamp']))
            history.append({
                'time': timestamp,
                'request': log['user_request'][:100] + "..." if len(log['user_request']) > 100 else log['user_request'],
                'backend': log['backend'],
                'has_screenshot': log['has_screenshot']
            })
            
        return history

