import torch
import os, sys, json, time
import torch.nn as nn
from fastapi import FastAPI
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation.utils import GenerationConfig

class Settings(BaseSettings):
    model_path: str
    model_name: str
    class Config:
        env_file = ".env"
        env_prefix = ""

class InputText(BaseModel):
    input_text: str
    max_new_tokens: int 
    model_max_length: int
    do_sample: bool
    temperature: float

settings = Settings()  
model_path = settings.model_path
model_name = settings.model_name
print(f"loading {model_path}...")

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    device_map="cuda:0"
)

tokenizer = AutoTokenizer.from_pretrained(model_path)
model.eval()

app = FastAPI()

@app.post("/generate_text")
async def generate_text(data: InputText):
    begin_time = time.time()
    input_text = data.input_text

    model.generation_config = GenerationConfig.from_pretrained(model_path)
    model.generation_config.do_sample = data.do_sample
    model.generation_config.temperature = data.temperature
    model.generation_config.model_max_length = data.model_max_length
    model.generation_config.max_new_tokens = data.max_new_tokens

    messages = [
        {"role": "system", "content": "你是一个忠实可靠的人工智能助手，请你根据以下指令，忠实地完成任务。"},
        {"role": "user", "content": input_text}
    ]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    generated_ids = model.generate(
        **model_inputs,
        output_scores=True,
        return_dict_in_generate=True,
        max_new_tokens=model.generation_config.max_new_tokens
    )
    
    scores = generated_ids['scores']
    generated_ids = generated_ids['sequences']
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    scores = scores[0]
    probs = nn.functional.softmax(scores)[0]
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    end_time = time.time()
    cost_time = end_time - begin_time
    return {
        "message": "success",
        "response": response,
        "input_text": input_text,
        "cost_time": cost_time,
        "model_name": model_name,
        "probs": probs,
        "max_new_tokens": data.max_new_tokens,
    }


@app.get("/health")
async def health_check():
    """
    detect the status of the agents
    """
    current_time = time.time()
    cuda_available = torch.cuda.is_available()
    
    gpu_memory = {}
    if cuda_available:
        try:
            gpu_memory = {
                "allocated_mb": torch.cuda.memory_allocated() / 1024**2,
                "max_allocated_mb": torch.cuda.max_memory_allocated() / 1024**2,
                "cached_mb": torch.cuda.memory_reserved() / 1024**2,
                "device_count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device(),
            }
        except Exception as e:
            gpu_memory = {"status": "error", 
                          "message": str(e)}
    
    return {
        "status": "healthy",
        "model_loaded": model is not None and tokenizer is not None,
        "model_name": model_name,
        "cuda_available": cuda_available,
        "gpu_memory": gpu_memory,
        "timestamp": current_time
    }
