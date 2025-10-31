#!/usr/bin/env python3
"""
LLM Benchmark Script for Concrete House Modifications
Compares Groq vs OpenAI LLM performance on SCAD modification tasks
"""

import os
import time
import csv
from datetime import datetime
import sys

# Import the appropriate LLM handlers based on user choice
def setup_llm_handlers(use_restricted=True):
    """Import and return the appropriate LLM handler functions"""
    if use_restricted:
        from llm_handler_groq_restricted import call_groq_llm
        from llm_handler_openai import call_openai_llm
        print("🔒 Using RESTRICTED mode (±20% parameter changes only)")
    else:
        from llm_handler_groq_unrestricted import call_groq_llm
        from llm_handler_openai_unrestricted import call_openai_llm
        print("🔓 Using UNRESTRICTED mode (full modifications allowed)")

    return call_groq_llm, call_openai_llm

# Test prompts for house modifications
TEST_PROMPTS = [
    "Make the wall thickness 300mm",
    "Add a chimney on the roof",
    "Make the door 2.5m high",
    "Add windows on the back wall",
    "Increase the roof height by 500mm",
    "Make the foundation 500mm deep",
    "Add a garage extension",
    "Change the roof to a flat roof",
    "Add reinforcement bars to the walls",
    "Make the house 1m taller",
    "Add a balcony on the second floor",
    "Change window sizes to 1.5m x 1.2m",
    "Add solar panels on the roof",
    "Make the walls 250mm thick",
    "Add a front porch"
]

def load_scad_file(filepath):
    """Load SCAD file content"""
    with open(filepath, 'r') as f:
        return f.read()

def save_results_to_csv(results, filename="benchmark_results.csv"):
    """Save benchmark results to CSV file"""
    fieldnames = [
        'timestamp', 'test_number', 'llm', 'prompt', 'response_time_ms',
        'llm_output_length', 'user_rating', 'error_message'
    ]

    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            writer.writerow(result)

    print(f"📊 Results saved to {filename}")

def show_diff(original, modified):
    """Show the full modified SCAD content"""
    print("\n📝 MODIFIED SCAD:")
    print("=" * 50)
    print(modified)  # Show full content, not truncated
    print("=" * 50)

def run_benchmark(scad_file, num_tests=5):
    """Run the benchmark test"""
    print("🏠 LLM Concrete House Benchmark")
    print("=" * 50)

    # Ask user for mode
    while True:
        mode_choice = input("Choose LLM mode - (R)estricted or (U)nrestricted? ").lower().strip()
        if mode_choice in ['r', 'restricted']:
            use_restricted = True
            break
        elif mode_choice in ['u', 'unrestricted']:
            use_restricted = False
            break
        else:
            print("Please enter 'R' for restricted or 'U' for unrestricted")

    # Setup LLM handlers based on choice
    call_groq_llm, call_openai_llm = setup_llm_handlers(use_restricted)

    # Load SCAD content
    try:
        scad_content = load_scad_file(scad_file)
        print(f"✅ Loaded SCAD file: {len(scad_content)} characters")
    except Exception as e:
        print(f"❌ Error loading SCAD file: {e}")
        return

    # Show the current SCAD code
    print("\n📄 CURRENT SCAD CODE:")
    print("=" * 50)
    print(scad_content)
    print("=" * 50)

    # Ask for the prompt
    print("\nEnter the prompt you want to test both LLMs on:")
    prompt = input("> ").strip()
    if not prompt:
        print("❌ No prompt entered, exiting...")
        return

    print(f"\nRunning {num_tests} tests with prompt: '{prompt}'")
    print()

    results = []
    scores = {'groq': 0, 'openai': 0}

    # Run tests
    for test_num in range(1, num_tests + 1):
        print(f"\n🧪 TEST {test_num}/{num_tests}")
        print("-" * 30)
        print(f"📋 Prompt: {prompt}")

        # Test both LLMs
        llm_results = {}

        for llm_name, llm_func in [('groq', call_groq_llm), ('openai', call_openai_llm)]:
            print(f"\n🤖 Testing {llm_name.upper()}...")

            start_time = time.time()
            try:
                result = llm_func(prompt, scad_content)
                response_time = (time.time() - start_time) * 1000  # ms

                if 'error' in result:
                    print(f"❌ {llm_name.upper()} Error: {result['error']}")
                    llm_results[llm_name] = {
                        'success': False,
                        'response_time': response_time,
                        'output': result.get('llm_output', ''),
                        'error': result['error']
                    }
                else:
                    print(f"✅ {llm_name.upper()} Response: {response_time:.1f}ms")
                    llm_results[llm_name] = {
                        'success': True,
                        'response_time': response_time,
                        'output': result.get('llm_output', ''),
                        'error': None
                    }

                    # Show the modification
                    show_diff(scad_content, result.get('llm_output', ''))

                    # Ask user for rating
                    while True:
                        rating = input(f"👍 Is {llm_name.upper()}'s modification correct? (y/n): ").lower().strip()
                        if rating in ['y', 'yes']:
                            user_rating = 1
                            scores[llm_name] += 1
                            break
                        elif rating in ['n', 'no']:
                            user_rating = 0
                            break
                        else:
                            print("Please enter 'y' or 'n'")

                    llm_results[llm_name]['user_rating'] = user_rating

            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                print(f"❌ {llm_name.upper()} Exception: {e}")
                llm_results[llm_name] = {
                    'success': False,
                    'response_time': response_time,
                    'output': '',
                    'error': str(e),
                    'user_rating': 0
                }

        # Save results for this test
        timestamp = datetime.now().isoformat()
        for llm_name, result in llm_results.items():
            results.append({
                'timestamp': timestamp,
                'test_number': test_num,
                'llm': llm_name,
                'prompt': prompt,
                'response_time_ms': round(result['response_time'], 1),
                'llm_output_length': len(result['output']),
                'user_rating': result.get('user_rating', 0),
                'error_message': result.get('error', '')
            })

    # Show final scores
    print("\n" + "=" * 50)
    print("🏆 FINAL RESULTS")
    print("=" * 50)
    print(f"Groq Score: {scores['groq']}/{num_tests}")
    print(f"OpenAI Score: {scores['openai']}/{num_tests}")

    if scores['groq'] > scores['openai']:
        print("🏆 Groq wins!")
    elif scores['openai'] > scores['groq']:
        print("🏆 OpenAI wins!")
    else:
        print("🤝 It's a tie!")

    # Save to CSV
    save_results_to_csv(results)

    return results

if __name__ == "__main__":
    # Default SCAD file
    scad_file = os.path.join(os.path.dirname(__file__), "house.scad")

    # Get number of tests from command line or default to 5
    num_tests = 5
    if len(sys.argv) > 1:
        try:
            num_tests = int(sys.argv[1])
        except ValueError:
            print("Usage: python benchmark.py [number_of_tests]")
            print("Example: python benchmark.py 10")
            sys.exit(1)

    # Run benchmark
    run_benchmark(scad_file, num_tests)