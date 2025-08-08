import os
import time
import json
from typing import Dict, List, Optional, Union, AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from cerebras.cloud.sdk import Cerebras
import uvicorn

app = FastAPI(title="Cerebras-Ollama Wrapper", version="1.0.0")

def get_cerebras_client():
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        raise ValueError("CEREBRAS_API_KEY environment variable is required")
    
    try:
        # Try basic initialization first
        return Cerebras(api_key=api_key)
    except Exception as e:
        # If that fails, try with minimal params
        try:
            from cerebras.cloud.sdk._base_client import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
            return Cerebras(
                api_key=api_key,
                max_retries=DEFAULT_MAX_RETRIES,
                timeout=DEFAULT_TIMEOUT
            )
        except Exception as e2:
            # Last resort - try with no optional params
            import cerebras.cloud.sdk._client as client_module
            client_cls = getattr(client_module, 'Cerebras')
            return client_cls(api_key=api_key)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    max_tokens: Optional[int] = 20000
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.8

class Choice(BaseModel):
    index: int
    message: Optional[Dict] = None
    delta: Optional[Dict] = None
    finish_reason: Optional[str] = None

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: Optional[Usage] = None

@app.get("/")
async def root():
    return {"message": "Cerebras-Ollama API Wrapper"}

@app.get("/api/tags")
async def list_models():
    return {
        "models": [
            {
                "name": os.environ.get("CAI_MODEL", "qwen-3-235b-a22b-instruct-2507"),
                "modified_at": "2024-01-01T00:00:00Z",
                "size": 0,
                "digest": "sha256:dummy"
            }
        ]
    }

async def generate_streaming_response(
    messages: List[Dict], 
    model: str,
    temperature: float = 0.7,
    top_p: float = 0.8,
    max_tokens: int = 20000
) -> AsyncGenerator[str, None]:
    try:
        client = get_cerebras_client()
        cerebras_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
        
        stream = client.chat.completions.create(
            messages=cerebras_messages,
            model=os.environ.get("CAI_MODEL", model),
            stream=True,
            max_completion_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p
        )
        
        created_time = int(time.time())
        chat_id = f"chatcmpl-{int(time.time() * 1000)}"
        
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                ollama_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": chunk.choices[0].delta.content
                        },
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(ollama_chunk)}\n\n"
        
        final_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created_time,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "api_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"

@app.post("/api/chat")
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    try:
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        if request.stream:
            return StreamingResponse(
                generate_streaming_response(
                    messages, 
                    request.model,
                    request.temperature,
                    request.top_p,
                    request.max_tokens
                ),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            client = get_cerebras_client()
            cerebras_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
            
            completion = client.chat.completions.create(
                messages=cerebras_messages,
                model=os.environ.get("CAI_MODEL", request.model),
                stream=False,
                max_completion_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p
            )
            
            return ChatResponse(
                id=f"chatcmpl-{int(time.time() * 1000)}",
                object="chat.completion",
                created=int(time.time()),
                model=request.model,
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": completion.choices[0].message.content
                    },
                    "finish_reason": "stop"
                }],
                usage=Usage(
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0
                )
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6000)