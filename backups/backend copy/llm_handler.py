import json
import requests

class LLMHandler:
    def __init__(self):
        self.api_url = "http://localhost:11434/api/generate"
        self.model = "llama3.1"
    
    def interpret_modification(self, user_input, current_params):
        """
        Ask Ollama to interpret the operator's modification request
        """
        prompt = f"""You are an expert in concrete 3D printing design modifications.

Current room design parameters (all in millimeters):
{json.dumps(current_params, indent=2)}

Operator's modification request: "{user_input}"

Analyze this request and return a JSON object with the modifications needed.

Return ONLY valid JSON in this exact format (no other text):
{{
    "understood": "brief description of what you understood",
    "modifications": {{
        "parameter_name": new_value_in_mm
    }},
    "reasoning": "why these changes make sense",
    "needs_clarification": false,
    "clarification_question": null
}}

If the request is unclear, set needs_clarification to true and provide a clarification_question.

Only modify parameters that exist in the current design.
Keep all values in millimeters.
Be conservative - don't make extreme changes unless explicitly requested.

JSON response:"""

        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3
                },
                timeout=60
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
                    print(f"No JSON found in response: {response_text}")
                    return self._fallback_response()
                
                json_str = response_text[start:end]
                parsed = json.loads(json_str)
                return parsed
                
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Response was: {response_text}")
                return self._fallback_response()
                
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            print("Make sure Ollama is running: ollama serve")
            return self._fallback_response()
    
    def _fallback_response(self):
        """Return a safe fallback when LLM fails"""
        return {
            "understood": "Error communicating with LLM",
            "modifications": {},
            "reasoning": "Please check that Ollama is running",
            "needs_clarification": True,
            "clarification_question": "Could you rephrase that request?"
        }