# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Cerebras-to-Ollama API wrapper that creates a drop-in replacement for Ollama by translating requests to the Cerebras API. The wrapper provides full compatibility with Ollama's API endpoints and streaming response format.

## Architecture

### Core Components

- **ollama_compliant.py**: The main production implementation with full Ollama API compatibility. Implements `/api/generate`, `/api/chat`, `/api/tags`, `/api/show`, `/api/ps`, and `/api/version` endpoints with proper Ollama response formats and streaming.

- **main.py**: Initial implementation using the Cerebras SDK with OpenAI-style endpoints (`/v1/chat/completions`). Includes robust client initialization with fallback mechanisms.

- **main_http.py**: HTTP-only implementation using direct API calls to Cerebras without the SDK dependency.

- **app_requirement.txt**: Contains development notes and example Cerebras API usage patterns.

### API Translation Layer

The wrapper performs several key translations:
- Converts Ollama chat/generate requests to Cerebras chat completions
- Transforms Cerebras streaming responses to match Ollama's chunk format
- Generates proper timestamps, model names, and timing metrics
- Handles both streaming and non-streaming responses

## Development Commands

### Running the Application

```bash
# Run the main Ollama-compliant server (production)
python ollama_compliant.py

# Run alternative implementations
python main.py           # SDK-based version
python main_http.py      # HTTP-only version
```

### Using Docker

```bash
# Build the container
docker build -t cerebras-ollama-wrapper .

# Run with docker-compose (preferred)
docker-compose up

# Run directly
docker run -p 6000:6000 --env-file .env cerebras-ollama-wrapper
```

### Installing Dependencies

```bash
pip install -r requirements.txt
```

## Environment Configuration

Required environment variables:
- `CEREBRAS_API_KEY`: Your Cerebras API key
- `CAI_MODEL`: The Cerebras model to use (defaults to "qwen-3-235b-a22b-instruct-2507")

The application runs on port 6000 and provides these key endpoints:
- `/api/chat` - Ollama chat completions
- `/api/generate` - Ollama text generation  
- `/api/tags` - List available models
- `/api/show` - Show model information
- `/api/ps` - Show running models
- `/api/version` - API version info

## Key Implementation Details

- Uses FastAPI for the web framework
- Supports both streaming and non-streaming responses
- Implements proper error handling and fallback mechanisms
- Maintains full compatibility with Ollama client libraries
- Generates realistic timing metrics and model metadata