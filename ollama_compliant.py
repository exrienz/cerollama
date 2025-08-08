import os
import time
import json
import httpx
from datetime import datetime, timezone
from typing import Dict, List, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Cerebras-Ollama Wrapper", version="1.0.0")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    options: Optional[Dict] = {}

class GenerateRequest(BaseModel):
    model: str
    prompt: str
    system: Optional[str] = None
    stream: Optional[bool] = False
    context: Optional[List[int]] = None
    options: Optional[Dict] = {}

def get_iso_timestamp():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def get_model_name():
    return os.environ.get("CAI_MODEL", "qwen-3-235b-a22b-instruct-2507").split("-")[0]

def get_timing_metrics():
    return {
        "total_duration": int(time.time() * 1_000_000_000),
        "load_duration": 1_000_000,
        "prompt_eval_count": 10,
        "prompt_eval_duration": 50_000_000,
        "eval_count": 20,
        "eval_duration": 100_000_000
    }

@app.get("/")
async def root():
    return {"message": "Ollama is running"}

@app.get("/api/version")
async def version():
    return {"version": "0.1.17"}

@app.get("/api/tags")
async def list_models():
    model_name = get_model_name()
    return {
        "models": [
            {
                "name": f"{model_name}:latest",
                "model": f"{model_name}:latest", 
                "modified_at": "2024-01-01T10:00:00Z",
                "size": 4_800_000_000,
                "digest": "sha256:abcd1234",
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": model_name,
                    "families": [model_name],
                    "parameter_size": "7B",
                    "quantization_level": "Q4_0"
                }
            }
        ]
    }

@app.post("/api/show")
async def show_model(request: dict):
    model_name = get_model_name()
    return {
        "license": "Apache 2.0",
        "modelfile": f"FROM {model_name}:latest",
        "parameters": "temperature 0.7\ntop_p 0.8",
        "template": "{{ .System }}{{ .Prompt }}",
        "details": {
            "parent_model": "",
            "format": "gguf", 
            "family": model_name,
            "families": [model_name],
            "parameter_size": "7B",
            "quantization_level": "Q4_0"
        }
    }

@app.get("/api/ps")
async def running_models():
    model_name = get_model_name()
    return {
        "models": [
            {
                "name": f"{model_name}:latest",
                "model": f"{model_name}:latest",
                "size": 4_800_000_000,
                "digest": "sha256:abcd1234",
                "expires_at": "2024-12-31T23:59:59Z"
            }
        ]
    }

async def generate_ollama_streaming_response(
    messages: List[Dict], 
    model: str,
    is_generate: bool = False,
    prompt: str = None
) -> AsyncGenerator[str, None]:
    try:
        api_key = os.environ.get("CEREBRAS_API_KEY")
        if not api_key:
            raise ValueError("CEREBRAS_API_KEY environment variable is required")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        if is_generate and prompt:
            cerebras_messages = [{"role": "user", "content": prompt}]
        else:
            cerebras_messages = messages
            
        payload = {
            "model": os.environ.get("CAI_MODEL", "qwen-3-235b-a22b-instruct-2507"),
            "messages": cerebras_messages,
            "stream": True,
            "max_completion_tokens": 20000,
            "temperature": 0.7,
            "top_p": 0.8
        }
        
        model_name = get_model_name()
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST", 
                "https://api.cerebras.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk_data = json.loads(data)
                            if chunk_data.get("choices") and chunk_data["choices"][0].get("delta", {}).get("content"):
                                content = chunk_data["choices"][0]["delta"]["content"]
                                
                                if is_generate:
                                    ollama_chunk = {
                                        "model": f"{model_name}:latest",
                                        "created_at": get_iso_timestamp(),
                                        "response": content,
                                        "done": False
                                    }
                                else:
                                    ollama_chunk = {
                                        "model": f"{model_name}:latest",
                                        "created_at": get_iso_timestamp(),
                                        "message": {
                                            "role": "assistant",
                                            "content": content
                                        },
                                        "done": False
                                    }
                                
                                yield json.dumps(ollama_chunk) + "\n"
                        except json.JSONDecodeError:
                            continue
        
        # Final chunk
        timing = get_timing_metrics()
        if is_generate:
            final_chunk = {
                "model": f"{model_name}:latest", 
                "created_at": get_iso_timestamp(),
                "response": "",
                "done": True,
                "done_reason": "stop",
                "context": [1, 2, 3, 4, 5],
                **timing
            }
        else:
            final_chunk = {
                "model": f"{model_name}:latest",
                "created_at": get_iso_timestamp(), 
                "message": {
                    "role": "assistant",
                    "content": ""
                },
                "done": True,
                "done_reason": "stop",
                **timing
            }
        
        yield json.dumps(final_chunk) + "\n"
        
    except Exception as e:
        error_chunk = {
            "error": str(e)
        }
        yield json.dumps(error_chunk) + "\n"

@app.post("/api/generate")
async def generate(request: GenerateRequest):
    try:
        if request.stream:
            return StreamingResponse(
                generate_ollama_streaming_response(
                    [], 
                    request.model,
                    is_generate=True,
                    prompt=request.prompt
                ),
                media_type="application/x-ndjson",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            api_key = os.environ.get("CEREBRAS_API_KEY")
            if not api_key:
                raise HTTPException(status_code=500, detail="CEREBRAS_API_KEY environment variable is required")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if request.system:
                messages.append({"role": "system", "content": request.system})
            messages.append({"role": "user", "content": request.prompt})
            
            payload = {
                "model": os.environ.get("CAI_MODEL", "qwen-3-235b-a22b-instruct-2507"),
                "messages": messages,
                "stream": False,
                "max_completion_tokens": 20000,
                "temperature": 0.7,
                "top_p": 0.8
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                completion_data = response.json()
            
            model_name = get_model_name()
            timing = get_timing_metrics()
            
            return {
                "model": f"{model_name}:latest",
                "created_at": get_iso_timestamp(),
                "response": completion_data["choices"][0]["message"]["content"],
                "done": True,
                "done_reason": "stop", 
                "context": [1, 2, 3, 4, 5],
                **timing
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_completions(request: ChatRequest):
    try:
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        if request.stream:
            return StreamingResponse(
                generate_ollama_streaming_response(
                    messages, 
                    request.model,
                    is_generate=False
                ),
                media_type="application/x-ndjson", 
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            api_key = os.environ.get("CEREBRAS_API_KEY")
            if not api_key:
                raise HTTPException(status_code=500, detail="CEREBRAS_API_KEY environment variable is required")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": os.environ.get("CAI_MODEL", "qwen-3-235b-a22b-instruct-2507"),
                "messages": messages,
                "stream": False,
                "max_completion_tokens": 20000,
                "temperature": 0.7,
                "top_p": 0.8
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                completion_data = response.json()
            
            model_name = get_model_name()
            timing = get_timing_metrics()
            
            return {
                "model": f"{model_name}:latest",
                "created_at": get_iso_timestamp(),
                "message": {
                    "role": "assistant",
                    "content": completion_data["choices"][0]["message"]["content"]
                },
                "done": True,
                "done_reason": "stop",
                **timing
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6000)