import json
import os
from dotenv import load_dotenv
from openai import OpenAI

class LLMHandler:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Initialize OpenAI client with Groq base URL
        self.client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
        
        if not os.environ.get("GROQ_API_KEY"):
            print("⚠️ WARNING: GROQ_API_KEY not found in .env file!")
            print("Add it to backend/.env file: GROQ_API_KEY='your-key-here'")
        
        # Groq models - using current supported models
        self.model = "llama-3.3-70b-versatile"  # Latest, fast, high quality
        # Alternative: "llama-3.1-8b-instant" for even faster responses
        # Alternative: "mixtral-8x7b-32768" for longer context
    
    def interpret_modification(self, user_input, full_scad_content, current_params=None):
        """
        Ask Groq LLM to interpret the operator's modification request
        ADVANCED MODE with intelligent routing
        """
        # Quick keyword check - if user says "add" or "create", use full SCAD
        add_keywords = ['add a', 'add another', 'create a', 'create another', 'new window', 'new door', 'new wall', 'add second', 'another window']
        user_input_lower = user_input.lower()
        
        if any(keyword in user_input_lower for keyword in add_keywords):
            print(f"🎯 Keyword detected - using Full SCAD mode")
            return self._interpret_with_full_scad(user_input, full_scad_content)
        
        # For simple changes, use parameter mode (faster)
        print(f"📊 Using parameter mode for simple changes")
        return self._interpret_with_parameters(user_input, current_params)
    
    def _interpret_with_parameters(self, user_input, current_params):
        """Parameter modification mode - fast for simple changes"""
        
        system_prompt = """You are an expert in OpenSCAD and concrete 3D printing design.
Analyze modification requests and return parameter changes in JSON format.
Only modify existing parameters - do not add new features."""

        user_prompt = f"""Current design parameters (all in millimeters):
{json.dumps(current_params, indent=2)}

User's request: "{user_input}"

Return ONLY valid JSON in this format:
{{
    "understood": "what you understood",
    "modifications": {{"parameter_name": new_value}},
    "reasoning": "brief explanation",
    "needs_clarification": false
}}

Only modify existing parameters. Keep all values in millimeters."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            response_text = response.choices[0].message.content
            
            print("\n" + "="*80)
            print("GROQ RESPONSE (Parameter Mode):")
            print("="*80)
            print(response_text)
            print("="*80 + "\n")
            
            # Parse JSON
            parsed = self._parse_json_response(response_text)
            
            # Ensure required fields
            if 'mode' not in parsed:
                parsed['mode'] = 'parameter_modification'
            
            return parsed
            
        except Exception as e:
            print(f"❌ Error in parameter mode: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_response()
    
    def _interpret_with_full_scad(self, user_input, full_scad_content):
        """Full SCAD modification mode - can add/remove features"""
        
        system_prompt = """You are an expert OpenSCAD programmer.
Modify SCAD code based on user requests. You can add/remove features.
Return complete modified SCAD code with proper JSON escaping."""

        user_prompt = f"""Current SCAD code:
{full_scad_content}

User's request: {user_input}

Return ONLY valid JSON with the complete modified SCAD code:
{{
    "understood": "what you understood",
    "new_scad_code": "complete SCAD code with \\\\n for newlines and \\\\" for quotes",
    "reasoning": "brief explanation",
    "needs_clarification": false,
    "changes_summary": ["list of changes"]
}}

CRITICAL: Use \\\\n for line breaks in new_scad_code, not actual newlines. Escape all quotes."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4096  # Need more tokens for full SCAD code
            )
            
            response_text = response.choices[0].message.content
            
            print("\n" + "="*80)
            print("GROQ RESPONSE (Full SCAD Mode):")
            print("="*80)
            print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
            print("="*80 + "\n")
            
            # Parse JSON
            parsed = self._parse_json_response(response_text)
            
            # Ensure required fields
            if 'mode' not in parsed:
                parsed['mode'] = 'code_modification'
            if 'changes_summary' not in parsed:
                parsed['changes_summary'] = []
            
            # Fix if SCAD code returned as array
            if isinstance(parsed.get('new_scad_code'), list):
                print("SCAD code returned as array, joining...")
                parsed['new_scad_code'] = ''.join(parsed['new_scad_code'])
            
            # Fix literal \n in SCAD code - convert to actual newlines
            if 'new_scad_code' in parsed and isinstance(parsed['new_scad_code'], str):
                # Replace literal \n with actual newlines
                parsed['new_scad_code'] = parsed['new_scad_code'].replace('\\n', '\n')
                # Replace literal \t with actual tabs
                parsed['new_scad_code'] = parsed['new_scad_code'].replace('\\t', '\t')
                print("✅ Fixed escaped newlines in SCAD code")
            
            return parsed
            
        except Exception as e:
            print(f"❌ Error in full SCAD mode: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_response()
    
    def _parse_json_response(self, response_text):
        """Parse JSON from LLM response with robust error handling"""
        # Remove markdown code blocks
        response_text = response_text.replace('```json', '').replace('```', '')
        
        # Remove preambles
        if 'Here is' in response_text[:50]:
            lines = response_text.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    response_text = '\n'.join(lines[i:])
                    break
        
        response_text = response_text.strip()
        
        # Remove trailing notes after closing brace
        last_brace = response_text.rfind('}')
        if last_brace != -1:
            response_text = response_text[:last_brace + 1]
        
        # Find JSON
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")
        
        json_str = response_text[start:end]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            if 'control character' in str(e):
                print("⚠️ Fixing literal newlines in JSON...")
                json_str = self._fix_literal_newlines(json_str)
                return json.loads(json_str)
            raise
    
    def _fix_literal_newlines(self, json_str):
        """Fix JSON where string values have literal newlines"""
        import re
        
        # Find new_scad_code field with literal newlines
        scad_start = json_str.find('"new_scad_code":')
        if scad_start == -1:
            return json_str
        
        quote_start = json_str.find('"', scad_start + len('"new_scad_code":'))
        if quote_start == -1:
            return json_str
        
        code_start = quote_start + 1
        
        # Find where SCAD code ends (next JSON field)
        next_field = re.search(r',\s*"(reasoning|needs_clarification|changes_summary)":', json_str[code_start:])
        if not next_field:
            return json_str
        
        code_end = code_start + next_field.start()
        scad_code = json_str[code_start:code_end].rstrip().rstrip('"').rstrip()
        
        # Properly escape
        scad_code_escaped = json.dumps(scad_code)
        
        # Reconstruct
        fixed_json = (
            json_str[:scad_start] +
            '"new_scad_code": ' +
            scad_code_escaped +
            json_str[code_end:].lstrip().lstrip('"')
        )
        
        print("✅ Fixed literal newlines")
        return fixed_json
    
    def _fallback_response(self):
        """Return safe fallback when LLM fails"""
        return {
            "understood": "Error communicating with LLM",
            "mode": "error",
            "modifications": {},
            "reasoning": "Please check your Groq API key and connection",
            "needs_clarification": True,
            "clarification_question": "Could you rephrase that request?"
        }
