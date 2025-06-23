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
        help="Show the full prompt being sent to ChatGPT for debugging"
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
        'debug_mode'
    ]

    def resource_string(self, path):
        """Helper for loading resources from the static folder."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def get_page_content(self):
        """Extract content from the current page/unit"""
        if not self.include_page_content:
            return ""
            
        try:
            # Get the parent unit
            parent = self.get_parent()
            if not parent:
                if self.debug_mode:
                    return "DEBUG: No parent found"
                return ""
            
            content_parts = []
            debug_parts = []
            
            if self.debug_mode:
                debug_parts.append(f"DEBUG: Parent found: {parent.__class__.__name__}, children: {len(parent.children) if hasattr(parent, 'children') else 'no children attr'}")
            
            # Walk through all children of the unit to collect content
            if hasattr(parent, 'children'):
                for i, child_id in enumerate(parent.children):
                    try:
                        child = self.runtime.get_block(child_id)
                        if child and child != self:  # Don't include ourselves
                            if self.debug_mode:
                                debug_parts.append(f"DEBUG: Child {i}: {child.__class__.__name__}, category: {getattr(child, 'category', 'no category')}")
                            
                            # Extract text content from various XBlock types
                            content = self._extract_content_from_xblock(child)
                            if content:
                                content_parts.append(content)
                                if self.debug_mode:
                                    debug_parts.append(f"DEBUG: Extracted content from child {i}: {content[:100]}...")
                            elif self.debug_mode:
                                debug_parts.append(f"DEBUG: No content extracted from child {i}")
                                
                    except Exception as e:
                        if self.debug_mode:
                            debug_parts.append(f"DEBUG: Error processing child {i}: {str(e)}")
                        continue
            
            # Combine and limit content
            combined_content = '\n\n'.join(content_parts)
            if len(combined_content) > self.max_content_length:
                combined_content = combined_content[:self.max_content_length] + "..."
            
            if self.debug_mode:
                debug_parts.append(f"DEBUG: Final combined content length: {len(combined_content)}")
                return '\n'.join(debug_parts) + '\n\nACTUAL CONTENT:\n' + combined_content
                
            return combined_content
            
        except Exception as e:
            if self.debug_mode:
                return f"DEBUG: Exception in get_page_content: {str(e)}"
            return ""

    def _extract_content_from_xblock(self, xblock):
        """Extract meaningful content from different types of XBlocks"""
        content_parts = []
        
        # Debug mode: show all attributes for video blocks
        if self.debug_mode and hasattr(xblock, 'category') and xblock.category == 'video':
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
            elif self.debug_mode:
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

    def _get_video_transcript_content(self, video_xblock):
        """Extract actual transcript content from video XBlocks"""
        try:
            # Method 1: Check for transcript data in video XBlock fields
            if hasattr(video_xblock, 'transcript'):
                transcript_data = video_xblock.transcript
                if transcript_data and isinstance(transcript_data, dict):
                    # Extract text content from transcript entries
                    transcript_text = self._parse_transcript_data(transcript_data)
                    if transcript_text:
                        return transcript_text
            
            # Method 2: Check transcripts field (Open edX stores transcripts here)
            if hasattr(video_xblock, 'transcripts') and video_xblock.transcripts:
                transcripts = video_xblock.transcripts
                if isinstance(transcripts, dict):
                    # Get the first available transcript
                    for lang, transcript_file in transcripts.items():
                        if transcript_file:
                            transcript_content = self._load_transcript_file(transcript_file, video_xblock)
                            if transcript_content:
                                return transcript_content
            
            # Method 3: Check for sub (subtitle) field
            if hasattr(video_xblock, 'sub') and video_xblock.sub:
                transcript_content = self._load_transcript_file(video_xblock.sub, video_xblock)
                if transcript_content:
                    return transcript_content
            
            # Method 4: Check for available_translations
            if hasattr(video_xblock, 'available_translations') and video_xblock.available_translations:
                for lang in video_xblock.available_translations:
                    transcript_content = self._get_transcript_for_language(video_xblock, lang)
                    if transcript_content:
                        return transcript_content
                        
            return None
            
        except Exception as e:
            # Log error but don't break the content extraction
            return None

    def _parse_transcript_data(self, transcript_data):
        """Parse transcript data structure to extract text content"""
        try:
            if isinstance(transcript_data, str):
                return transcript_data
            elif isinstance(transcript_data, dict):
                # Common transcript formats
                text_parts = []
                
                # Format 1: Direct text entries
                if 'text' in transcript_data:
                    return transcript_data['text']
                
                # Format 2: Timed entries with text
                if 'entries' in transcript_data:
                    entries = transcript_data['entries']
                    if isinstance(entries, list):
                        for entry in entries:
                            if isinstance(entry, dict) and 'text' in entry:
                                text_parts.append(entry['text'])
                
                # Format 3: SRT-like format with timestamps
                for key, value in transcript_data.items():
                    if isinstance(value, dict) and 'text' in value:
                        text_parts.append(value['text'])
                    elif isinstance(value, str) and len(value) > 10:  # Likely text content
                        text_parts.append(value)
                
                return ' '.join(text_parts) if text_parts else None
            elif isinstance(transcript_data, list):
                # List of transcript entries
                text_parts = []
                for entry in transcript_data:
                    if isinstance(entry, dict) and 'text' in entry:
                        text_parts.append(entry['text'])
                    elif isinstance(entry, str):
                        text_parts.append(entry)
                return ' '.join(text_parts) if text_parts else None
                
            return None
        except Exception:
            return None

    def _load_transcript_file(self, transcript_identifier, video_xblock):
        """Load transcript content from file or URL"""
        try:
            # This would need to be implemented based on how your Open edX instance
            # stores transcripts. Common patterns:
            
            # Method 1: Try to get transcript via the video XBlock's transcript handler
            if hasattr(video_xblock, 'get_transcript'):
                try:
                    transcript_content = video_xblock.get_transcript()
                    if transcript_content:
                        return self._parse_transcript_content(transcript_content)
                except Exception:
                    pass
            
            # Method 2: Try runtime transcript service
            if hasattr(self.runtime, 'service') and hasattr(video_xblock, 'location'):
                try:
                    transcript_service = self.runtime.service(video_xblock, 'transcript')
                    if transcript_service:
                        transcript_content = transcript_service.get_transcript(
                            video_id=transcript_identifier,
                            language='en'  # Default to English, could be made configurable
                        )
                        if transcript_content:
                            return self._parse_transcript_content(transcript_content)
                except Exception:
                    pass
            
            # Method 3: Direct field access for simple cases
            if hasattr(video_xblock, 'transcript_text'):
                return video_xblock.transcript_text
                
            return None
            
        except Exception:
            return None

    def _get_transcript_for_language(self, video_xblock, language):
        """Get transcript for a specific language"""
        try:
            if hasattr(video_xblock, 'get_transcript'):
                transcript_content = video_xblock.get_transcript(language=language)
                if transcript_content:
                    return self._parse_transcript_content(transcript_content)
            return None
        except Exception:
            return None

    def _parse_transcript_content(self, content):
        """Parse raw transcript content (SRT, VTT, or plain text)"""
        try:
            if isinstance(content, dict):
                return self._parse_transcript_data(content)
            elif isinstance(content, str):
                # Remove SRT/VTT timestamps and formatting
                lines = content.split('\n')
                text_lines = []
                
                for line in lines:
                    line = line.strip()
                    # Skip empty lines, numbers, and timestamp lines
                    if (line and 
                        not line.isdigit() and 
                        '-->' not in line and 
                        not line.startswith('WEBVTT') and
                        not line.startswith('NOTE')):
                        # Remove HTML tags if present
                        clean_line = re.sub(r'<[^>]+>', '', line)
                        if clean_line.strip():
                            text_lines.append(clean_line.strip())
                
                return ' '.join(text_lines) if text_lines else None
            
            return None
        except Exception:
            return None

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

        # Build enhanced context with page content
        enhanced_context = self.build_enhanced_context()

        # Debug mode: show what content was extracted
        debug_info = ""
        if self.debug_mode:
            page_content = self.get_page_content()
            debug_info = f"""
**DEBUG INFO:**
Raw page content extracted: {repr(page_content)}

Enhanced context being sent to ChatGPT:
{enhanced_context}

---
"""

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

        # Debug mode: add messages info
        if self.debug_mode:
            debug_info += f"""
Messages being sent to OpenAI:
{messages}

---
"""

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

        # Prepend debug info if debug mode is enabled
        if self.debug_mode:
            content = debug_info + content

        return {"answer": content}

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