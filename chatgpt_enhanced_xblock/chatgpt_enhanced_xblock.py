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
        
        # HTML XBlocks
        if hasattr(xblock, 'data') and xblock.data:
            html_content = str(xblock.data)
            clean_text = re.sub(r'<[^>]+>', ' ', html_content)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            if clean_text and len(clean_text) > 20:
                content_parts.append(f"Page content: {clean_text}")
        
        # Video XBlocks with transcripts
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
        
        # First, try to extract transcript content normally
        transcript_content = self._extract_transcript_simple(xblock)
        
        # If testing mode is enabled, run comprehensive tests but don't include in content
        if self.test_transcript_extraction:
            test_results = self._run_comprehensive_transcript_tests(xblock)
            # Store test results separately - they should be shown in debug output, not sent to ChatGPT
            self._transcript_test_results = test_results
        
        return transcript_content

    def _extract_transcript_simple(self, xblock):
        """Simple transcript extraction - just get the content without debug info"""
        try:
            # Method 1: Try calling the transcript() method directly
            if hasattr(xblock, 'transcript') and callable(xblock.transcript):
                try:
                    transcript_result = xblock.transcript(None)
                    if transcript_result:
                        if hasattr(transcript_result, 'content'):
                            content = transcript_result.content
                        else:
                            content = str(transcript_result)
                        
                        parsed_content = self._parse_transcript_content(content)
                        if parsed_content:
                            return parsed_content
                except Exception:
                    pass
            
            # Method 2: Try getting transcript via transcripts attribute and file loading
            if hasattr(xblock, 'transcripts') and xblock.transcripts:
                try:
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
            
            # Method 3: Try using edx_video_id to get transcript
            if hasattr(xblock, 'edx_video_id') and xblock.edx_video_id:
                try:
                    video_id = xblock.edx_video_id
                    transcript_data = self._get_transcript_by_video_id(xblock, video_id)
                    if transcript_data:
                        parsed_content = self._parse_transcript_content(transcript_data)
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
        
        # METHOD 1: Try calling the transcript() method with proper dispatch
        try:
            if hasattr(xblock, 'transcript'):
                try:
                    # Try with mock dispatch first
                    class MockRequest:
                        def __init__(self):
                            self.GET = {}
                            self.POST = {}
                    
                    mock_request = MockRequest()
                    transcript_response = xblock.transcript(mock_request)
                    if transcript_response and hasattr(transcript_response, 'content'):
                        content = transcript_response.content.decode('utf-8')
                        add_result("METHOD 1", "✅", "xblock.transcript() with mock request", content)
                    else:
                        add_result("METHOD 1", "❌", "xblock.transcript() returned empty response")
                except Exception as dispatch_error:
                    # Try without dispatch parameter 
                    try:
                        transcript_data = xblock.transcript()
                        add_result("METHOD 1", "✅", "xblock.transcript() direct call", str(transcript_data))
                    except Exception as direct_error:
                        add_result("METHOD 1", "❌", f"xblock.transcript() error: {str(dispatch_error)}")
            else:
                add_result("METHOD 1", "❌", "xblock.transcript() method not available")
        except Exception as e:
            add_result("METHOD 1", "❌", f"METHOD 1 error: {str(e)}")
        
        # METHOD 2: Enhanced file loading from transcripts attribute
        try:
            if hasattr(xblock, 'transcripts') and xblock.transcripts:
                add_result("METHOD 2", "✅", f"Found transcripts dict: {xblock.transcripts}")
                
                for lang, filename in xblock.transcripts.items():
                    add_result("METHOD 2", "ℹ️", f"Trying to load transcript file: {filename}")
                    
                    # Try multiple file loading approaches
                    transcript_content = None
                    
                    # Approach 2a: Try contentstore access
                    try:
                        from openedx.core.lib.file_storage import get_storage
                        from django.conf import settings
                        
                        storage = get_storage()
                        if storage.exists(f"transcripts/{filename}"):
                            with storage.open(f"transcripts/{filename}") as f:
                                transcript_content = f.read().decode('utf-8')
                                add_result("METHOD 2a", "✅", f"Loaded via contentstore: {filename}", transcript_content)
                                break
                    except Exception as storage_error:
                        add_result("METHOD 2a", "❌", f"Contentstore access failed: {str(storage_error)}")
                    
                    # Approach 2b: Try modulestore access
                    try:
                        from xmodule.modulestore.django import modulestore
                        from opaque_keys.edx.keys import UsageKey
                        
                        if hasattr(xblock, 'location'):
                            store = modulestore()
                            # Try to find transcript in static assets
                            course_key = xblock.location.course_key
                            transcript_location = f"transcripts/{filename}"
                            
                            # This might work for some Open edX configurations
                            asset_content = store.find_asset_metadata(course_key, transcript_location)
                            if asset_content:
                                add_result("METHOD 2b", "✅", f"Found asset metadata for {filename}")
                            else:
                                add_result("METHOD 2b", "❌", f"No asset metadata found for {filename}")
                                
                    except Exception as modulestore_error:
                        add_result("METHOD 2b", "❌", f"Modulestore access failed: {str(modulestore_error)}")
                    
                    # Approach 2c: Try direct file system access (for development)
                    try:
                        import os
                        from django.conf import settings
                        
                        possible_paths = [
                            f"/openedx/data/transcripts/{filename}",
                            f"/openedx/edx-platform/transcripts/{filename}",
                            f"{settings.MEDIA_ROOT}/transcripts/{filename}" if hasattr(settings, 'MEDIA_ROOT') else None,
                        ]
                        
                        for path in possible_paths:
                            if path and os.path.exists(path):
                                with open(path, 'r', encoding='utf-8') as f:
                                    transcript_content = f.read()
                                    add_result("METHOD 2c", "✅", f"Loaded via filesystem: {path}", transcript_content)
                                    break
                        
                        if not transcript_content:
                            add_result("METHOD 2c", "❌", f"File not found in any expected location")
                            
                    except Exception as fs_error:
                        add_result("METHOD 2c", "❌", f"Filesystem access failed: {str(fs_error)}")
                    
                    if not transcript_content:
                        add_result("METHOD 2", "❌", f"Could not load {filename} via any method")
                    
            else:
                add_result("METHOD 2", "❌", "No transcripts attribute found")
        except Exception as e:
            add_result("METHOD 2", "❌", f"METHOD 2 error: {str(e)}")
        
        # METHOD 3: Enhanced Video API using edx_video_id
        try:
            video_id = getattr(xblock, 'edx_video_id', None)
            if video_id:
                add_result("METHOD 3", "✅", f"Trying edx_video_id: {video_id}")
                
                # Try multiple video API approaches
                try:
                    from edxval.api import get_video_transcript_content
                    transcript_content = get_video_transcript_content(video_id, language_code='en')
                    if transcript_content:
                        add_result("METHOD 3a", "✅", "Got transcript via edxval.api.get_video_transcript_content", transcript_content)
                    else:
                        add_result("METHOD 3a", "❌", "edxval.api returned empty content")
                except Exception as api_error:
                    add_result("METHOD 3a", "❌", f"edxval.api failed: {str(api_error)}")
                
                try:
                    from edxval.models import VideoTranscript
                    transcript_obj = VideoTranscript.objects.filter(video__edx_video_id=video_id, language_code='en').first()
                    if transcript_obj:
                        add_result("METHOD 3b", "✅", f"Found VideoTranscript object: {transcript_obj.file_format}", transcript_obj.transcript)
                    else:
                        add_result("METHOD 3b", "❌", "No VideoTranscript object found in database")
                except Exception as model_error:
                    add_result("METHOD 3b", "❌", f"VideoTranscript model access failed: {str(model_error)}")
                    
            else:
                add_result("METHOD 3", "❌", "No edx_video_id found")
        except Exception as e:
            add_result("METHOD 3", "❌", f"METHOD 3 error: {str(e)}")
        
        # METHOD 4: Enhanced available_translations() method
        try:
            if hasattr(xblock, 'available_translations'):
                try:
                    # Try with transcripts parameter
                    transcripts_dict = getattr(xblock, 'transcripts', {})
                    available_langs = xblock.available_translations(transcripts_dict)
                    add_result("METHOD 4a", "✅", f"Available translations: {available_langs}")
                    
                    # Try to get content for each available language
                    for lang in available_langs:
                        try:
                            # This is a guess at the API - might need adjustment
                            content = xblock.get_transcript(lang)
                            if content:
                                add_result("METHOD 4b", "✅", f"Got transcript content for {lang}", content)
                        except Exception as content_error:
                            add_result("METHOD 4b", "❌", f"Failed to get content for {lang}: {str(content_error)}")
                            
                except Exception as trans_error:
                    # Try without parameters
                    try:
                        available_langs = xblock.available_translations()
                        add_result("METHOD 4c", "✅", f"Available translations (no params): {available_langs}")
                    except Exception as no_param_error:
                        add_result("METHOD 4", "❌", f"available_translations() error: {str(trans_error)}")
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