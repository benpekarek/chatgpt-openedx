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
        'max_content_length'
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
                return ""
            
            content_parts = []
            
            # Walk through all children of the unit to collect content
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

    def _extract_content_from_xblock(self, xblock):
        """Extract meaningful content from different types of XBlocks"""
        content_parts = []
        
        # HTML XBlocks
        if hasattr(xblock, 'data') and xblock.data:
            html_content = str(xblock.data)
            clean_text = re.sub(r'<[^>]+>', ' ', html_content)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            if clean_text and len(clean_text) > 20:
                content_parts.append(f"Page content: {clean_text}")
        
        # Video XBlocks with transcripts
        if self.include_video_transcripts:
            if hasattr(xblock, 'transcript') and xblock.transcript:
                content_parts.append(f"Video transcript: {xblock.transcript}")
            
            # Check for transcript in different possible locations
            transcript_fields = ['transcript_download', 'transcript_text', 'transcripts']
            for field in transcript_fields:
                if hasattr(xblock, field):
                    transcript_data = getattr(xblock, field)
                    if transcript_data:
                        content_parts.append(f"Video transcript: {str(transcript_data)}")
                        break
        
        # Problem XBlocks
        if hasattr(xblock, 'problem_text') and xblock.problem_text:
            content_parts.append(f"Problem content: {xblock.problem_text}")
            
        return '\n'.join(content_parts)

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