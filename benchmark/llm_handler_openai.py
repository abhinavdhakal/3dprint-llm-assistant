import os
import requests
import time
import json

class LLMHandler:
    def __init__(self):
        # Load environment variables
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

        if not self.api_key:
            print("⚠️ WARNING: OPENAI_API_KEY not found in .env file!")
            print("Add it to .env file: OPENAI_API_KEY='your-key-here'")

    def interpret_modification(self, user_input, full_scad_content, current_params=None):
        """
        RESTRICTED MODE - Only allows small parameter adjustments, always uses full SCAD
        """
        print(f"🔒 RESTRICTED MODE - Safety-limited modifications")
        return self._interpret_with_full_scad(user_input, full_scad_content)

    def _interpret_with_full_scad(self, user_input, full_scad_content):
        """Full SCAD modification mode - RESTRICTED to parameter changes only"""

        system_prompt = """You are a safety-constrained OpenSCAD assistant for concrete 3D printing.

STRICT LIMITATIONS - You can ONLY:
- Modify existing parameter values (sizes, dimensions, positions)
- Adjust parameters by maximum ±20% from current values
- Make small positional adjustments

You CANNOT and MUST REFUSE to:
- Add new features (windows, doors, walls, rooms)
- Remove existing features
- Change the structural design
- Add or remove modules or geometry
- Make changes larger than ±20%

Safety rules for concrete 3D printing:
- Wall thickness: minimum 200mm (never go below this)
- Structural changes require engineering approval
- Large modifications need unrestricted mode

If a request requires actions you cannot perform, you MUST return needs_clarification=true with an explanation."""

        user_prompt = f"""Current OpenSCAD design:

```scad
{full_scad_content}
```

User's modification request:
"{user_input}"

Analyze this request carefully:

1. If it asks to ADD, CREATE, or REMOVE features → REJECT (needs unrestricted mode)
2. If it asks for changes >20% → REJECT (too large for restricted mode)
3. If it only adjusts existing parameters ≤20% → ACCEPT and make changes

Return ONLY a JSON object in this EXACT format:

For ACCEPTED requests:
{{
    "understood": "Summary of the parameter changes",
    "new_scad_code": "Modified OpenSCAD code with \\\\n for newlines",
    "reasoning": "Explanation of parameter adjustments made",
    "needs_clarification": false,
    "changes_summary": [
        "Parameter X changed from A to B (Y% change)",
        "Parameter Z adjusted by W mm"
    ]
}}

For REJECTED requests:
{{
    "understood": "What the user wants to do",
    "reasoning": "This request requires [adding/removing/major changes] which exceeds restricted mode limits",
    "needs_clarification": true,
    "clarification_question": "This modification requires structural changes beyond safe parameter adjustments. Please use unrestricted mode for this request, or rephrase to only adjust existing parameter values by up to 20%."
}}

CRITICAL formatting rules:
1. Use \\\\n for line breaks in new_scad_code (not actual newlines)
2. Escape quotes as \\\\"
3. Return ONLY the JSON object, no markdown, no extra text
4. Be strict about the ±20% limit
5. Reject any request to add/remove features
6. The new_scad_code must be COMPLETE and valid OpenSCAD
7. MUST include the final module call (e.g., "room();" at the end)
8. Return the ENTIRE working SCAD file, not partial code"""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,  # Very low for consistent safety checks
                "max_tokens": 8000,
                "top_p": 0.9
            }

            response = requests.post(self.api_url, headers=headers, json=payload)

            if response.status_code != 200:
                raise Exception(f"API Error: {response.text}")

            data = response.json()
            response_text = data["choices"][0]["message"]["content"]

            print("\n" + "="*80)
            print("🔒 OPENAI RESTRICTED RESPONSE:")
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

            # Check if clarification is needed (rejected request)
            if parsed.get('needs_clarification'):
                print("🚫 Request rejected by restricted mode")
                return parsed

            # Fix if SCAD code returned as array
            if isinstance(parsed.get('new_scad_code'), list):
                print("⚙️ SCAD code returned as array, joining...")
                parsed['new_scad_code'] = ''.join(parsed['new_scad_code'])

            # Fix literal \n in SCAD code - convert to actual newlines
            if 'new_scad_code' in parsed and isinstance(parsed['new_scad_code'], str):
                # Replace literal \n with actual newlines
                parsed['new_scad_code'] = parsed['new_scad_code'].replace('\\n', '\n')
                # Replace literal \t with actual tabs
                parsed['new_scad_code'] = parsed['new_scad_code'].replace('\\t', '\t')
                print("✅ Fixed escaped newlines in SCAD code")

                # Validate SCAD code completeness
                scad_code = parsed['new_scad_code'].strip()

                # Check if it has a module call at the end (e.g., "room();")
                if 'module ' in scad_code and not scad_code.rstrip().endswith(');'):
                    # Find module name
                    import re
                    module_match = re.search(r'module\s+(\w+)\s*\(', scad_code)
                    if module_match:
                        module_name = module_match.group(1)
                        # Append the module call
                        parsed['new_scad_code'] = scad_code + '\n\n// Generate the design\n' + module_name + '();\n'
                        print(f"⚠️ Added missing module call: {module_name}();")

            # Validate that changes are actually restricted (double-check)
            if 'new_scad_code' in parsed:
                if self._has_structural_changes(full_scad_content, parsed['new_scad_code']):
                    print("⚠️ Structural changes detected - overriding to rejection")
                    return {
                        "understood": parsed.get('understood', 'Structural modification detected'),
                        "reasoning": "Security override: Structural changes detected in restricted mode",
                        "needs_clarification": True,
                        "clarification_question": "This modification appears to add or remove structural elements. Please use unrestricted mode for this request."
                    }

            return parsed

        except Exception as e:
            print(f"❌ Error in restricted mode: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_response()

    def _has_structural_changes(self, old_code, new_code):
        """Check if code has structural changes (new modules, features, etc.)"""
        # Count modules
        old_modules = old_code.count('module ')
        new_modules = new_code.count('module ')

        # Count translate/cube statements (rough structural check)
        old_transforms = old_code.count('translate(') + old_code.count('cube(')
        new_transforms = new_code.count('translate(') + new_code.count('cube(')

        # If module count changed or transforms changed by >20%, it's structural
        if old_modules != new_modules:
            return True

        if old_transforms > 0:
            change_ratio = abs(new_transforms - old_transforms) / old_transforms
            if change_ratio > 0.20:  # 20% threshold
                return True

        return False

    def _parse_json_response(self, response_text):
        """Parse JSON from LLM response with robust error handling"""
        # Remove markdown code blocks
        response_text = response_text.replace('```json', '').replace('```', '')

        # Remove preambles
        if 'Here is' in response_text[:50] or 'Here\'s' in response_text[:50]:
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
            "reasoning": "There was an error processing your request. Please try again.",
            "needs_clarification": True,
            "clarification_question": "Could you rephrase that request?"
        }


def call_openai_llm(prompt, scad_content=None):
    """
    Call OpenAI LLM for SCAD modification.
    Returns dict with llm_output, stl_time, total_time, stl_text
    """
    import time
    start_time = time.time()

    handler = LLMHandler()

    try:
        result = handler.interpret_modification(prompt, scad_content or "")

        # Extract the modified SCAD from the result
        llm_output = result.get("new_scad_code", "")

        # Simulate STL generation (replace with actual logic)
        stl_start = time.time()
        # Your STL generation code here
        stl_time = (time.time() - stl_start) * 1000  # ms

        total_time = (time.time() - start_time) * 1000  # ms

        return {
            "llm_output": llm_output,
            "stl_time": stl_time,
            "total_time": total_time,
            "stl_text": "Generated STL content here"  # Replace with actual STL
        }

    except Exception as e:
        return {
            "error": str(e),
            "llm_output": "",
            "stl_time": 0,
            "total_time": (time.time() - start_time) * 1000
        }