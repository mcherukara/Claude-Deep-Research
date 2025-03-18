# Claude Deep Research

An MCP (Model Context Protocol) server that enables comprehensive research capabilities for Claude and other MCP-compatible AI assistants. This server integrates web and academic search functionality, allowing AI models to access current information from multiple sources, follow relevant links, and provide well-structured research results.

![Research Workflow](workflow.svg)

## Overview

Claude Deep Research is a powerful research tool that extends the capabilities of LLMs by providing:

1. **Web search** integration through DuckDuckGo
2. **Academic research** access through Semantic Scholar 
3. **Content extraction** from web pages
4. **Comprehensive analysis** with structured formatting
5. **Visualization guidance** for data representation

The server follows MCP design principles to provide a seamless integration with Claude and other AI assistants.

## Features

- **Unified Research Tool**: Single interface for web and academic information
- **Multi-Source Integration**: Combines information from various sources into cohesive research
- **Content Extraction**: Pulls relevant information from web pages
- **Academic Source Discovery**: Finds scholarly articles related to your topic
- **Smart Formatting**: Properly formats research with citations
- **Visual Framework**: Provides guidance for creating effective data visualizations
- **Structured Analysis**: Organizes research using academic methodologies

## Installation

### Prerequisites

- Python 3.8 or higher
- pip or uv package manager

### Quick Install

```bash
# Using pip
pip install mcp httpx beautifulsoup4

# Clone the repository
git clone https://github.com/yourusername/claude-deep-research.git
```

## Configuration

The server works out of the box with default settings, but you can modify the following parameters in deep_research.py for customization:

```python
# Configuration
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
MAX_CONTENT_SIZE = 8000  # Maximum characters in the final response
MAX_RESULTS = 3         # Maximum number of results to process
```

## Usage

### Running the Server

Modify your Claude desktop config and restart Claude. 
On a Mac this is at ~/Library/Application Support/Claude
```
  "search-scholar": {
      "command": "<Path to Python>/python",
      "args": [
        "<Path to deep research>/deep_research.py"
      ]
    }
```

### Using with Claude Desktop

Once installed, you can access the server in Claude Desktop:

1. **Tool Access**: Use the `deep_research` tool directly in conversation

### Research Tool

The main `deep_research` tool accepts the following parameters:

- `query` (required): The research question or topic
- `sources` (optional): Which sources to use: "web", "academic", or "both" (default)
- `num_results` (optional): Number of sources to examine (default 2, max 3)

Example prompts:

```
Can you research the latest developments in quantum computing?

I need comprehensive information about climate change mitigation strategies. Use the deep_research tool to help me.

Research the history and cultural significance of origami using academic sources.
```

### Research Prompt

The server includes a structured research prompt that guides Claude through a comprehensive research process:

1. **Initial Exploration**: Gathers information from multiple sources
2. **Preliminary Synthesis**: Organizes findings with visualization
3. **Follow-up Research**: Identifies and explores knowledge gaps
4. **Comprehensive Analysis**: Integrates all information with visual elements
5. **Proper Citations**: Formats references using APA style


## Troubleshooting

### Common Issues

- **Server Connection Failures**: Ensure you're using the correct path to the server file.
- **Search Errors**: Some searches may time out or return limited results. Try a more specific query.
- **Web Access Issues**: The server requires internet access to function properly.
- **Content Formatting**: Very large responses may be truncated to fit within size limits.

### Logs

The server outputs logs to stderr that can help diagnose issues:

```bash
# View logs when running directly
python deep_research.py 2> server.log

# View logs from Claude Desktop (macOS/Linux)
tail -f ~/Library/Logs/Claude/mcp-server-deepresearch.log
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


## Acknowledgments

- Built on the [Model Context Protocol](https://modelcontextprotocol.io/)
- Uses [DuckDuckGo](https://duckduckgo.com/) for web search
- Uses [Semantic Scholar](https://www.semanticscholar.org/) for academic research
- Inspired by Anthropic's [Claude](https://claude.ai/)

---

Made with ❤️ for extending AI capabilities through MCP
