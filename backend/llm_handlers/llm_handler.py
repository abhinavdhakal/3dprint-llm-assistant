import json
import requests

class LLMHandler:
    def __init__(self):
        self.api_url = "http://localhost:11434/api/generate"
        self.model = "llama3.1"
    
    def interpret_modification(self, user_input, full_scad_content):
        """
        Ask Ollama to interpret the operator's modification request
        MODERATE MODE: Balanced modifications to SCAD code
        """
        prompt = f"""You are an expert in OpenSCAD and concrete 3D printing design.

Current SCAD file:
```openscad
{full_scad_content}
```

Operator's modification request: "{user_input}"

You can make moderate design changes including:
- Adjusting dimensions and parameters
- Minor structural modifications
- Reasonable design improvements

Analyze the request and return MODIFIED SCAD CODE.

Return ONLY valid JSON in this exact format (no other text):
{{
    "understood": "brief description of what you understood",
    "new_scad_code": "complete modified SCAD code here",
    "reasoning": "explanation of changes made",
    "needs_clarification": false,
    "clarification_question": null
}}

IMPORTANT:
- Return the COMPLETE SCAD code, not just a snippet
- Maintain proper OpenSCAD syntax
- Keep measurements in millimeters
- Preserve the overall structure and style
- Be conservative - don't make extreme changes unless explicitly requested
- If unclear, set needs_clarification to true

JSON response:"""

        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,
                    "num_predict": 4000  # Allow longer responses for full SCAD code
                },
                timeout=120  # Longer timeout for code generation
            )
            
            if response.status_code != 200:
                print(f"Ollama API error: {response.status_code}")
                return self._fallback_response()
            
            result = response.json()
            response_text = result.get('response', '')
            
            # Parse JSON from response
            try:
                # Find JSON in the response
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start == -1 or end == 0:
                    print(f"No JSON found in response: {response_text[:200]}")
                    return self._fallback_response()
                
                json_str = response_text[start:end]
                parsed = json.loads(json_str)
                return parsed
                
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Response was: {response_text[:500]}")
                return self._fallback_response()
                
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            print("Make sure Ollama is running: ollama serve")
            return self._fallback_response()
    
    def _fallback_response(self):
        """Return a safe fallback when LLM fails"""
        return {
            "understood": "Error communicating with LLM",
            "new_scad_code": None,
            "reasoning": "Please check that Ollama is running",
            "needs_clarification": True,
            "clarification_question": "Could you rephrase that request?"
        }