import json
import requests

class LLMHandler:
    def __init__(self):
        self.api_url = "http://localhost:11434/api/generate"
        self.model = "llama3.1"
    
    def interpret_modification(self, user_input, full_scad_content, current_params=None):
        """
        Ask Ollama to interpret the operator's modification request
        ADVANCED MODE: Can add/remove features like windows, roofs, walls, doors, etc.
        
        This handler intelligently chooses between:
        - Parameter modification mode (fast, for simple changes)
        - Full SCAD modification mode (powerful, for structural changes)
        """
        # Quick keyword check - if user says "add" or "create" or "new", likely needs full SCAD
        add_keywords = ['add a', 'add another', 'create a', 'create another', 'new window', 'new door', 'new wall', 'add second', 'another window']
        user_input_lower = user_input.lower()
        
        if any(keyword in user_input_lower for keyword in add_keywords):
            print(f"🎯 Keyword detected - automatically choosing Full SCAD mode")
            return self._interpret_with_full_scad(user_input, full_scad_content)
        
        # First, ask LLM to determine if this needs full SCAD modification or just parameters
        decision_prompt = f"""Analyze this modification request and determine if it requires full SCAD code modification.

Current parameters:
{json.dumps(current_params, indent=2) if current_params else "Unknown"}

REQUEST: "{user_input}"

Return ONLY this JSON:
{{
    "needs_full_scad": true or false,
    "reason": "brief explanation"
}}

IMPORTANT RULES:
needs_full_scad = TRUE if:
- Adding NEW features (new window, new door, new wall, roof, etc.)
- Removing features
- Structural/architectural changes
- Creating components that don't exist

needs_full_scad = FALSE if:
- Modifying EXISTING parameter values only
- Resizing existing features (make existing window bigger/smaller)
- Simple dimension adjustments to things that already exist

CRITICAL: "Add a window" or "add a door" means needs_full_scad=TRUE because it's creating something new!

JSON:"""

        try:
            decision_response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": decision_prompt,
                    "stream": False,
                    "temperature": 0.2,
                    "num_predict": 200
                },
                timeout=30
            )
            
            if decision_response.status_code == 200:
                decision_text = decision_response.json().get('response', '')
                start = decision_text.find('{')
                end = decision_text.rfind('}') + 1
                if start != -1 and end > 0:
                    decision = json.loads(decision_text[start:end])
                    needs_full_scad = decision.get('needs_full_scad', True)
                    print(f"🤖 Decision: {'Full SCAD' if needs_full_scad else 'Parameter'} mode - {decision.get('reason')}")
                else:
                    needs_full_scad = True  # Default to full SCAD if can't parse
            else:
                needs_full_scad = True  # Default to full SCAD on error
                
        except:
            needs_full_scad = True  # Default to full SCAD on error
        
        # Route to appropriate mode
        if needs_full_scad:
            return self._interpret_with_full_scad(user_input, full_scad_content)
        else:
            return self._interpret_with_parameters(user_input, current_params)
    
    def _interpret_with_full_scad(self, user_input, full_scad_content):
        """Full SCAD modification mode - can add/remove features"""
        prompt = f"""Modify this OpenSCAD code based on the request.

CURRENT CODE:
{full_scad_content}

REQUEST: {user_input}

Return JSON with complete modified SCAD code:
{{
    "understood": "what you understood",
    "new_scad_code": "complete SCAD code with \\n for newlines",
    "reasoning": "explanation",
    "needs_clarification": false,
    "changes_summary": ["change 1", "change 2"]
}}

CRITICAL: 
- Return COMPLETE SCAD code in "new_scad_code"
- Use \\n for line breaks (not actual newlines)
- Escape quotes as \\"
- Keep all measurements in mm

JSON:"""

        print("\n" + "="*80)
        print("PROMPT SENT TO LLM (Full SCAD Mode):")
        print("="*80)
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        print("="*80 + "\n")

        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,  # Lower temperature for more consistent output
                    "top_p": 0.9,        # Focus on most likely tokens
                    "top_k": 40,         # Limit vocabulary
                    "num_predict": 4096, # Increased - need full SCAD code
                    "repeat_penalty": 1.1  # Reduce repetition
                },
                timeout=120  # Increased timeout
            )
            
            if response.status_code != 200:
                print(f"Ollama API error: {{response.status_code}}")
                return self._fallback_response()
            
            result = response.json()
            response_text = result.get('response', '')
            
            print("\n" + "="*80)
            print("RAW LLM RESPONSE:")
            print("="*80)
            print(response_text)
            print("="*80 + "\n")
            
            # Clean up response - remove markdown code blocks and preamble
            response_text = response_text.replace('```json', '').replace('```', '')
            # Remove common preambles
            if 'Here is' in response_text[:50]:
                lines = response_text.split('\n')
                # Find the line with the opening brace
                for i, line in enumerate(lines):
                    if line.strip().startswith('{'):
                        response_text = '\n'.join(lines[i:])
                        break
            response_text = response_text.strip()
            
            # Remove trailing notes after closing brace
            last_brace = response_text.rfind('}')
            if last_brace != -1:
                response_text = response_text[:last_brace + 1]
            
            print("\n" + "="*80)
            print("CLEANED RESPONSE (before JSON parsing):")
            print("="*80)
            print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
            print("="*80 + "\n")
            
            # Parse JSON from response
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start == -1 or end == 0:
                    print(f"No JSON found in response")
                    return self._fallback_response()
                
                json_str = response_text[start:end]
                
                # CRITICAL FIX: Check if JSON has literal newlines in string values
                # Try to parse first to see if we get the control character error
                try:
                    parsed = json.loads(json_str)
                    print("✅ JSON parsed successfully on first try!")
                    
                except json.JSONDecodeError as e:
                    if 'control character' in str(e) or 'Invalid \\escape' in str(e):
                        print("⚠️ Detected literal newlines/escaping issues, attempting to fix...")
                        json_str = self._fix_literal_newlines_in_json(json_str)
                        parsed = json.loads(json_str)
                        print("✅ JSON parsed successfully after fixing!")
                    else:
                        # Try backtick fix as last resort
                        print("⚠️ Other JSON error, trying backtick fix...")
                        json_str = self._fix_backtick_code(json_str)
                        parsed = json.loads(json_str)
                        print("✅ JSON parsed after backtick fix!")
                
                # Fix if new_scad_code is returned as an array of strings
                if isinstance(parsed.get('new_scad_code'), list):
                    print("SCAD code returned as array, joining into single string...")
                    parsed['new_scad_code'] = ''.join(parsed['new_scad_code'])
                
                # Ensure required fields exist
                if 'mode' not in parsed:
                    parsed['mode'] = 'code_modification'
                if 'changes_summary' not in parsed:
                    parsed['changes_summary'] = []
                
                return parsed
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                print(f"Failed JSON was: {json_str[:500] if 'json_str' in locals() else response_text[:500]}")
                return self._fallback_response()
                
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return self._fallback_response()
    
    def _interpret_with_parameters(self, user_input, current_params):
        """Standard mode: Modify only parameters"""
        prompt = f"""You are an expert in concrete 3D printing design modifications with FULL DESIGN CAPABILITIES.

Current room design parameters (all in millimeters):
{json.dumps(current_params, indent=2)}

Operator's modification request: "{user_input}"

You can make parameter changes to the design.

Analyze this request and return a JSON object with the modifications needed.

Return ONLY valid JSON in this exact format (no other text):
{{
    "understood": "brief description of what you understood",
    "mode": "parameter_modification",
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
            
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start == -1 or end == 0:
                    print(f"No JSON found in response: {response_text}")
                    return self._fallback_response()
                
                json_str = response_text[start:end]
                parsed = json.loads(json_str)
                
                if 'mode' not in parsed:
                    parsed['mode'] = 'parameter_modification'
                
                return parsed
                
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                return self._fallback_response()
                
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return self._fallback_response()
    
    def _fallback_response(self):
        """Return a safe fallback when LLM fails"""
        return {
            "understood": "Error communicating with LLM",
            "mode": "error",
            "modifications": {},
            "reasoning": "Please check that Ollama is running",
            "needs_clarification": True,
            "clarification_question": "Could you rephrase that request?"
        }
    
    def _fallback_with_rephrase(self):
        """Return a fallback asking user to rephrase due to formatting issues"""
        return {
            "understood": "LLM response formatting error",
            "mode": "error",
            "modifications": {},
            "reasoning": "The LLM returned improperly formatted code. This is a known issue.",
            "needs_clarification": True,
            "clarification_question": "Please try rephrasing your request or try a different modification."
        }
    
    def _fix_backtick_code(self, json_str):
        """Fix JSON with backtick-wrapped SCAD code by converting to proper JSON string"""
        import re
        
        # Find the pattern: "new_scad_code": `...`
        pattern = r'"new_scad_code":\s*`([^`]*)`'
        match = re.search(pattern, json_str, re.DOTALL)
        
        if match:
            scad_code = match.group(1)
            # Properly escape the SCAD code for JSON
            scad_code_escaped = json.dumps(scad_code)[1:-1]  # Remove the quotes json.dumps adds
            # Replace the backtick version with properly escaped version
            fixed_json = re.sub(
                pattern,
                f'"new_scad_code": "{scad_code_escaped}"',
                json_str,
                flags=re.DOTALL
            )
            print("Successfully fixed backtick-wrapped SCAD code")
            return fixed_json
        
        return json_str
    
    def _fix_literal_newlines_in_json(self, json_str):
        """Fix JSON where new_scad_code has literal newlines instead of escaped \\n"""
        import re
        
        # Find where new_scad_code starts
        scad_start = json_str.find('"new_scad_code":')
        if scad_start == -1:
            return json_str
        
        # Find the opening quote after the colon
        quote_start = json_str.find('"', scad_start + len('"new_scad_code":'))
        if quote_start == -1:
            return json_str
        
        # Now find the SCAD code section - it ends at the next unescaped quote
        # But because of literal newlines, we need to find where it actually ends
        # Look for the pattern: ",\n    "reasoning": or similar
        code_start = quote_start + 1
        
        # Find the end - look for the closing structure
        # The SCAD code ends before the next JSON field
        next_field_pattern = r',\s*"(reasoning|needs_clarification|changes_summary)":'
        next_field_match = re.search(next_field_pattern, json_str[code_start:])
        
        if not next_field_match:
            return json_str
        
        code_end = code_start + next_field_match.start()
        
        # Extract the SCAD code (with literal newlines)
        scad_code = json_str[code_start:code_end]
        
        # Remove trailing quote and whitespace if present
        scad_code = scad_code.rstrip().rstrip('"').rstrip()
        
        # Now properly escape it
        scad_code_escaped = json.dumps(scad_code)  # This will add quotes and escape everything
        
        # Reconstruct the JSON
        fixed_json = (
            json_str[:scad_start] +
            '"new_scad_code": ' +
            scad_code_escaped +
            json_str[code_end:].lstrip().lstrip('"')
        )
        
        print("✅ Fixed literal newlines in SCAD code")
        return fixed_json
