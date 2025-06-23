# ChatGPT Enhanced XBlock

An enhanced version of the ChatGPT XBlock for Open edX platforms with advanced features including configurable reflection prompts, multi-turn conversations, and intelligent content awareness.

## ✨ Features

### Core Functionality
- **AI-Powered Conversations**: Interactive chat interface powered by OpenAI's GPT models
- **Multiple GPT Models**: Support for GPT-3.5 Turbo, GPT-4, GPT-4 Turbo, GPT-4o, and GPT-4o Mini
- **Content Moderation**: Built-in OpenAI moderation for appropriate content

### Enhanced Features
- **🔄 Configurable Reflection**: Optional reflection prompts after AI responses
- **💬 Multi-Turn Conversations**: Maintains conversation context across multiple exchanges
- **📖 Smart Content Awareness**: Automatically includes page content and video transcripts in AI context
- **⚙️ Flexible Configuration**: Studio-editable settings for all features
- **📱 Responsive Design**: Modern, mobile-friendly interface
- **🎯 Token Management**: Configurable limits for conversation length and content inclusion

### Studio Configuration Options
- **Display Name**: Customize the XBlock title
- **Model Selection**: Choose from available GPT models
- **API Key**: Your OpenAI API key
- **Context Settings**: System prompt and temperature control
- **Feature Toggles**:
  - Enable/disable reflection prompts
  - Enable/disable multi-turn conversations
  - Enable/disable page content inclusion
  - Enable/disable video transcript inclusion
- **Limits**: Max tokens, conversation length, and content length

## 📋 Requirements

- Open edX (Tutor-based installations supported)
- Python 3.8+
- OpenAI API key
- XBlock framework

## 🚀 Installation

### Option 1: Install from GitHub (Recommended)

Add to your Open edX requirements:

```bash
# For Tutor installations
tutor config save --set OPENEDX_EXTRA_PIP_REQUIREMENTS='["git+https://github.com/your-username/chatgpt-enhanced-xblock.git"]'
tutor images build openedx
tutor local stop && tutor local start -d
```

### Option 2: Development Installation

```bash
# Clone the repository
git clone https://github.com/your-username/chatgpt-enhanced-xblock.git
cd chatgpt-enhanced-xblock

# Install in development mode
pip install -e .
```

### Option 3: Manual Installation in Docker Container

```bash
# Enter the LMS container
tutor local exec lms bash

# Install the package
pip install git+https://github.com/your-username/chatgpt-enhanced-xblock.git

# Exit and restart
exit
tutor local restart
```

## ⚙️ Configuration

### 1. Enable the XBlock

Add to your advanced module list in Studio:

```json
["chatgpt_enhanced_xblock"]
```

Or via Django admin/config:

```python
ADVANCED_COMPONENT_TYPES = ["chatgpt_enhanced_xblock"]
```

### 2. Studio Settings

After adding to a unit, configure in Studio:

1. **API Key**: Enter your OpenAI API key
2. **Model**: Select your preferred GPT model
3. **Features**: Enable/disable reflection, multi-turn, content awareness
4. **Context**: Customize the system prompt
5. **Limits**: Set token and conversation limits

### 3. OpenAI API Key

Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys) and add it in the XBlock settings.

## 🎯 Usage

### For Course Authors

1. **Add the XBlock**: In Studio, add "ChatGPT Enhanced Assistant" from Advanced components
2. **Configure Settings**: Set your API key and desired features
3. **Customize Context**: Write a system prompt that aligns with your course goals
4. **Content Awareness**: Enable page content inclusion for contextual responses
5. **Reflection**: Enable reflection prompts to encourage critical thinking

### For Students

1. **Ask Questions**: Type questions about the course content
2. **Multi-Turn Conversations**: Build on previous questions (if enabled)
3. **Contextual Responses**: Get answers that reference page content and videos
4. **Reflect**: Use reflection prompts to deepen understanding (if enabled)

## 🏗️ Architecture

### Smart Content Awareness

The XBlock automatically extracts content from the current page/unit:

- **HTML Content**: Text from HTML XBlocks
- **Video Transcripts**: Automatic transcript inclusion
- **Problem Content**: Text from problem XBlocks
- **Content Limits**: Configurable character limits to manage token usage

### Conversation Management

- **Memory**: Maintains conversation history per student
- **Limits**: Configurable max conversation length
- **Context**: Combines system prompt with page content
- **Reset**: Conversations reset when page is reloaded

### Security & Moderation

- **Content Filtering**: OpenAI moderation API integration
- **API Key Security**: Stored securely in XBlock settings
- **Error Handling**: Graceful fallbacks for API failures

## 🛠️ Development

### Local Development Setup

```bash
# Clone and setup
git clone https://github.com/your-username/chatgpt-enhanced-xblock.git
cd chatgpt-enhanced-xblock

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt
```

### File Structure

```
chatgpt-enhanced-xblock/
├── chatgpt_enhanced_xblock/
│   ├── __init__.py
│   ├── chatgpt_enhanced_xblock.py      # Main XBlock class
│   └── static/
│       ├── css/
│       │   └── chatgpt_enhanced.css    # Styling
│       ├── js/
│       │   └── chatgpt_enhanced.js     # Frontend logic
│       └── html/
│           └── chatgpt_enhanced.html   # Template
├── setup.py                            # Package configuration
├── README.md                           # This file
├── LICENSE                             # License file
└── requirements.txt                    # Dependencies
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 🔧 Troubleshooting

### Common Issues

**XBlock not appearing in Studio**
- Verify it's added to advanced module list
- Check Docker container restart after installation
- Ensure entry points are correctly configured

**API Errors**
- Verify OpenAI API key is correct and has credits
- Check network connectivity from your Open edX instance
- Review API usage limits

**Content Not Loading**
- Ensure page content inclusion is enabled
- Check that parent unit has content
- Verify content length limits

**Conversation Not Persisting**
- Ensure multi-turn conversations are enabled
- Check that user state is being saved properly
- Verify conversation length limits

### Debug Mode

Enable debug logging in your Open edX settings:

```python
LOGGING['loggers']['chatgpt_enhanced_xblock'] = {
    'handlers': ['tracking'],
    'level': 'DEBUG',
    'propagate': False,
}
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/your-username/chatgpt-enhanced-xblock/issues)
- **Documentation**: Additional docs available in the [Wiki](https://github.com/your-username/chatgpt-enhanced-xblock/wiki)
- **Community**: Join discussions in the [Open edX Community](https://discuss.openedx.org/)

## 🙏 Acknowledgments

- Built on the original [ChatGPT XBlock](https://github.com/abconlinecourses/chatgpt-xblock)
- Open edX Platform and XBlock framework
- OpenAI for the GPT API
- Open source community contributions

## 📊 Analytics & Privacy

- **Reflection Data**: Stored locally for instructor review (optional)
- **Conversation Logs**: Not stored by default (configurable)
- **API Usage**: Subject to OpenAI's usage policies
- **Student Privacy**: No personal data sent to OpenAI beyond conversation content 