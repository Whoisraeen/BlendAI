import bpy

class AICodePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    
    # API Keys for different providers
    openai_api_key: bpy.props.StringProperty(
        name="OpenAI API Key",
        description="Your OpenAI API key for GPT models",
        default="",
        subtype='PASSWORD'
    )
    
    anthropic_api_key: bpy.props.StringProperty(
        name="Anthropic API Key", 
        description="Your Anthropic API key for Claude models",
        default="",
        subtype='PASSWORD'
    )
    
    gemini_api_key: bpy.props.StringProperty(
        name="Gemini API Key",
        description="Your Google API key for Gemini models",
        default="",
        subtype='PASSWORD'
    )
    
    local_api_url: bpy.props.StringProperty(
        name="Local API URL",
        description="URL for your local LLM server (e.g., http://localhost:1234/v1)",
        default="http://localhost:1234/v1"
    )
    
    # AI Provider Selection
    ai_provider: bpy.props.EnumProperty(
        name="AI Provider",
        description="Choose your preferred AI model provider",
        items=[
            ('openai', 'OpenAI', 'Use OpenAI GPT models'),
            ('anthropic', 'Anthropic', 'Use Anthropic Claude models'),
            ('gemini', 'Google Gemini', 'Use Google Gemini models'),
            ('local', 'Local LLM', 'Use local language model server')
        ],
        default='openai'
    )
    
    # OpenAI Model Selection (Updated 2025)
    openai_model: bpy.props.EnumProperty(
        name="OpenAI Model",
        description="Select OpenAI model to use",
        items=[
            ('gpt-4.1', 'GPT-4.1', 'Latest GPT model with 1M context (April 2025)'),
            ('gpt-4.1-mini', 'GPT-4.1 Mini', 'Faster and cheaper version of GPT-4.1'),
            ('gpt-4.1-nano', 'GPT-4.1 Nano', 'Ultra-fast and cost-effective model'),
            ('o3', 'o3', 'Advanced reasoning model (latest)'),
            ('o3-mini', 'o3-mini', 'Smaller reasoning model'),
            ('o4-mini', 'o4-mini', 'Small but powerful model'),
            ('gpt-4o', 'GPT-4o', 'Multimodal model with vision capabilities'),
            ('gpt-4o-mini', 'GPT-4o Mini', 'Efficient multimodal model'),
            ('o1', 'o1', 'Reasoning model (previous generation)'),
            ('o1-mini', 'o1-mini', 'Smaller reasoning model (previous generation)')
        ],
        default='gpt-4.1'
    )
    
    # Anthropic Model Selection (Updated 2025)
    anthropic_model: bpy.props.EnumProperty(
        name="Anthropic Model",
        description="Select Anthropic Claude model to use",
        items=[
            ('claude-4-opus', 'Claude 4 Opus', 'Most powerful coding model (May 2025)'),
            ('claude-4-sonnet', 'Claude 4 Sonnet', 'High-performance model with reasoning'),
            ('claude-3.7-sonnet', 'Claude 3.7 Sonnet', 'Hybrid reasoning model (Feb 2025)'),
            ('claude-3.5-sonnet', 'Claude 3.5 Sonnet', 'Balanced performance model'),
            ('claude-3.5-haiku', 'Claude 3.5 Haiku', 'Fast and efficient model'),
            ('claude-3-opus', 'Claude 3 Opus', 'Legacy powerful model'),
            ('claude-3-sonnet', 'Claude 3 Sonnet', 'Legacy balanced model'),
            ('claude-3-haiku', 'Claude 3 Haiku', 'Legacy fast model')
        ],
        default='claude-4-sonnet'
    )
    
    # Gemini Model Selection (Updated 2025)
    gemini_model: bpy.props.EnumProperty(
        name="Gemini Model",
        description="Select Google Gemini model to use",
        items=[
            ('gemini-2.5-pro', 'Gemini 2.5 Pro', 'Most advanced with thinking capabilities (June 2025)'),
            ('gemini-2.5-flash', 'Gemini 2.5 Flash', 'Best price-performance with thinking'),
            ('gemini-2.5-flash-lite', 'Gemini 2.5 Flash-Lite', 'Cost-efficient model'),
            ('gemini-2.0-flash', 'Gemini 2.0 Flash', 'Next-gen features and speed'),
            ('gemini-2.0-flash-lite', 'Gemini 2.0 Flash-Lite', 'Cost-efficient 2.0 model'),
            ('gemini-1.5-pro', 'Gemini 1.5 Pro', 'Legacy advanced model'),
            ('gemini-1.5-flash', 'Gemini 1.5 Flash', 'Legacy fast model'),
            ('gemini-1.5-flash-8b', 'Gemini 1.5 Flash-8B', 'Legacy lightweight model')
        ],
        default='gemini-2.5-flash'
    )
    
    # Local Model Name
    local_model: bpy.props.StringProperty(
        name="Local Model Name",
        description="Name of the local model to use (e.g., 'llama3', 'codellama')",
        default="llama3"
    )
    
    # Enhanced Settings
    enable_diff_summary: bpy.props.BoolProperty(
        name="Enable Diff Summary",
        description="Show a summary of changes after code execution",
        default=True
    )
    
    enable_viewport_screenshot: bpy.props.BoolProperty(
        name="Enable Viewport Screenshot",
        description="Include viewport screenshot in AI prompts for better context",
        default=True
    )
    
    max_screenshot_resolution: bpy.props.EnumProperty(
        name="Screenshot Resolution",
        description="Maximum resolution for viewport screenshots",
        items=[
            ('512', '512x512', 'Low resolution, faster processing'),
            ('1024', '1024x1024', 'Medium resolution, balanced'),
            ('2048', '2048x2048', 'High resolution, slower processing')
        ],
        default='1024'
    )
    
    thinking_budget: bpy.props.EnumProperty(
        name="Thinking Budget",
        description="Control how much reasoning the AI should do (for models that support it)",
        items=[
            ('auto', 'Auto', 'Let the model decide based on task complexity'),
            ('low', 'Low', 'Quick responses with minimal thinking'),
            ('medium', 'Medium', 'Balanced thinking and speed'),
            ('high', 'High', 'Deep reasoning for complex tasks'),
            ('max', 'Maximum', 'Extensive reasoning for the most complex tasks')
        ],
        default='auto'
    )

    def draw(self, context):
        layout = self.layout
        
        # Header
        box = layout.box()
        row = box.row()
        row.label(text="🤖 BlendAI Configuration", icon='SETTINGS')
        
        # Provider Selection
        provider_box = layout.box()
        provider_box.label(text="AI Provider Settings:", icon='WORLD')
        provider_box.prop(self, "ai_provider")
        
        # Provider-specific settings
        if self.ai_provider == 'openai':
            # API Key field with visual indicator
            key_row = provider_box.row()
            if not self.openai_api_key or not self.openai_api_key.strip():
                key_row.alert = True
            key_row.prop(self, "openai_api_key")
            
            provider_box.prop(self, "openai_model")
            
            # Show model info
            model_info = {
                'gpt-4.1': '🚀 Latest model with 1M context window',
                'gpt-4.1-mini': '⚡ Fast and efficient',
                'o3': '🧠 Advanced reasoning capabilities',
                'o4-mini': '💡 Small but powerful',
                'gpt-4o': '👁️ Multimodal with vision'
            }
            if self.openai_model in model_info:
                info_row = provider_box.row()
                info_row.label(text=model_info[self.openai_model], icon='INFO')
                
        elif self.ai_provider == 'anthropic':
            # API Key field with visual indicator
            key_row = provider_box.row()
            if not self.anthropic_api_key or not self.anthropic_api_key.strip():
                key_row.alert = True
            key_row.prop(self, "anthropic_api_key")
            
            provider_box.prop(self, "anthropic_model")
            
            # Show model info
            model_info = {
                'claude-4-opus': '🥇 Best coding model worldwide',
                'claude-4-sonnet': '⚡ High-performance with reasoning',
                'claude-3.7-sonnet': '🔄 Hybrid reasoning model',
                'claude-3.5-sonnet': '⚖️ Balanced performance'
            }
            if self.anthropic_model in model_info:
                info_row = provider_box.row()
                info_row.label(text=model_info[self.anthropic_model], icon='INFO')
                
        elif self.ai_provider == 'gemini':
            # API Key field with visual indicator
            key_row = provider_box.row()
            if not self.gemini_api_key or not self.gemini_api_key.strip():
                key_row.alert = True
            key_row.prop(self, "gemini_api_key")
            
            provider_box.prop(self, "gemini_model")
            
            # Show model info  
            model_info = {
                'gemini-2.5-pro': '🧠 Most advanced with thinking',
                'gemini-2.5-flash': '💰 Best price-performance',
                'gemini-2.0-flash': '🚀 Next-gen features',
                'gemini-1.5-pro': '📚 Large context window'
            }
            if self.gemini_model in model_info:
                info_row = provider_box.row()
                info_row.label(text=model_info[self.gemini_model], icon='INFO')
                
        elif self.ai_provider == 'local':
            # API URL field with visual indicator
            url_row = provider_box.row()
            if not self.local_api_url or not self.local_api_url.strip():
                url_row.alert = True
            url_row.prop(self, "local_api_url")
            
            provider_box.prop(self, "local_model")
            
        # Enhanced Features
        features_box = layout.box()
        features_box.label(text="Enhanced Features:", icon='MODIFIER')
        features_box.prop(self, "enable_diff_summary")
        features_box.prop(self, "enable_viewport_screenshot")
        
        if self.enable_viewport_screenshot:
            features_box.prop(self, "max_screenshot_resolution")
            
        # AI Reasoning Settings
        if self.ai_provider in ['gemini', 'anthropic'] and any(x in self.gemini_model or x in self.anthropic_model for x in ['2.5', '4', '3.7']):
            reasoning_box = layout.box()
            reasoning_box.label(text="AI Reasoning:", icon='OUTLINER_OB_LIGHTPROBE')
            reasoning_box.prop(self, "thinking_budget")
            
            if self.thinking_budget != 'auto':
                info_row = reasoning_box.row()
                info_row.label(text="💡 Higher thinking budgets improve quality but increase cost", icon='INFO')
        
        # Status Information
        status_box = layout.box()
        status_box.label(text="Status:", icon='CHECKMARK')
        
        # Check API key
        api_key = ""
        if self.ai_provider == 'openai':
            api_key = self.openai_api_key
        elif self.ai_provider == 'anthropic':
            api_key = self.anthropic_api_key
        elif self.ai_provider == 'gemini':
            api_key = self.gemini_api_key
        elif self.ai_provider == 'local':
            api_key = "local"  # Always show as configured for local
            
        if api_key and api_key.strip():
            status_box.label(text="✅ API configured", icon='CHECKMARK')
            # Add test connection button
            test_row = status_box.row()
            test_row.operator("ai.test_connection", text="Test Connection", icon='PLUGIN')
        else:
            # Enhanced warning for missing API key
            warning_row = status_box.row()
            warning_row.alert = True
            warning_row.label(text="⚠️ API key required for AI functionality", icon='ERROR')
            
            # Provider-specific guidance
            if self.ai_provider == 'openai':
                status_box.label(text="→ Visit platform.openai.com to get your API key")
            elif self.ai_provider == 'anthropic':
                status_box.label(text="→ Visit console.anthropic.com to get your API key")
            elif self.ai_provider == 'gemini':
                status_box.label(text="→ Visit aistudio.google.com to get your API key")
            
        # Quick setup tips
        tips_box = layout.box()
        tips_box.label(text="Quick Setup Tips:", icon='QUESTION')
        if self.ai_provider == 'openai':
            tips_box.label(text="• Get your API key from platform.openai.com")
            tips_box.label(text="• GPT-4.1 offers the best capabilities for 3D modeling")
            tips_box.label(text="• Create an account and navigate to API Keys section")
        elif self.ai_provider == 'anthropic':
            tips_box.label(text="• Get your API key from console.anthropic.com")
            tips_box.label(text="• Claude 4 Opus excels at complex coding tasks")
            tips_box.label(text="• Sign up and go to API Keys in your dashboard")
        elif self.ai_provider == 'gemini':
            tips_box.label(text="• Get your API key from aistudio.google.com")
            tips_box.label(text="• Gemini 2.5 models support advanced reasoning")
            tips_box.label(text="• Create a project and generate an API key")
        elif self.ai_provider == 'local':
            tips_box.label(text="• Ensure your local LLM server is running")
            tips_box.label(text="• Test the URL in your browser first")
            tips_box.label(text="• Common ports: 8080, 11434 (Ollama), 5000")
            
        # Security information
        security_box = layout.box()
        security_box.label(text="🔒 Security & Privacy:", icon='LOCKED')
        security_box.label(text="• API keys are stored locally in Blender preferences")
        security_box.label(text="• Keys are not transmitted except to your chosen AI provider")
        security_box.label(text="• For maximum security, use environment variables")
        if self.ai_provider != 'local':
            security_box.label(text="• Your code prompts are sent to the AI provider for processing")
        else:
            security_box.label(text="• Local models keep all data on your machine")