# Cerebras-Ollama Wrapper

A drop-in replacement for Ollama that translates requests to the Cerebras API, providing full compatibility with Ollama's API endpoints and streaming response format.

## Overview

This project creates a bridge between the Ollama API format and Cerebras AI's cloud inference API, allowing you to use any Ollama-compatible client with Cerebras models. The wrapper maintains full compatibility with Ollama's response formats while leveraging Cerebras's high-performance inference infrastructure.

## Features

- **Full Ollama API Compatibility**: Supports all major Ollama endpoints (`/api/chat`, `/api/generate`, `/api/tags`, `/api/show`, `/api/ps`, `/api/version`)
- **Streaming Support**: Real-time streaming responses matching Ollama's chunk format
- **Multiple Implementations**: Choose from SDK-based, HTTP-only, or production-ready implementations
- **Docker Support**: Easy deployment with Docker and docker-compose
- **Robust Error Handling**: Comprehensive error handling with fallback mechanisms
- **Configurable Models**: Support for any Cerebras model via environment variables

## Quick Start

### Prerequisites

- Python 3.8+
- Cerebras API key ([get one here](https://cerebras.ai/))

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd xcerllama
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your Cerebras API key
```

### Configuration

Create a `.env` file with the following variables:

```env
CEREBRAS_API_KEY=your_cerebras_api_key_here
CAI_MODEL=qwen-3-235b-a22b-instruct-2507
```

## Usage

### Running the Server

#### Production (Recommended)
```bash
python ollama_compliant.py
```

#### Alternative Implementations
```bash
# SDK-based version
python main.py

# HTTP-only version
python main_http.py
```

The server will start on `http://localhost:6000`

### Using with Ollama Clients

Once the server is running, you can use any Ollama-compatible client:

```bash
# Using curl
curl http://localhost:6000/api/chat \
  -d '{
    "model": "qwen",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "stream": false
  }'

# Using Ollama CLI (point to your wrapper)
OLLAMA_HOST=http://localhost:6000 ollama run qwen "Hello!"
```

### Docker Deployment

#### Using Docker Compose (Recommended)
```bash
docker-compose up
```

#### Using Docker directly
```bash
# Build the image
docker build -t cerebras-ollama-wrapper .

# Run the container
docker run -p 6000:6000 --env-file .env cerebras-ollama-wrapper
```

## API Endpoints

The wrapper provides full compatibility with Ollama's API:

- `GET /` - Health check
- `POST /api/chat` - Chat completions (with streaming support)
- `POST /api/generate` - Text generation (with streaming support)
- `GET /api/tags` - List available models
- `POST /api/show` - Show model information
- `GET /api/ps` - Show running models
- `GET /api/version` - API version information

## Architecture

### Core Components

- **ollama_compliant.py**: Production-ready implementation with full Ollama compatibility
- **main.py**: SDK-based implementation using the Cerebras Python SDK
- **main_http.py**: HTTP-only implementation for minimal dependencies

### API Translation

The wrapper performs several key translations:
- Converts Ollama chat/generate requests to Cerebras chat completions
- Transforms Cerebras streaming responses to match Ollama's chunk format
- Generates proper timestamps, model names, and timing metrics
- Handles both streaming and non-streaming responses

## Development

### Project Structure
```
xcerllama/
├── ollama_compliant.py    # Main production implementation
├── main.py               # SDK-based alternative
├── main_http.py          # HTTP-only alternative
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Docker compose configuration
├── Dockerfile           # Docker image definition
├── .env.example         # Environment variables template
└── CLAUDE.md           # Development documentation
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both streaming and non-streaming requests
5. Submit a pull request

## Supported Models

The wrapper supports any Cerebras model. Common options include:
- `qwen-3-235b-a22b-instruct-2507` (default)
- `llama3.1-8b`
- `llama3.1-70b`

Set your preferred model using the `CAI_MODEL` environment variable.

## Troubleshooting

### Common Issues

1. **"CEREBRAS_API_KEY environment variable is required"**
   - Ensure your `.env` file contains a valid Cerebras API key

2. **Connection errors**
   - Check that the Cerebras API is accessible from your network
   - Verify your API key is valid and has sufficient credits

3. **Model not found**
   - Ensure the `CAI_MODEL` environment variable contains a valid Cerebras model name

### Debugging

Enable debug logging by setting the log level:
```bash
export PYTHONPATH=$PYTHONPATH:. 
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python ollama_compliant.py
```

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Acknowledgments

- [Cerebras](https://cerebras.ai/) for providing high-performance AI inference
- [Ollama](https://ollama.ai/) for the excellent local AI interface design
- The open-source community for inspiration and feedback
