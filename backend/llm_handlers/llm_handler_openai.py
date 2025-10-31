import os
import requests
import time

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def call_openai_llm(prompt, scad_content=None):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Build the prompt with SCAD content if provided
    full_prompt = prompt
    if scad_content:
        full_prompt = f"""
You are an expert in OpenSCAD for concrete 3D printing. Modify the following SCAD code based on the user's request.

Current SCAD code:
{scad_content}

User request: {prompt}

Return only the modified SCAD code, no explanations.
"""
    
    messages = [{"role": "user", "content": full_prompt}]
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2048
    }
    start = time.time()
    response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
    latency = time.time() - start
    if response.status_code == 200:
        data = response.json()
        output = data["choices"][0]["message"]["content"]
        return {
            "llm_output": output,
            "stl_time": 0,  # Placeholder
            "total_time": round(latency * 1000, 1),
            "stl_text": ""  # Placeholder
        }
    else:
        return {
            "error": response.text,
            "llm_output": "",
            "stl_time": 0,
            "total_time": round(latency * 1000, 1)
        }
