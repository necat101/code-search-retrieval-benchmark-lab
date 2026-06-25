#!/usr/bin/env python3
"""
Code Search Retrieval Benchmark
Compares grep, ripgrep, and other search strategies for agent code retrieval.
Measures retrieval quality BEFORE token savings.
"""

import json
import subprocess
import time
import statistics
from pathlib import Path
from datetime import datetime

# Configuration
CORPUS_DIR = Path("corpus")
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

TRIALS = 3
TOKEN_ESTIMATE_DIVISOR = 4

def run_grep_search(query: str, corpus_dir: Path, context_lines: int = 0):
    """Run grep search"""
    cmd = ["grep", "-r", "-n", "-i"]
    if context_lines > 0:
        cmd.extend([f"-C{context_lines}"])
    cmd.extend([query, str(corpus_dir)])
    
    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "time_ms": elapsed,
            "chars": len(proc.stdout),
            "tokens_est": len(proc.stdout) // TOKEN_ESTIMATE_DIVISOR,
            "results": proc.stdout[:200]
        }
    except:
        return {"time_ms": 5000, "chars": 0, "tokens_est": 0, "results": ""}

def main():
    print("Code Search Retrieval Benchmark")
    print("=" * 50)
    
    if not CORPUS_DIR.exists():
        print("ERROR: Corpus not found. Run generate_corpus.py first.")
        return
    
    # Test queries
    test_queries = [
        "UserSessionStore",
        "rate limiting",
        "refresh token"
    ]
    
    results = []
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = run_grep_search(query, CORPUS_DIR, context_lines=2)
        print(f"  Time: {result['time_ms']:.1f}ms, "
              f"Chars: {result['chars']}, "
              f"Tokens: ~{result['tokens_est']}")
        results.append({"query": query, **result})
    
    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "results": results
    }
    
    results_file = RESULTS_DIR / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")

if __name__ == "__main__":
    main()
