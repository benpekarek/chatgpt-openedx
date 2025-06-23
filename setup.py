"""
Setup configuration for the ChatGPT Enhanced XBlock
"""

from setuptools import setup, find_packages
import os

def read_file(filename):
    """Read a file and return its contents."""
    with open(os.path.join(os.path.dirname(__file__), filename), 'r', encoding='utf-8') as f:
        return f.read()

setup(
    name='chatgpt-enhanced-xblock',
    version='1.0.0',
    description='Enhanced ChatGPT XBlock with configurable features and smart content awareness',
    long_description=read_file('README.md') if os.path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    author='ChatGPT Enhanced XBlock Developers',
    author_email='support@example.com',
    url='https://github.com/your-username/chatgpt-enhanced-xblock',
    
    # Package configuration
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    
    # Dependencies
    install_requires=[
        'XBlock>=1.2.0',
        'xblock-utils>=2.0.0',
        'openai>=1.0.0',
        'requests>=2.25.0',
    ],
    
    # Python version requirement
    python_requires='>=3.8',
    
    # Entry points for XBlock discovery
    entry_points={
        'xblock.v1': [
            'chatgpt_enhanced_xblock = chatgpt_enhanced_xblock:ChatGPTEnhancedXBlock',
        ],
    },
    
    # Package data (static files)
    package_data={
        'chatgpt_enhanced_xblock': [
            'static/css/*.css',
            'static/js/*.js',
            'static/html/*.html',
            'static/images/*',
        ],
    },
    
    # Classifiers for PyPI
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Education',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Framework :: Django',
        'Topic :: Education',
        'Topic :: Internet :: WWW/HTTP',
    ],
    
    # Keywords for discoverability
    keywords='openedx xblock chatgpt ai education',
    
    # Project URLs
    project_urls={
        'Bug Reports': 'https://github.com/your-username/chatgpt-enhanced-xblock/issues',
        'Source': 'https://github.com/your-username/chatgpt-enhanced-xblock',
        'Documentation': 'https://github.com/your-username/chatgpt-enhanced-xblock#readme',
    },
) 