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
        UNRESTRICTED MODE - Can do any modifications, always uses full SCAD
        """
        print(f"🔓 UNRESTRICTED MODE - Full SCAD processing")
        return self._interpret_with_full_scad(user_input, full_scad_content)

    def _interpret_with_full_scad(self, user_input, full_scad_content):
        """Full SCAD modification mode - can add/remove/modify anything"""

        system_prompt = """You are an expert OpenSCAD programmer specializing in concrete 3D printing design.

OPENSCAD FUNDAMENTALS:
- Statements end with semicolons
- Use lowerCamel or snake_case consistently
- Variables are immutable after definition
- Add unit comments (mm) for all dimensions
- Keep line length under 100 characters

PRIMITIVES:
- cube([x, y, z], center = true);
- sphere(r = R, $fn = N);
- cylinder(h = H, r = R, r2 = R2, center = true, $fn = N);
- polyhedron(points = [...], faces = [...]);

TRANSFORMS:
- translate([x, y, z]) { ... }
- rotate([a, b, c]) { ... }
- scale([sx, sy, sz]) { ... }
- mirror([nx, ny, nz]) { ... }

BOOLEAN OPERATIONS (order matters):
- union() { ... } groups objects
- difference() { keep; cut1; cut2; ... } subtracts cut1, cut2 from keep
- intersection() { ... }

CRITICAL OpenSCAD structure rules for concrete buildings:
- Use difference() to REMOVE material (doors, windows, interior cavity)
- Use union() to ADD material (dividing walls, columns, roofs, extra features)
- Dividing walls MUST be ADDED with union(), NOT subtracted
- Example for adding dividing walls:
  union() {
      difference() {
          cube([...]); // Outer shell
          translate(...) cube([...]); // Hollow interior
          translate(...) cube([...]); // Door/window openings
      }
      // Add dividing walls HERE (inside union, outside difference):
      translate(...) cube([divider_thickness, room_width, wall_height]);
  }

POLYHEDRON syntax (for roofs, pyramids, etc):
- Use polyhedron(points=[...], faces=[...]) NOT triangles parameter
- points: list of 3D coordinates [[x,y,z], ...]
- faces: list of point indices for each face
- Faces must be defined with correct winding order (counterclockwise from outside)
- Example pyramid with base:
  polyhedron(
    points=[[0,0,0], [10,0,0], [10,10,0], [0,10,0], [5,5,10]],
    faces=[
      [0,1,4],    // side 1
      [1,2,4],    // side 2
      [2,3,4],    // side 3
      [3,0,4],    // side 4
      [0,3,2,1]   // base (must be included!)
    ]
  );

CONCRETE 3D PRINTING design principles:
- Wall thickness: minimum 200mm for structural integrity
- Door height: typically 2100mm (standard residential)
- Door width: typically 800-900mm
- Window sill height: typically 900mm from floor
- Wall height: typically 2800mm (standard ceiling)
- All measurements in millimeters

PARAMETRIZATION:"""

        user_prompt = f"""Current OpenSCAD design:

```scad
{full_scad_content}
```

User's modification request:
"{user_input}"

Analyze this request and provide a complete OpenSCAD design that implements the requested changes.

Return ONLY a JSON object in this EXACT format:

{{
    "understood": "Clear summary of what you're implementing",
    "new_scad_code": "Complete OpenSCAD code with ALL necessary modifications - use \\\\n for line breaks",
    "reasoning": "Detailed explanation of the changes made and why",
    "needs_clarification": false,
    "changes_summary": [
        "What was added/changed and why",
        "Technical details of modifications",
        "Any design considerations"
    ]
}}

CRITICAL REQUIREMENTS:
1. Return the ENTIRE working SCAD file, not partial code
2. Include the final module call (e.g., "house();" at the end)
3. Use proper OpenSCAD syntax and structure
4. Add comments explaining complex parts
5. Ensure the design is 3D printable (no floating parts, proper supports)
6. Use \\\\n for line breaks in new_scad_code (not actual newlines)
7. Escape quotes as \\\\"
8. Make the code production-ready and well-commented"""

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
                "temperature": 0.3,  # Slightly higher for creativity but still consistent
                "max_tokens": 8000,
                "top_p": 0.9
            }

            response = requests.post(self.api_url, headers=headers, json=payload)

            if response.status_code != 200:
                raise Exception(f"API Error: {response.text}")

            data = response.json()
            response_text = data["choices"][0]["message"]["content"]

            print("\n" + "="*80)
            print("🔓 OPENAI UNRESTRICTED RESPONSE:")
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

                # Check if it has a module call at the end
                if 'module ' in scad_code and not scad_code.rstrip().endswith(');'):
                    import re
                    module_match = re.search(r'module\s+(\w+)\s*\(', scad_code)
                    if module_match:
                        module_name = module_match.group(1)
                        parsed['new_scad_code'] = scad_code + '\n\n// Generate the design\n' + module_name + '();\n'
                        print(f"⚠️ Added missing module call: {module_name}();")

            return parsed

        except Exception as e:
            print(f"❌ Error in unrestricted mode: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_response()

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

# Function interface for benchmark compatibility
def call_openai_llm(user_input, full_scad_content, current_params=None):
    """Function interface for unrestricted OpenAI LLM calls"""
    handler = LLMHandler()
    return handler.interpret_modification(user_input, full_scad_content, current_params)