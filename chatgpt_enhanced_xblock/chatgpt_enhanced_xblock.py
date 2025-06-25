import os
import re
import pkg_resources
from openai import OpenAI, AuthenticationError
from xblock.core import XBlock
from xblock.fields import Float, Scope, String, List, Integer, Boolean
from xblock.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin


class ChatGPTEnhancedXBlock(StudioEditableXBlockMixin, XBlock):
    """
    An enhanced ChatGPT XBlock with configurable features and smart content awareness.
    
    Features:
    - Configurable reflection prompts
    - Multi-turn conversation control
    - Automatic page content inclusion
    - Video transcript integration
    - Advanced moderation and error handling
    """

    display_name = String(
        display_name="Display Name",
        help="Display name for this module",
        default="ChatGPT Enhanced Assistant",
        scope=Scope.settings,
    )
    
    model_name = String(
        display_name="Model name",
        default="gpt-3.5-turbo",
        scope=Scope.settings,
        help="Select a ChatGPT model.",
        values=[
            {"display_name": "GPT-3.5 Turbo", "value": "gpt-3.5-turbo"},
            {"display_name": "GPT-4", "value": "gpt-4"},
            {"display_name": "GPT-4 Turbo", "value": "gpt-4-turbo"},
            {"display_name": "GPT-4o", "value": "gpt-4o"},
            {"display_name": "GPT-4o Mini", "value": "gpt-4o-mini"},
        ],
    )
    
    api_key = String(
        default="your-openai-api-key-here",
        scope=Scope.settings,
        help="Your OpenAI API key",
    )
    
    description = String(
        default='Enhanced ChatGPT Assistant with smart content awareness',
        scope=Scope.settings,
        help='Description shown to students'
    )

    max_tokens = Integer(
        display_name="Max tokens",
        default=300,
        scope=Scope.settings,
        help="The maximum number of tokens to generate.",
    )

    context_text = String(
        default="You are a helpful teaching assistant. Use the provided course content to give accurate, relevant answers. Reference specific parts of the content when appropriate.",
        scope=Scope.settings,
        help="System prompt to guide the AI's behavior."
    )

    temperature = Float(
        default=0.3,
        scope=Scope.settings,
        help="Controls randomness (0.0-1.0). Lower values make responses more focused and deterministic."
    )
    
    # Enhanced features
    enable_reflection = Boolean(
        display_name="Enable Reflection",
        default=False,
        scope=Scope.settings,
        help="Show reflection prompt after each AI response"
    )
    
    enable_multi_turn = Boolean(
        display_name="Enable Multi-Turn Conversations",
        default=True,
        scope=Scope.settings,
        help="Allow conversation history to build up over multiple exchanges"
    )
    
    max_conversation_length = Integer(
        display_name="Max Conversation Length",
        default=6,
        scope=Scope.settings,
        help="Maximum number of messages to keep in conversation history (affects token usage)"
    )
    
    include_page_content = Boolean(
        display_name="Include Page Content",
        default=True,
        scope=Scope.settings,
        help="Automatically include text content from the current page/unit in context"
    )
    
    include_video_transcripts = Boolean(
        display_name="Include Video Transcripts",
        default=True,
        scope=Scope.settings,
        help="Automatically include video transcripts from the current page in context"
    )
    
    include_vimeo_transcripts = Boolean(
        display_name="Include Vimeo Transcripts",
        default=True,
        scope=Scope.settings,
        help="Automatically extract and include transcripts from embedded Vimeo videos"
    )
    
    max_content_length = Integer(
        display_name="Max Content Length",
        default=2000,
        scope=Scope.settings,
        help="Maximum characters of page content to include (to manage token usage)"
    )

    # Debug mode
    debug_mode = Boolean(
        display_name="Debug Mode",
        default=False,
        scope=Scope.settings,
        help="Show detailed debugging information (NEVER sent to ChatGPT - only for troubleshooting)"
    )

    # Transcript testing mode  
    test_transcript_extraction = Boolean(
        display_name="Test Transcript Extraction",
        default=False,
        scope=Scope.settings,
        help="Run comprehensive transcript extraction testing (debug only - not sent to ChatGPT)"
    )

    # Student-specific fields
    conversation_history = List(
        default=[],
        scope=Scope.user_state,
        help="Keeps track of user and assistant messages for conversation-like experience."
    )

    # Fields that can be edited in Studio
    editable_fields = [
        'display_name', 
        'model_name',
        'api_key',
        'description',
        'context_text',
        'max_tokens',
        'temperature',
        'enable_reflection',
        'enable_multi_turn',
        'max_conversation_length',
        'include_page_content',
        'include_video_transcripts',
        'include_vimeo_transcripts',
        'max_content_length',
        'debug_mode',
        'test_transcript_extraction'
    ]

    def resource_string(self, path):
        """Helper for loading resources from the static folder."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def get_page_content(self):
        """Extract content from the current page/unit (NEVER includes debug info sent to ChatGPT)"""
        if not self.include_page_content:
            return ""
            
        try:
            # Get the parent unit
            parent = self.get_parent()
            if not parent:
                return ""
            
            content_parts = []
            
            # Walk through all children of the unit to collect content
            if hasattr(parent, 'children'):
                for child_id in parent.children:
                    try:
                        child = self.runtime.get_block(child_id)
                        if child and child != self:  # Don't include ourselves
                            # Extract text content from various XBlock types
                            content = self._extract_content_from_xblock(child)
                            if content:
                                content_parts.append(content)
                                
                    except Exception:
                        continue
            
            # Combine and limit content
            combined_content = '\n\n'.join(content_parts)
            if len(combined_content) > self.max_content_length:
                combined_content = combined_content[:self.max_content_length] + "..."
                
            return combined_content
            
        except Exception:
            return ""

    def get_debug_info(self):
        """Get debug information separately - NEVER sent to ChatGPT"""
        if not self.debug_mode:
            return ""
            
        debug_parts = []
        
        try:
            # Get the parent unit
            parent = self.get_parent()
            if not parent:
                debug_parts.append("DEBUG: No parent found")
                return '\n'.join(debug_parts)
            
            debug_parts.append(f"DEBUG: Parent found: {parent.__class__.__name__}, children: {len(parent.children) if hasattr(parent, 'children') else 'no children attr'}")
            
            # Walk through all children of the unit to collect debug info
            if hasattr(parent, 'children'):
                for i, child_id in enumerate(parent.children):
                    try:
                        child = self.runtime.get_block(child_id)
                        if child and child != self:  # Don't include ourselves
                            debug_parts.append(f"DEBUG: Child {i}: {child.__class__.__name__}, category: {getattr(child, 'category', 'no category')}")
                            
                            # Extract text content from various XBlock types
                            content = self._extract_content_from_xblock(child, debug_mode=True)
                            if content:
                                debug_parts.append(f"DEBUG: Extracted content from child {i}: {content[:100]}...")
                            else:
                                debug_parts.append(f"DEBUG: No content extracted from child {i}")
                                
                    except Exception as e:
                        debug_parts.append(f"DEBUG: Error processing child {i}: {str(e)}")
                        continue
            
            # Get the actual content that would be sent to ChatGPT
            page_content = self.get_page_content()
            debug_parts.append(f"DEBUG: Final combined content length: {len(page_content)}")
            debug_parts.append("DEBUG: ACTUAL CONTENT SENT TO CHATGPT:")
            debug_parts.append(page_content)
            
            return '\n'.join(debug_parts)
            
        except Exception as e:
            return f"DEBUG: Exception in get_debug_info: {str(e)}"

    def _extract_content_from_xblock(self, xblock, debug_mode=False):
        """Extract meaningful content from different types of XBlocks"""
        content_parts = []
        
        # Debug mode: show all attributes for video blocks
        if debug_mode and hasattr(xblock, 'category') and xblock.category == 'video':
            debug_attrs = []
            debug_attrs.append(f"VIDEO DEBUG - XBlock type: {type(xblock).__name__}")
            
            # Check common video attributes
            video_attrs_to_check = [
                'transcripts', 'transcript', 'sub', 'available_translations',
                'transcript_language', 'transcript_download_format',
                'video_id', 'youtube_id_1_0', 'html5_sources',
                'data', 'xml_attributes', 'fields'
            ]
            
            for attr in video_attrs_to_check:
                if hasattr(xblock, attr):
                    value = getattr(xblock, attr)
                    debug_attrs.append(f"  {attr}: {repr(value)}")
                else:
                    debug_attrs.append(f"  {attr}: NOT FOUND")
            
            # Check all attributes that might contain transcript info
            all_attrs = [attr for attr in dir(xblock) if not attr.startswith('_')]
            transcript_related = [attr for attr in all_attrs if 'transcript' in attr.lower() or 'sub' in attr.lower()]
            if transcript_related:
                debug_attrs.append(f"  All transcript-related attrs: {transcript_related}")
                for attr in transcript_related:
                    try:
                        value = getattr(xblock, attr)
                        debug_attrs.append(f"    {attr}: {repr(value)}")
                    except Exception as e:
                        debug_attrs.append(f"    {attr}: Error accessing - {e}")
            
            content_parts.append("VIDEO DEBUG INFO:\n" + "\n".join(debug_attrs))
        
        # HTML XBlocks - check for both text content and embedded videos
        if hasattr(xblock, 'data') and xblock.data:
            html_content = str(xblock.data)
            
            # Check for Vimeo embedded videos and extract transcripts
            if self.include_vimeo_transcripts:
                vimeo_transcripts = self._extract_vimeo_transcripts(html_content)
                if vimeo_transcripts:
                    content_parts.append(f"Vimeo video transcripts: {vimeo_transcripts}")
            
            # Extract regular text content
            clean_text = re.sub(r'<[^>]+>', ' ', html_content)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            if clean_text and len(clean_text) > 20:
                content_parts.append(f"Page content: {clean_text}")
        
        # Video XBlocks with transcripts (keeping existing functionality for native video blocks)
        if self.include_video_transcripts and hasattr(xblock, 'category') and xblock.category == 'video':
            transcript_content = self._get_video_transcript_content(xblock)
            if transcript_content:
                content_parts.append(f"Video transcript: {transcript_content}")
            elif debug_mode:
                content_parts.append("VIDEO DEBUG: No transcript content extracted by _get_video_transcript_content")
        
        # Problem XBlocks
        if hasattr(xblock, 'problem_text') and xblock.problem_text:
            content_parts.append(f"Problem content: {xblock.problem_text}")
        elif hasattr(xblock, 'data') and hasattr(xblock, 'category') and xblock.category == 'problem':
            # Extract problem content from problem XBlocks
            problem_content = self._extract_problem_content(xblock)
            if problem_content:
                content_parts.append(f"Problem content: {problem_content}")
            
        return '\n'.join(content_parts)

    def _get_video_transcript_content(self, xblock):
        """Extract actual transcript content from video XBlocks"""
        if not hasattr(xblock, 'category') or xblock.category != 'video':
            return ""
        
        # Always try simple extraction first (using proven working methods)
        transcript_content = self._extract_transcript_simple(xblock)
        
        # If testing mode is enabled, run comprehensive tests and store results separately
        if self.test_transcript_extraction:
            test_results = self._run_comprehensive_transcript_tests(xblock)
            # Store test results separately - they should be shown in debug output, not sent to ChatGPT
            self._transcript_test_results = test_results
        
        return transcript_content

    def _extract_transcript_simple(self, xblock):
        """Simple transcript extraction using proven working methods"""
        try:
            video_id = getattr(xblock, 'edx_video_id', None)
            if not video_id:
                return ""
            
            # METHOD 1 (Primary): Use proven edxval.api.get_video_transcript_data
            try:
                from edxval import api as edxval_api
                
                if hasattr(edxval_api, 'get_video_transcript_data'):
                    transcript_data = edxval_api.get_video_transcript_data(video_id, language_code='en')
                    if transcript_data and 'content' in transcript_data:
                        content = transcript_data['content']
                        if isinstance(content, bytes):
                            content = content.decode('utf-8')
                        parsed_content = self._parse_transcript_content(content)
                        if parsed_content:
                            return parsed_content
            except Exception:
                pass
            
            # METHOD 2 (Secondary): Use proven VideoTranscript model access
            try:
                from edxval.models import VideoTranscript, Video
                
                # Find the Video object
                video_obj = Video.objects.get(edx_video_id=video_id)
                
                # Get transcripts for this video
                transcripts = VideoTranscript.objects.filter(video=video_obj, language_code='en')
                if transcripts.exists():
                    transcript_obj = transcripts.first()
                    
                    # Read the transcript file
                    if hasattr(transcript_obj, 'transcript') and transcript_obj.transcript:
                        transcript_file = transcript_obj.transcript
                        if hasattr(transcript_file, 'read'):
                            content = transcript_file.read()
                            if isinstance(content, bytes):
                                content = content.decode('utf-8')
                            parsed_content = self._parse_transcript_content(content)
                            if parsed_content:
                                return parsed_content
            except Exception:
                pass
            
            # METHOD 3 (Fallback): Try transcripts attribute with file loading (legacy)
            try:
                if hasattr(xblock, 'transcripts') and xblock.transcripts:
                    transcripts_dict = xblock.transcripts
                    lang = getattr(xblock, 'transcript_language', 'en')
                    if lang in transcripts_dict:
                        transcript_filename = transcripts_dict[lang]
                        file_content = self._load_transcript_file(xblock, transcript_filename)
                        if file_content:
                            parsed_content = self._parse_transcript_content(file_content)
                            if parsed_content:
                                return parsed_content
            except Exception:
                pass
            
            # METHOD 4 (Last resort): Try calling transcript() method
            try:
                if hasattr(xblock, 'transcript') and callable(xblock.transcript):
                    from django.http import HttpRequest
                    
                    request = HttpRequest()
                    request.method = 'GET'
                    request.GET = {}
                    request.POST = {}
                    
                    transcript_response = xblock.transcript(request)
                    if transcript_response and hasattr(transcript_response, 'content'):
                        content = transcript_response.content
                        if isinstance(content, bytes):
                            content = content.decode('utf-8')
                        parsed_content = self._parse_transcript_content(content)
                        if parsed_content:
                            return parsed_content
            except Exception:
                pass
            
            return ""
            
        except Exception:
            return ""

    def _run_comprehensive_transcript_tests(self, xblock):
        """Run comprehensive transcript extraction tests and return detailed results"""
        test_results = []
        
        def add_result(method, status, message, content_preview=""):
            test_results.append({
                'method': method,
                'status': status,
                'message': message,
                'content_preview': content_preview[:200] + "..." if len(content_preview) > 200 else content_preview
            })
        
        # METHOD 1: Try calling the transcript() method with proper request
        try:
            if hasattr(xblock, 'transcript'):
                try:
                    # Create a proper Django request-like object
                    from django.http import HttpRequest
                    
                    request = HttpRequest()
                    request.method = 'GET'
                    request.GET = {}
                    request.POST = {}
                    
                    # Try with Django request
                    transcript_response = xblock.transcript(request)
                    if transcript_response and hasattr(transcript_response, 'content'):
                        content = transcript_response.content
                        if isinstance(content, bytes):
                            content = content.decode('utf-8')
                        parsed_content = self._parse_transcript_content(content)
                        add_result("METHOD 1", "✅", "xblock.transcript() with Django request", parsed_content)
                    else:
                        add_result("METHOD 1", "❌", "xblock.transcript() returned empty response")
                        
                except Exception as django_error:
                    # Try with simple mock object
                    try:
                        class SimpleRequest:
                            def __init__(self):
                                self.GET = {}
                                self.POST = {}
                                self.method = 'GET'
                        
                        simple_request = SimpleRequest()
                        transcript_response = xblock.transcript(simple_request)
                        if transcript_response:
                            add_result("METHOD 1", "✅", "xblock.transcript() with simple request", str(transcript_response))
                        else:
                            add_result("METHOD 1", "❌", f"Django request failed: {str(django_error)}")
                    except Exception as simple_error:
                        add_result("METHOD 1", "❌", f"Both request methods failed: {str(simple_error)}")
            else:
                add_result("METHOD 1", "❌", "xblock.transcript() method not available")
        except Exception as e:
            add_result("METHOD 1", "❌", f"METHOD 1 error: {str(e)}")
        
        # METHOD 2: Enhanced file loading with correct API signatures
        try:
            if hasattr(xblock, 'transcripts') and xblock.transcripts:
                add_result("METHOD 2", "✅", f"Found transcripts dict: {xblock.transcripts}")
                
                for lang, filename in xblock.transcripts.items():
                    add_result("METHOD 2", "ℹ️", f"Trying to load transcript file: {filename}")
                    
                    transcript_content = None
                    
                    # Approach 2a: Try correct modulestore API
                    try:
                        from xmodule.modulestore.django import modulestore
                        
                        if hasattr(xblock, 'location'):
                            store = modulestore()
                            course_key = xblock.location.course_key
                            
                            # Try to get the asset directly
                            asset_key = course_key.make_asset_key('asset', filename)
                            try:
                                asset_content = store.find(asset_key)
                                if asset_content and hasattr(asset_content, 'data'):
                                    transcript_content = asset_content.data.decode('utf-8')
                                    parsed_content = self._parse_transcript_content(transcript_content)
                                    add_result("METHOD 2a", "✅", f"Loaded via modulestore.find(): {filename}", parsed_content)
                                    break
                                else:
                                    add_result("METHOD 2a", "❌", f"Asset found but no data: {filename}")
                            except Exception as find_error:
                                add_result("METHOD 2a", "❌", f"modulestore.find() failed: {str(find_error)}")
                                
                    except Exception as modulestore_error:
                        add_result("METHOD 2a", "❌", f"Modulestore access failed: {str(modulestore_error)}")
                    
                    # Approach 2b: Try contentstore access with correct import
                    try:
                        from xmodule.contentstore.content import StaticContent
                        from xmodule.modulestore.django import modulestore
                        
                        if hasattr(xblock, 'location'):
                            course_key = xblock.location.course_key
                            store = modulestore()
                            
                            # Try different asset key formats
                            possible_keys = [
                                course_key.make_asset_key('asset', filename),
                                course_key.make_asset_key('asset', f'transcripts/{filename}'),
                                course_key.make_asset_key('asset', f'subs_{filename}'),
                            ]
                            
                            for asset_key in possible_keys:
                                try:
                                    content = StaticContent.get(asset_key)
                                    if content:
                                        transcript_content = content.data.decode('utf-8')
                                        parsed_content = self._parse_transcript_content(transcript_content)
                                        add_result("METHOD 2b", "✅", f"Loaded via StaticContent: {asset_key}", parsed_content)
                                        break
                                except Exception:
                                    continue
                                    
                            if not transcript_content:
                                add_result("METHOD 2b", "❌", f"StaticContent not found for any key variant")
                                
                    except Exception as content_error:
                        add_result("METHOD 2b", "❌", f"StaticContent access failed: {str(content_error)}")
                    
                    # Approach 2c: Try direct file system access
                    try:
                        import os
                        
                        possible_paths = [
                            f"/openedx/data/transcripts/{filename}",
                            f"/openedx/data/uploads/{filename}",
                            f"/tmp/transcripts/{filename}",
                            f"/edx/var/edxapp/media/transcripts/{filename}",
                        ]
                        
                        for path in possible_paths:
                            if os.path.exists(path):
                                with open(path, 'r', encoding='utf-8') as f:
                                    transcript_content = f.read()
                                    parsed_content = self._parse_transcript_content(transcript_content)
                                    add_result("METHOD 2c", "✅", f"Loaded via filesystem: {path}", parsed_content)
                                    break
                        
                        if not transcript_content:
                            add_result("METHOD 2c", "❌", f"File not found in filesystem")
                            
                    except Exception as fs_error:
                        add_result("METHOD 2c", "❌", f"Filesystem access failed: {str(fs_error)}")
                    
                    if not transcript_content:
                        add_result("METHOD 2", "❌", f"Could not load {filename} via any method")
                    
            else:
                add_result("METHOD 2", "❌", "No transcripts attribute found")
        except Exception as e:
            add_result("METHOD 2", "❌", f"METHOD 2 error: {str(e)}")
        
        # METHOD 3: Enhanced Video API with correct edxval calls
        try:
            video_id = getattr(xblock, 'edx_video_id', None)
            if video_id:
                add_result("METHOD 3", "✅", f"Trying edx_video_id: {video_id}")
                
                # Try actual available edxval functions
                try:
                    from edxval import api as edxval_api
                    
                    # Check what functions are actually available
                    available_functions = [func for func in dir(edxval_api) if 'transcript' in func.lower()]
                    add_result("METHOD 3a", "ℹ️", f"Available edxval functions: {available_functions}")
                    
                    # Try get_video_transcript_data if available
                    if hasattr(edxval_api, 'get_video_transcript_data'):
                        transcript_data = edxval_api.get_video_transcript_data(video_id, language_code='en')
                        if transcript_data:
                            add_result("METHOD 3a", "✅", "Got transcript via get_video_transcript_data", str(transcript_data))
                        else:
                            add_result("METHOD 3a", "❌", "get_video_transcript_data returned empty")
                    
                    # Try get_3rd_party_transcription_plans
                    if hasattr(edxval_api, 'get_3rd_party_transcription_plans'):
                        plans = edxval_api.get_3rd_party_transcription_plans()
                        add_result("METHOD 3a", "ℹ️", f"Transcription plans: {plans}")
                        
                except Exception as api_error:
                    add_result("METHOD 3a", "❌", f"edxval.api exploration failed: {str(api_error)}")
                
                # Try VideoTranscript model with correct field access
                try:
                    from edxval.models import VideoTranscript, Video
                    
                    # First try to find the Video object
                    try:
                        video_obj = Video.objects.get(edx_video_id=video_id)
                        add_result("METHOD 3b", "✅", f"Found Video object: {video_obj}")
                        
                        # Now get transcripts for this video
                        transcripts = VideoTranscript.objects.filter(video=video_obj, language_code='en')
                        if transcripts.exists():
                            transcript_obj = transcripts.first()
                            add_result("METHOD 3b", "✅", f"Found VideoTranscript: format={transcript_obj.file_format}")
                            
                            # Try to read the transcript file
                            if hasattr(transcript_obj, 'transcript') and transcript_obj.transcript:
                                try:
                                    # transcript is a FileField, need to read it properly
                                    transcript_file = transcript_obj.transcript
                                    if hasattr(transcript_file, 'read'):
                                        content = transcript_file.read()
                                        if isinstance(content, bytes):
                                            content = content.decode('utf-8')
                                        parsed_content = self._parse_transcript_content(content)
                                        add_result("METHOD 3b", "✅", f"Read transcript file content", parsed_content)
                                    else:
                                        add_result("METHOD 3b", "❌", f"Transcript file not readable: {type(transcript_file)}")
                                except Exception as read_error:
                                    add_result("METHOD 3b", "❌", f"Error reading transcript file: {str(read_error)}")
                            else:
                                add_result("METHOD 3b", "❌", "VideoTranscript object has no transcript file")
                        else:
                            add_result("METHOD 3b", "❌", "No VideoTranscript objects found")
                            
                    except Video.DoesNotExist:
                        add_result("METHOD 3b", "❌", f"Video object not found for edx_video_id: {video_id}")
                        
                except Exception as model_error:
                    add_result("METHOD 3b", "❌", f"VideoTranscript model access failed: {str(model_error)}")
                    
            else:
                add_result("METHOD 3", "❌", "No edx_video_id found")
        except Exception as e:
            add_result("METHOD 3", "❌", f"METHOD 3 error: {str(e)}")
        
        # METHOD 4: Fixed available_translations() method calls
        try:
            if hasattr(xblock, 'available_translations'):
                try:
                    # Try without parameters first (most likely to work)
                    available_langs = xblock.available_translations()
                    add_result("METHOD 4a", "✅", f"Available translations (no params): {available_langs}")
                    
                    # If successful, try to get content for each language
                    for lang in available_langs:
                        try:
                            # Try various methods to get transcript content by language
                            methods_to_try = [
                                ('get_transcript', lambda: getattr(xblock, 'get_transcript', lambda x: None)(lang)),
                                ('transcript_download_handler', lambda: getattr(xblock, 'transcript_download_handler', lambda x: None)(lang)),
                                ('sub_attr', lambda: getattr(xblock, 'sub', None)),
                            ]
                            
                            for method_name, method_call in methods_to_try:
                                try:
                                    content = method_call()
                                    if content:
                                        add_result("METHOD 4b", "✅", f"Got content via {method_name} for {lang}", str(content)[:200])
                                        break
                                except Exception:
                                    continue
                            else:
                                add_result("METHOD 4b", "❌", f"No content retrieval method worked for {lang}")
                                
                        except Exception as content_error:
                            add_result("METHOD 4b", "❌", f"Failed to get content for {lang}: {str(content_error)}")
                    
                except Exception as no_param_error:
                    # Try with transcripts parameter as backup
                    try:
                        transcripts_dict = getattr(xblock, 'transcripts', {})
                        available_langs = xblock.available_translations(transcripts_dict)
                        add_result("METHOD 4c", "✅", f"Available translations (with transcripts): {available_langs}")
                    except Exception as with_param_error:
                        add_result("METHOD 4", "❌", f"available_translations() failed both ways: {str(no_param_error)}")
            else:
                add_result("METHOD 4", "❌", "available_translations() method not available")
        except Exception as e:
            add_result("METHOD 4", "❌", f"METHOD 4 error: {str(e)}")
        
        return test_results

    def get_transcript_test_results(self):
        """Get formatted transcript test results for display"""
        if not self.test_transcript_extraction:
            return ""
        
        try:
            # Get the parent unit
            parent = self.get_parent()
            if not parent or not hasattr(parent, 'children'):
                return "No parent unit found for transcript testing"
            
            # Find video XBlocks in the unit
            video_results = []
            for child_id in parent.children:
                try:
                    child = self.runtime.get_block(child_id)
                    if hasattr(child, 'category') and child.category == 'video':
                        test_results = self._run_comprehensive_transcript_tests(child)
                        
                        # Format results for this video
                        video_name = getattr(child, 'display_name', 'Unknown Video')
                        formatted_results = [f"📹 VIDEO: {video_name}"]
                        formatted_results.append("=" * 50)
                        
                        # Group results by method
                        method_groups = {}
                        for result in test_results:
                            method = result['method'].split()[0]  # Get METHOD 1, METHOD 2, etc.
                            if method not in method_groups:
                                method_groups[method] = []
                            method_groups[method].append(result)
                        
                        # Format each method group
                        success_found = False
                        for method in sorted(method_groups.keys()):
                            results = method_groups[method]
                            formatted_results.append(f"\n{method}:")
                            
                            for result in results:
                                status = result['status']
                                message = result['message']
                                content_preview = result['content_preview']
                                
                                if status == "✅" and content_preview:
                                    success_found = True
                                    formatted_results.append(f"  {status} {message}")
                                    formatted_results.append(f"      📝 Content: {content_preview}")
                                elif status == "✅":
                                    formatted_results.append(f"  {status} {message}")
                                elif status == "ℹ️":
                                    formatted_results.append(f"  {status} {message}")
                                else:
                                    formatted_results.append(f"  {status} {message}")
                        
                        # Add summary
                        formatted_results.append("\n" + "=" * 50)
                        if success_found:
                            formatted_results.append("🎉 SUCCESS: Found working transcript extraction method!")
                        else:
                            formatted_results.append("❌ NO SUCCESS: No method successfully extracted transcript content")
                            formatted_results.append("💡 TROUBLESHOOTING:")
                            formatted_results.append("   - Check if transcripts are uploaded in Studio")
                            formatted_results.append("   - Verify video has associated transcript files")
                            formatted_results.append("   - Try uploading transcript directly to video component")
                        
                        video_results.append('\n'.join(formatted_results))
                        
                except Exception as child_error:
                    video_results.append(f"Error processing child: {str(child_error)}")
            
            if not video_results:
                return "No video XBlocks found in this unit"
            
            return '\n\n'.join(video_results)
            
        except Exception as e:
            return f"Error running transcript tests: {str(e)}"

    def _load_transcript_file(self, xblock, filename):
        """Try to load transcript file using various Open edX methods"""
        try:
            # Method 1: Try using the runtime's contentstore
            if hasattr(xblock.runtime, 'contentstore') and hasattr(xblock.runtime.contentstore, 'find'):
                try:
                    # Try to find the file in the contentstore
                    course_key = xblock.scope_ids.usage_id.course_key
                    file_location = course_key.make_asset_key('asset', filename)
                    content = xblock.runtime.contentstore.find(file_location)
                    if content and hasattr(content, 'data'):
                        return content.data.decode('utf-8')
                except Exception:
                    pass
            
            # Method 2: Try using Open edX file system
            if hasattr(xblock, 'runtime') and hasattr(xblock.runtime, 'resources_fs'):
                try:
                    fs = xblock.runtime.resources_fs
                    if fs.exists(filename):
                        return fs.open(filename, 'r').read()
                except Exception:
                    pass
            
            # Method 3: Try getting via transcript API if available
            if hasattr(xblock, 'get_transcript'):
                try:
                    lang = filename.split('-')[-1].replace('.srt', '') if '-' in filename else 'en'
                    transcript_data = xblock.get_transcript(language=lang)
                    if transcript_data:
                        return transcript_data
                except Exception:
                    pass
            
            return None
            
        except Exception:
            return None

    def _get_transcript_by_video_id(self, xblock, video_id):
        """Try to get transcript using video ID through Open edX video API"""
        try:
            # Try importing Open edX video modules
            try:
                from openedx.core.djangoapps.video_config.models import VideoTranscriptEnabledFlag
                from openedx.core.djangoapps.video_pipeline.api import get_transcript_data
                
                # Try to get transcript data
                transcript_data = get_transcript_data(video_id, 'en')
                if transcript_data:
                    return transcript_data
            except ImportError:
                pass
            
            # Try alternative video API
            try:
                from cms.djangoapps.contentstore.video_storage_handlers import get_video_transcript
                transcript = get_video_transcript(video_id, 'en')
                if transcript:
                    return transcript
            except ImportError:
                pass
            
            return None
            
        except Exception:
            return None

    def _parse_transcript_content(self, content):
        """Parse SRT or VTT transcript content to extract just the text"""
        if not content:
            return ""
        
        try:
            lines = content.split('\n')
            text_lines = []
            
            # Parse SRT format
            for line in lines:
                line = line.strip()
                # Skip empty lines, numbers, and timestamp lines
                if (line and 
                    not line.isdigit() and 
                    '-->' not in line and
                    not line.startswith('WEBVTT') and
                    not line.startswith('NOTE')):
                    
                    # Remove SRT formatting tags
                    import re
                    clean_line = re.sub(r'<[^>]+>', '', line)  # Remove HTML tags
                    clean_line = re.sub(r'\{[^}]+\}', '', clean_line)  # Remove SRT styling
                    clean_line = clean_line.strip()
                    
                    if clean_line:
                        text_lines.append(clean_line)
            
            # Join lines and clean up
            transcript_text = ' '.join(text_lines)
            # Remove extra whitespace
            transcript_text = ' '.join(transcript_text.split())
            
            return transcript_text
            
        except Exception:
            # If parsing fails, return the original content
            return content[:1000] if len(content) > 1000 else content

    def _extract_problem_content(self, problem_xblock):
        """Extract meaningful text from problem XBlocks"""
        try:
            if hasattr(problem_xblock, 'data') and problem_xblock.data:
                # Parse XML/HTML content to extract problem text
                problem_html = str(problem_xblock.data)
                
                # Remove script and style elements
                problem_html = re.sub(r'<script[^>]*>.*?</script>', '', problem_html, flags=re.DOTALL | re.IGNORECASE)
                problem_html = re.sub(r'<style[^>]*>.*?</style>', '', problem_html, flags=re.DOTALL | re.IGNORECASE)
                
                # Extract text content
                clean_text = re.sub(r'<[^>]+>', ' ', problem_html)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                
                if clean_text and len(clean_text) > 20:
                    return clean_text
                    
            return None
        except Exception:
            return None

    def build_enhanced_context(self):
        """Build context that includes page content"""
        base_context = self.context_text
        
        page_content = self.get_page_content()
        if page_content:
            enhanced_context = f"""{base_context}

CURRENT COURSE CONTENT:
{page_content}

Use this course content to provide relevant, accurate answers. Reference specific parts when helpful."""
            return enhanced_context
        
        return base_context

    def student_view(self, context=None):
        """
        The primary view of the ChatGPTEnhancedXBlock, shown to students.
        """
        html = self.resource_string("static/html/chatgpt_enhanced.html")

        # Smart disclaimer based on content inclusion
        content_features = []
        if self.include_page_content:
            content_features.append("page content")
        if self.include_video_transcripts:
            content_features.append("video transcripts")
            
        if content_features:
            disclaimer_text = f"This AI assistant has access to {' and '.join(content_features)} and can provide contextual answers."
        else:
            disclaimer_text = "This AI assistant can help answer your questions about the course material."

        disclaimer_html = f"""
        <div class="chatgpt__disclaimer">
          <strong>Smart Assistant:</strong> {disclaimer_text}
        </div>
        """
        
        # Optional reflection section
        reflection_html = ""
        if self.enable_reflection:
            reflection_html = """
            <div class="chatgpt__reflection">
              <label for="reflection-input">Reflection: How does this answer relate to the course content?</label>
              <textarea id="reflection-input" rows="2" placeholder="Reflect on the AI's response..."></textarea>
              <button id="reflection-submit-btn">Submit Reflection</button>
            </div>
            """

        # Format the final HTML content
        final_html = html.format(
            self=self,
            disclaimer=disclaimer_html,
            reflection=reflection_html
        )

        frag = Fragment(final_html)
        frag.add_css(self.resource_string("static/css/chatgpt_enhanced.css"))
        frag.add_javascript(self.resource_string("static/js/chatgpt_enhanced.js"))
        frag.initialize_js('ChatGPTEnhancedXBlock')
        return frag

    def get_openai_client(self):
        """Initialize and return an OpenAI client."""
        api_key = self.api_key
        if not api_key or api_key == "your-openai-api-key-here":
            return None
            
        try:
            client = OpenAI(api_key=api_key)
            return client
        except Exception:
            return None

    @XBlock.json_handler
    def get_answer(self, data, suffix=''):
        """
        Handle the submission of the user's question and return an answer.
        """
        question = data.get('question', '').strip()
        if not question:
            return {"answer": "Please enter a question."}

        # Initialize OpenAI client
        client = self.get_openai_client()
        if client is None:
            return {'error': 'Unable to initialize OpenAI client. Please check your API key configuration.'}

        # Content moderation
        try:
            mod_resp = client.moderations.create(input=question)
            if mod_resp.results[0].flagged:
                return {
                    "answer": "Your question may contain inappropriate content. Please revise your question."
                }
        except AuthenticationError:
            return {"answer": "Authentication error. Please check your API key in studio settings."}
        except Exception as e:
            return {"answer": f"Moderation error: {str(e)}"}

        # Build enhanced context with page content (NEVER includes debug info)
        enhanced_context = self.build_enhanced_context()

        # Handle conversation history
        if self.enable_multi_turn:
            # Add user's question to conversation history
            self.conversation_history.append({"role": "user", "content": question})

            # Limit conversation length
            while len(self.conversation_history) > self.max_conversation_length:
                self.conversation_history.pop(0)

            # Prepare messages with system prompt plus conversation
            messages = [{"role": "system", "content": enhanced_context}]
            messages.extend(self.conversation_history)
        else:
            # Single-turn: just use current question with system prompt
            messages = [
                {"role": "system", "content": enhanced_context},
                {"role": "user", "content": question}
            ]

        # Call ChatGPT API
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
        except AuthenticationError:
            return {"answer": "Authentication error. Please check your API key in studio settings."}
        except Exception as e:
            return {"answer": f"OpenAI API error: {str(e)}"}

        if not response.choices:
            return {"answer": "No response received from the model."}

        content = response.choices[0].message.content.strip()
        if not content:
            content = "Sorry, I couldn't generate a response. Please try again."

        # Add assistant's answer to conversation history (if multi-turn enabled)
        if self.enable_multi_turn:
            self.conversation_history.append({"role": "assistant", "content": content})

        # Prepare the response
        response_data = {"answer": content}
        
        # Add debug information SEPARATELY - not sent to ChatGPT
        if self.debug_mode:
            debug_info = self.get_debug_info()
            response_data["debug_info"] = debug_info
            
        # Add transcript test results if available
        if self.test_transcript_extraction:
            test_results = self.get_transcript_test_results()
            response_data["transcript_test_results"] = test_results

        return response_data

    @XBlock.json_handler
    def submit_reflection(self, data, suffix=''):
        """
        Handle reflection submissions from students.
        """
        reflection = data.get('reflection', '').strip()
        if reflection:
            # TODO: Store reflection for analytics/review
            # You could save to a database, send to analytics service, etc.
            return {"status": "success", "message": "Reflection submitted successfully."}
        else:
            return {"status": "error", "message": "Reflection text is empty."}

    @staticmethod
    def workbench_scenarios():
        """
        Scenarios for display in the XBlock workbench.
        """
        return [
            ("ChatGPTEnhancedXBlock",
             """<chatgpt_enhanced_xblock/>
             """),
            ("Multiple ChatGPTEnhancedXBlock",
             """<vertical_demo>
                <chatgpt_enhanced_xblock/>
                <chatgpt_enhanced_xblock/>
                </vertical_demo>
             """),
        ] 

    def _extract_vimeo_transcripts(self, html_content):
        """Extract transcripts from Vimeo videos embedded in HTML content"""
        try:
            import re
            import requests
            
            # Extract Vimeo video IDs from iframe src URLs
            vimeo_pattern = r'player\.vimeo\.com/video/(\d+)'
            vimeo_matches = re.findall(vimeo_pattern, html_content)
            
            if not vimeo_matches:
                return ""
            
            all_transcripts = []
            
            for video_id in vimeo_matches:
                try:
                    # Try to get Vimeo video transcript via their API
                    transcript_content = self._get_vimeo_transcript(video_id)
                    if transcript_content:
                        all_transcripts.append(f"Video {video_id}: {transcript_content}")
                        
                except Exception as e:
                    # If transcript extraction fails, continue with other videos
                    if self.debug_mode:
                        all_transcripts.append(f"Video {video_id}: Transcript extraction failed - {str(e)}")
                    continue
            
            return '\n\n'.join(all_transcripts)
            
        except Exception:
            return ""

    def _get_vimeo_transcript(self, video_id):
        """Get transcript content from a Vimeo video ID"""
        try:
            import requests
            import json
            
            # Method 1: Try Vimeo's public API for video information
            try:
                # First get video information to check if transcripts are available
                video_url = f"https://vimeo.com/api/v2/video/{video_id}.json"
                response = requests.get(video_url, timeout=10)
                
                if response.status_code == 200:
                    video_info = response.json()
                    if self.debug_mode:
                        # Add debug info about the video
                        return f"Video found: {video_info[0].get('title', 'Unknown')} (Transcript API access requires authentication)"
                        
            except Exception:
                pass
            
            # Method 2: Try to access Vimeo's transcript endpoint (may require authentication)
            try:
                # This is a common pattern for Vimeo transcript access
                transcript_url = f"https://vimeo.com/{video_id}/transcript"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(transcript_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    # Parse HTML response to extract transcript content
                    transcript_content = self._parse_vimeo_transcript_html(response.text)
                    if transcript_content:
                        return transcript_content
                        
            except Exception:
                pass
            
            # Method 3: Try alternative Vimeo API endpoints
            try:
                # Some Vimeo videos have publicly accessible transcript data
                api_url = f"https://player.vimeo.com/video/{video_id}/texttrack"
                response = requests.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    # This might return VTT format transcript
                    transcript_content = self._parse_transcript_content(response.text)
                    if transcript_content:
                        return transcript_content
                        
            except Exception:
                pass
            
            # Method 4: Check for embedded transcript data in the video page
            try:
                video_page_url = f"https://vimeo.com/{video_id}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(video_page_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    # Look for JSON data embedded in the page that might contain transcript info
                    page_content = response.text
                    
                    # Extract any JSON data that might contain transcript information
                    json_pattern = r'window\.vimeoPlayer\s*=\s*({.*?});'
                    json_matches = re.findall(json_pattern, page_content, re.DOTALL)
                    
                    for json_str in json_matches:
                        try:
                            data = json.loads(json_str)
                            # Look for transcript-related data in the JSON
                            if 'transcript' in str(data).lower():
                                # Extract any transcript data found
                                transcript_data = self._extract_transcript_from_json(data)
                                if transcript_data:
                                    return transcript_data
                        except Exception:
                            continue
                            
            except Exception:
                pass
            
            # If all methods fail, return empty string
            return ""
            
        except Exception:
            return ""

    def _parse_vimeo_transcript_html(self, html_content):
        """Parse HTML content from Vimeo transcript page"""
        try:
            import re
            from html import unescape
            
            # Look for transcript content in various HTML structures
            transcript_patterns = [
                r'<div[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</div>',
                r'<span[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</span>',
                r'<p[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</p>',
            ]
            
            for pattern in transcript_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                if matches:
                    # Clean up the HTML content
                    transcript_text = ' '.join(matches)
                    # Remove HTML tags
                    clean_text = re.sub(r'<[^>]+>', ' ', transcript_text)
                    # Decode HTML entities
                    clean_text = unescape(clean_text)
                    # Clean up whitespace
                    clean_text = ' '.join(clean_text.split())
                    
                    if clean_text and len(clean_text) > 50:  # Ensure we have substantial content
                        return clean_text
            
            return ""
            
        except Exception:
            return ""

    def _extract_transcript_from_json(self, json_data):
        """Extract transcript data from JSON objects"""
        try:
            import json
            
            # Convert to string for searching
            data_str = json.dumps(json_data).lower()
            
            # Look for transcript-related keys
            transcript_keys = ['transcript', 'captions', 'subtitles', 'srt', 'vtt']
            
            def search_nested(obj, target_keys):
                """Recursively search for transcript data in nested objects"""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if any(target_key in key.lower() for target_key in target_keys):
                            if isinstance(value, str) and len(value) > 50:
                                return value
                        # Recursively search nested objects
                        result = search_nested(value, target_keys)
                        if result:
                            return result
                elif isinstance(obj, list):
                    for item in obj:
                        result = search_nested(item, target_keys)
                        if result:
                            return result
                return None
            
            transcript_data = search_nested(json_data, transcript_keys)
            if transcript_data:
                # Parse the transcript data (might be VTT, SRT, or plain text)
                return self._parse_transcript_content(transcript_data)
            
            return ""
            
        except Exception:
            return "" 