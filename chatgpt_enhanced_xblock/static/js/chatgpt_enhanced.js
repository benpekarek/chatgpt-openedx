function ChatGPTEnhancedXBlock(runtime, element) {
    'use strict';

    // Cache DOM elements
    const $element = $(element);
    const $questionInput = $element.find('#user-question');
    const $submitBtn = $element.find('#submit-question');
    const $conversation = $element.find('#conversation-history');
    const $statusMessage = $element.find('#status-message');
    const $reflectionInput = $element.find('#reflection-input');
    const $reflectionSubmitBtn = $element.find('#reflection-submit-btn');
    
    // Button text elements
    const $btnText = $submitBtn.find('.btn-text');
    const $btnLoading = $submitBtn.find('.btn-loading');

    // Handler URLs
    const getAnswerUrl = runtime.handlerUrl(element, 'get_answer');
    const submitReflectionUrl = runtime.handlerUrl(element, 'submit_reflection');

    // Initialize the XBlock
    function init() {
        setupEventListeners();
        $questionInput.focus();
        
        // Add welcome message if conversation is empty
        if ($conversation.children().length === 0) {
            addWelcomeMessage();
        }
    }

    function setupEventListeners() {
        // Submit question on button click
        $submitBtn.on('click', function(e) {
            e.preventDefault();
            submitQuestion();
        });

        // Submit question on Enter (but allow Shift+Enter for new lines)
        $questionInput.on('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submitQuestion();
            }
        });

        // Auto-resize textarea
        $questionInput.on('input', function() {
            autoResizeTextarea(this);
        });

        // Reflection submission
        if ($reflectionSubmitBtn.length) {
            $reflectionSubmitBtn.on('click', function(e) {
                e.preventDefault();
                submitReflection();
            });
        }

        // Focus management
        $questionInput.on('focus', function() {
            $(this).parent().addClass('focused');
        }).on('blur', function() {
            $(this).parent().removeClass('focused');
        });
    }

    function addWelcomeMessage() {
        const welcomeHtml = `
            <div class="chatgpt__message chatgpt__message--assistant">
                <p>👋 Hello! I'm your AI assistant. I can help answer questions about the course content on this page.</p>
                <p>Feel free to ask me anything about what you're learning!</p>
            </div>
        `;
        $conversation.append(welcomeHtml);
        scrollToBottom();
    }

    function submitQuestion() {
        const question = $questionInput.val().trim();
        
        if (!question) {
            showStatus('Please enter a question.', 'error');
            return;
        }

        // Disable form and show loading state
        setLoadingState(true);
        
        // Add user message to conversation
        addUserMessage(question);
        
        // Clear input
        $questionInput.val('');
        resetTextareaHeight();

        // Make API call
        $.ajax({
            url: getAnswerUrl,
            type: 'POST',
            data: JSON.stringify({ question: question }),
            contentType: 'application/json',
            success: function(response) {
                handleApiResponse(response);
            },
            error: function(xhr, status, error) {
                handleApiError(error);
            },
            complete: function() {
                setLoadingState(false);
            }
        });
    }

    function handleApiResponse(response) {
        if (response.error) {
            showStatus(response.error, 'error');
            addAssistantMessage('Sorry, I encountered an error. Please try again.');
        } else if (response.answer) {
            addAssistantMessage(response.answer);
            showReflectionPrompt();
        } else {
            showStatus('Unexpected response format.', 'error');
            addAssistantMessage('Sorry, I couldn\'t process your request properly.');
        }
    }

    function handleApiError(error) {
        console.error('API Error:', error);
        showStatus('Network error. Please check your connection and try again.', 'error');
        addAssistantMessage('Sorry, I\'m having trouble connecting right now. Please try again in a moment.');
    }

    function addUserMessage(message) {
        const messageHtml = `
            <div class="chatgpt__message chatgpt__message--user">
                ${escapeHtml(message)}
            </div>
        `;
        $conversation.append(messageHtml);
        scrollToBottom();
    }

    function addAssistantMessage(message) {
        // Convert markdown-style formatting to HTML
        let formattedMessage = formatMessageContent(message);
        
        const messageHtml = `
            <div class="chatgpt__message chatgpt__message--assistant">
                ${formattedMessage}
            </div>
        `;
        $conversation.append(messageHtml);
        scrollToBottom();
    }

    function formatMessageContent(content) {
        // Basic markdown-like formatting
        content = escapeHtml(content);
        
        // Convert **bold** to <strong>
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert *italic* to <em>
        content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Convert line breaks to paragraphs
        const paragraphs = content.split('\n\n').filter(p => p.trim());
        if (paragraphs.length > 1) {
            content = paragraphs.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
        } else {
            content = `<p>${content.replace(/\n/g, '<br>')}</p>`;
        }
        
        return content;
    }

    function showReflectionPrompt() {
        // Only show if reflection is enabled and exists
        if ($reflectionInput.length && $reflectionInput.is(':visible')) {
            $reflectionInput.closest('.chatgpt__reflection').show();
            // Optionally focus the reflection input
            setTimeout(() => {
                $reflectionInput.focus();
            }, 500);
        }
    }

    function submitReflection() {
        const reflection = $reflectionInput.val().trim();
        
        if (!reflection) {
            showStatus('Please enter your reflection.', 'error');
            return;
        }

        // Disable reflection form
        $reflectionSubmitBtn.prop('disabled', true);

        $.ajax({
            url: submitReflectionUrl,
            type: 'POST',
            data: JSON.stringify({ reflection: reflection }),
            contentType: 'application/json',
            success: function(response) {
                if (response.status === 'success') {
                    showStatus('Reflection submitted successfully!', 'success');
                    $reflectionInput.val('');
                    $reflectionInput.closest('.chatgpt__reflection').hide();
                } else {
                    showStatus(response.message || 'Failed to submit reflection.', 'error');
                }
            },
            error: function() {
                showStatus('Error submitting reflection.', 'error');
            },
            complete: function() {
                $reflectionSubmitBtn.prop('disabled', false);
            }
        });
    }

    function setLoadingState(isLoading) {
        $submitBtn.prop('disabled', isLoading);
        $questionInput.prop('disabled', isLoading);
        
        if (isLoading) {
            $btnText.hide();
            $btnLoading.show();
            
            // Add typing indicator
            addTypingIndicator();
        } else {
            $btnText.show();
            $btnLoading.hide();
            
            // Remove typing indicator
            removeTypingIndicator();
            
            // Re-focus input
            $questionInput.focus();
        }
    }

    function addTypingIndicator() {
        const typingHtml = `
            <div class="chatgpt__message chatgpt__message--assistant chatgpt__typing" id="typing-indicator">
                <p>
                    <span class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </span>
                    Thinking...
                </p>
            </div>
        `;
        $conversation.append(typingHtml);
        scrollToBottom();

        // Add CSS for typing animation if not already present
        if (!document.querySelector('#typing-animation-css')) {
            const style = document.createElement('style');
            style.id = 'typing-animation-css';
            style.textContent = `
                .typing-dots {
                    display: inline-block;
                    margin-right: 8px;
                }
                .typing-dots span {
                    display: inline-block;
                    width: 4px;
                    height: 4px;
                    border-radius: 50%;
                    background-color: #999;
                    margin: 0 1px;
                    animation: typing 1.4s infinite;
                }
                .typing-dots span:nth-child(2) {
                    animation-delay: 0.2s;
                }
                .typing-dots span:nth-child(3) {
                    animation-delay: 0.4s;
                }
                @keyframes typing {
                    0%, 60%, 100% {
                        transform: translateY(0);
                        opacity: 0.4;
                    }
                    30% {
                        transform: translateY(-8px);
                        opacity: 1;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    function removeTypingIndicator() {
        $conversation.find('#typing-indicator').remove();
    }

    function scrollToBottom() {
        $conversation.animate({
            scrollTop: $conversation[0].scrollHeight
        }, 300);
    }

    function autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    function resetTextareaHeight() {
        $questionInput[0].style.height = 'auto';
    }

    function showStatus(message, type) {
        $statusMessage
            .removeClass('chatgpt__status--success chatgpt__status--error')
            .addClass('chatgpt__status--' + type)
            .text(message)
            .show();

        // Auto-hide after 5 seconds
        setTimeout(() => {
            $statusMessage.fadeOut();
        }, 5000);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Initialize when DOM is ready
    $(document).ready(function() {
        init();
    });

    // Public API
    return {
        init: init,
        submitQuestion: submitQuestion,
        submitReflection: submitReflection
    };
} 