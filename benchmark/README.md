# LLM Concrete House Benchmark

A command-line tool to benchmark Groq vs OpenAI LLMs on concrete house modification tasks using OpenSCAD.

## Setup

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   Create a `.env` file in this directory with:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Files

- `house.scad` - Simple concrete house model for testing
- `benchmark.py` - Main benchmark script
- `llm_handler_groq_restricted.py` - Groq LLM handler (restricted mode)
- `llm_handler_groq_unrestricted.py` - Groq LLM handler (unrestricted mode)
- `llm_handler_openai.py` - OpenAI LLM handler (restricted mode)
- `llm_handler_openai_unrestricted.py` - OpenAI LLM handler (unrestricted mode)

## Usage

### Run Benchmark

```bash
python benchmark.py [number_of_tests]
```

- `number_of_tests`: Optional, defaults to 5
- The script will ask you to choose between **Restricted** or **Unrestricted** mode
- Example: `python benchmark.py 10` (runs 10 tests after mode selection)

### LLM Modes

#### 🔒 **Restricted Mode** (±20% parameter changes only)

- Safe parameter adjustments only
- Cannot add/remove structural features
- Perfect for testing parameter modification accuracy
- Uses: `llm_handler_groq_restricted.py` and `llm_handler_openai.py`

#### 🔓 **Unrestricted Mode** (Full modifications allowed)

- Can add/remove/modify any features
- Full OpenSCAD programming capabilities
- Perfect for testing creative design capabilities
- Uses: `llm_handler_groq_unrestricted.py` and `llm_handler_openai_unrestricted.py`

### What It Does

1. **Asks** you to choose between Restricted or Unrestricted mode
2. **Shows** the current SCAD code for the house
3. **Asks** you to enter a prompt to test
4. **Runs** the specified number of tests with that same prompt
5. **Tests** both LLMs simultaneously on each run (using the selected mode)
6. **Records** response times and shows modifications
7. **Asks** you to rate each modification (y/n)
8. **Scores** LLMs based on correctness (1 point per correct modification)
9. **Saves** all results to `benchmark_results.csv`

### Sample Prompts

- "Make the wall thickness 300mm"
- "Add a chimney on the roof"
- "Make the door 2.5m high"
- "Add windows on the back wall"
- "Increase the roof height by 500mm"
- And 10 more concrete construction tasks...

### Output

The script will:

- Show real-time results for each test
- Display modified SCAD code
- Ask for your rating of correctness
- Show final scores (who won!)
- Save detailed CSV with timestamps, response times, ratings, and errors

### CSV Output

The `benchmark_results.csv` contains:

- timestamp
- test_number
- llm (groq/openai)
- prompt
- response_time_ms
- llm_output_length
- user_rating (1=correct, 0=incorrect)
- error_message

Perfect for analysis and visualization in Excel, Python pandas, or any data analysis tool!

## Example Output

```
### Example Output

**Predefined Prompts Mode:**
```

# 🏠 LLM Concrete House Benchmark

Testing 5 random prompts from 15 available

✅ Loaded SCAD file: 2847 characters

## 🧪 TEST 1/5

📋 Prompt: Make the wall thickness 300mm

🤖 Testing GROQ...
✅ GROQ Response: 1250.3ms

📝 MODIFIED SCAD:
[shows modified code...]

👍 Is GROQ's modification correct? (y/n): y

🤖 Testing OPENAI...
✅ OPENAI Response: 2100.7ms

📝 MODIFIED SCAD:
[shows modified code...]

👍 Is OPENAI's modification correct? (y/n): n

# 🏆 FINAL RESULTS

Groq Score: 3/5
OpenAI Score: 2/5
🏆 Groq wins!

📊 Results saved to benchmark_results.csv

```

**Custom Prompts Mode:**
```

# 🏠 LLM Concrete House Benchmark

Testing 3 prompts from your custom input

✅ Loaded SCAD file: 2847 characters

## 🧪 TEST 1/3

Enter your custom prompt: Make the roof twice as high
📋 Prompt: Make the roof twice as high

🤖 Testing GROQ...
✅ GROQ Response: 1180.2ms

📝 MODIFIED SCAD:
[shows modified code...]

👍 Is GROQ's modification correct? (y/n): y

🤖 Testing OPENAI...
✅ OPENAI Response: 1950.1ms

📝 MODIFIED SCAD:
[shows modified code...]

👍 Is OPENAI's modification correct? (y/n): n

## 🧪 TEST 2/3

Enter your custom prompt: Add a garage door
📋 Prompt: Add a garage door

[...continues...]

```

```
