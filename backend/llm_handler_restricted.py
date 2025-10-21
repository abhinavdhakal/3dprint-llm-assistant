import json
import requests

class LLMHandler:
    def __init__(self):
        self.api_url = "http://localhost:11434/api/generate"
        self.model = "llama3.1"
    
    def interpret_modification(self, user_input, full_scad_content=None, current_params=None):
        """
        Ask Ollama to interpret the operator's modification request
        RESTRICTED MODE: Only allows minor parameter adjustments (±20%), rejects major changes
        NOTE: This mode uses parameter extraction for faster, more reliable responses
        """
        # Use provided parameters or extract them if needed
        if not current_params and full_scad_content:
            import re
            current_params = {}
            pattern = r'(\w+)\s*=\s*(\d+(?:\.\d+)?)\s*;'
            matches = re.findall(pattern, full_scad_content)
            for key, value in matches:
                try:
                    current_params[key] = float(value) if '.' in value else int(value)
                except ValueError:
                    pass
        
        prompt = f"""You are an expert in concrete 3D printing design modifications with RESTRICTED PERMISSIONS.

Current room design parameters (all in millimeters):
{json.dumps(current_params, indent=2)}

Operator's modification request: "{user_input}"

IMPORTANT RESTRICTIONS:
- You can ONLY adjust existing parameters by maximum ±20% of their current value
- You CANNOT add new features (windows, doors, roofs, etc.)
- You CANNOT remove existing features
- You CANNOT make structural changes
- You can only fine-tune dimensions within safe limits

If the operator requests major changes (adding/removing features, structural modifications, >20% changes), 
you MUST reject it by setting needs_clarification to true with an explanation.

Analyze this request and return a JSON object.

Return ONLY valid JSON in this exact format (no other text):
{{
    "understood": "brief description of what you understood",
    "modifications": {{
        "parameter_name": new_value_in_mm
    }},
    "reasoning": "why these changes are within allowed limits OR why they are rejected",
    "needs_clarification": false,
    "clarification_question": null,
    "rejected": false,
    "rejection_reason": null
}}

If the request exceeds restrictions:
- Set needs_clarification to true
- Set rejected to true
- Provide rejection_reason explaining which restriction was violated
- Set clarification_question asking for a minor adjustment instead

Only modify parameters that exist in the current design.
Keep all values in millimeters.
Be very conservative - safety is paramount.

JSON response:"""

        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1  # Very low creativity for restricted mode
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
                
                # Ensure restriction fields exist
                if 'rejected' not in parsed:
                    parsed['rejected'] = False
                if 'rejection_reason' not in parsed:
                    parsed['rejection_reason'] = None
                
                # Validate modifications don't exceed ±20%
                if parsed['modifications']:
                    validated_mods = {}
                    for param, new_value in parsed['modifications'].items():
                        if param in current_params:
                            current_value = current_params[param]
                            max_change = abs(current_value * 0.20)
                            change = abs(new_value - current_value)
                            
                            if change <= max_change:
                                validated_mods[param] = new_value
                            else:
                                print(f"⚠️ Rejected {param} change: {change}mm exceeds ±20% limit ({max_change}mm)")
                    
                    parsed['modifications'] = validated_mods
                
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
            "clarification_question": "Could you rephrase that request?",
            "rejected": False,
            "rejection_reason": None
        }
