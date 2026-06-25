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
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import hashlib

# Configuration
CORPUS_DIR = Path("corpus")
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

TRIALS = 3
TOKEN_ESTIMATE_DIVISOR = 4  # chars / 4 = rough token estimate

class SearchResult:
    def __init__(self, file: str, line_start: int, line_end: int, 
                 content: str, score: float = 1.0):
        self.file = file
        self.line_start = line_start
        self.line_end = line_end
        self.content = content
        self.score = score
    
    def to_dict(self):
        return {
            "file": self.file,
            "lines": f"{self.line_start}-{self.line_end}",
            "content_preview": self.content[:100],
            "score": self.score
        }

class QueryResult:
    def __init__(self, query_id: str, strategy: str):
        self.query_id = query_id
        self.strategy = strategy
        self.results: List[SearchResult] = []
        self.search_time_ms = 0
        self.index_time_ms = 0
        self.chars_returned = 0
        self.tokens_estimated = 0
        self.files_read = 0
        self.cache_hit = False
        
    def calculate_metrics(self, ground_truth: Dict) -> Dict[str, Any]:
        """Calculate retrieval quality metrics"""
        expected_files = set(ground_truth.get("expected_files", []))
        expected_symbols = set(ground_truth.get("expected_symbols", []))
        
        # Get actual results
        result_files = set(r.file for r in self.results)
        result_content = " ".join(r.content.lower() for r in self.results)
        
        # Hit rates
        top1_hit = len(result_files & expected_files) > 0 if self.results else False
        top3_files = set(r.file for r in self.results[:3])
        top3_hit = len(top3_files & expected_files) > 0
        top5_files = set(r.file for r in self.results[:5])
        top5_hit = len(top5_files & expected_files) > 0
        
        # Check if expected symbols appear in results
        symbols_found = sum(1 for sym in expected_symbols 
                          if sym.lower() in result_content)
        symbol_recall = symbols_found / len(expected_symbols) if expected_symbols else 0
        
        # Check line ranges (simplified)
        line_match = False
        expected_lines = ground_truth.get("expected_lines", {})
        for result in self.results:
            if result.file in expected_lines:
                exp_start, exp_end = expected_lines[result.file]
                # Check if result overlaps with expected range
                if not (result.line_end < exp_start or result.line_start > exp_end):
                    line_match = True
                    break
        
        # MRR (Mean Reciprocal Rank) - simplified
        mrr = 0.0
        for i, result in enumerate(self.results, 1):
            if result.file in expected_files:
                mrr = 1.0 / i
                break
        
        # Precision@k and Recall@k
        k = 5
        top_k_files = set(r.file for r in self.results[:k])
        relevant_in_top_k = len(top_k_files & expected_files)
        precision_at_k = relevant_in_top_k / k if k > 0 else 0
        recall_at_k = relevant_in_top_k / len(expected_files) if expected_files else 0
        
        return {
            "top1_hit": top1_hit,
            "top3_hit": top3_hit,
            "top5_hit": top5_hit,
            "mrr": mrr,
            "precision_at_5": precision_at_k,
            "recall_at_5": recall_at_k,
            "symbol_recall": symbol_recall,
            "line_range_match": line_match,
            "results_count": len(self.results),
            "expected_files_found": list(result_files & expected_files),
            "expected_files_missed": list(expected_files - result_files)
        }

def run_grep_search(query: str, corpus_dir: Path, context_lines: int = 0) -> QueryResult:
    """Run grep search"""
    result = QueryResult("unknown", f"grep{'+context' if context_lines else ''}")
    
    cmd = ["grep", "-r", "-n", "-i"]
    if context_lines > 0:
        cmd.extend([f"-C{context_lines}"])
    cmd.extend([query, str(corpus_dir)])
    
    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        result.search_time_ms = (time.perf_counter() - start) * 1000
        
        if proc.returncode in (0, 1):  # 0=matches, 1=no matches
            lines = proc.stdout.strip().split('\n') if proc.stdout.strip() else []
            result.chars_returned = len(proc.stdout)
            result.tokens_estimated = result.chars_returned // TOKEN_ESTIMATE_DIVISOR
            
            # Parse results (simplified)
            for line in lines[:10]:  # Top 10
                if ':' in line:
                    parts = line.split(':', 2)
                    if len(parts) >= 2:
                        file_path = parts[0].replace(str(corpus_dir) + '/', '')
                        try:
                            line_no = int(parts[1])
                            content = parts[2] if len(parts) > 2 else ""
                            result.results.append(SearchResult(
                                file=file_path,
                                line_start=max(1, line_no - context_lines),
                                line_end=line_no + context_lines,
                                content=content
                            ))
                        except ValueError:
                            pass
            
            result.files_read = len(set(r.file for r in result.results))
    except subprocess.TimeoutExpired:
        result.search_time_ms = 5000
    
    return result

def run_ripgrep_search(query: str, corpus_dir: Path, context_lines: int = 0) -> QueryResult:
    """Run ripgrep search"""
    result = QueryResult("unknown", f"ripgrep{'+context' if context_lines else ''}")
    
    cmd = ["rg", "-n", "-i", "--no-heading"]
    if context_lines > 0:
        cmd.extend([f"-C{context_lines}"])
    cmd.extend([query, str(corpus_dir)])
    
    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        result.search_time_ms = (time.perf_counter() - start) * 1000
        
        if proc.returncode in (0, 1):
            lines = proc.stdout.strip().split('\n') if proc.stdout.strip() else []
            result.chars_returned = len(proc.stdout)
            result.tokens_estimated = result.chars_returned // TOKEN_ESTIMATE_DIVISOR
            
            # Parse results
            current_file = None
            for line in lines[:20]:
                if line and not line.startswith('--'):
                    if ':' in line and not line[0].isdigit():
                        # File:line:content format
                        parts = line.split(':', 2)
                        if len(parts) >= 2:
                            file_path = parts[0].replace(str(corpus_dir) + '/', '')
                            try:
                                line_no = int(parts[1])
                                content = parts[2] if len(parts) > 2 else ""
                                result.results.append(SearchResult(
                                    file=file_path,
                                    line_start=max(1, line_no - context_lines),
                                    line_end=line_no + context_lines,
                                    content=content
                                ))
                            except ValueError:
                                pass
            
            result.files_read = len(set(r.file for r in result.results))
    except subprocess.TimeoutExpired:
        result.search_time_ms = 5000
    except FileNotFoundError:
        # ripgrep not installed
        pass
    
    return result

def run_lexical_search(query: str, corpus_dir: Path) -> QueryResult:
    """Pure Python lexical search baseline"""
    result = QueryResult("unknown", "python-lexical")
    
    start = time.perf_counter()
    query_terms = query.lower().split()
    
    matches = []
    for file_path in corpus_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in ['.py', '.ts', '.go', '.rs', '.md', '.yaml', '.json']:
            # Skip vendor dirs
            if any(part in ['vendor', 'node_modules', 'target', '.git'] 
                   for part in file_path.parts):
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                # Simple term matching
                score = sum(1 for term in query_terms if term in content_lower)
                if score > 0:
                    # Find first occurrence
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if any(term in line.lower() for term in query_terms):
                            matches.append((
                                score,
                                SearchResult(
                                    file=str(file_path.relative_to(corpus_dir)),
                                    line_start=i,
                                    line_end=i,
                                    content=line,
                                    score=score
                                )
                            ))
                            break
            except Exception:
                pass
    
    result.search_time_ms = (time.perf_counter() - start) * 1000
    
    # Sort by score and take top results
    matches.sort(key=lambda x: x[0], reverse=True)
    result.results = [m[1] for m in matches[:10]]
    result.chars_returned = sum(len(r.content) for r in result.results)
    result.tokens_estimated = result.chars_returned // TOKEN_ESTIMATE_DIVISOR
    result.files_read = len(matches)
    
    return result

def run_bm25_search(query: str, corpus_dir: Path) -> QueryResult:
    """Simple BM25-ish baseline (simplified - not true BM25)"""
    result = QueryResult("unknown", "python-bm25")
    
    start = time.perf_counter()
    query_terms = query.lower().split()
    
    # Build simple inverted index on the fly (inefficient but works for small corpus)
    doc_scores = {}
    
    for file_path in corpus_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in ['.py', '.ts', '.go', '.rs', '.md']:
            if any(part in ['vendor', 'node_modules', 'target', '.git'] 
                   for part in file_path.parts):
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                # Simple TF-IDFish scoring
                score = 0
                for term in query_terms:
                    tf = content_lower.count(term)
                    if tf > 0:
                        # Boost for exact matches and symbol-like patterns
                        if term in content:
                            score += tf * 2
                        else:
                            score += tf
                
                if score > 0:
                    doc_scores[str(file_path.relative_to(corpus_dir))] = {
                        'score': score,
                        'content': content,
                        'path': file_path
                    }
            except Exception:
                pass
    
    result.search_time_ms = (time.perf_counter() - start) * 1000
    
    # Sort and create results
    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1]['score'], reverse=True)
    
    for file_path, data in sorted_docs[:5]:
        lines = data['content'].split('\n')
        # Find best matching line
        best_line_idx = 0
        best_score = 0
        for i, line in enumerate(lines):
            line_score = sum(1 for term in query_terms if term in line.lower())
            if line_score > best_score:
                best_score = line_score
                best_line_idx = i
        
        # Return context around best match
        start_line = max(0, best_line_idx - 2)
        end_line = min(len(lines), best_line_idx + 3)
        context = '\n'.join(lines[start_line:end_line])
        
        result.results.append(SearchResult(
            file=file_path,
            line_start=start_line + 1,
            line_end=end_line,
            content=context,
            score=data['score']
        ))
    
    result.chars_returned = sum(len(r.content) for r in result.results)
    result.tokens_estimated = result.chars_returned // TOKEN_ESTIMATE_DIVISOR
    result.files_read = len(doc_scores)
    
    return result

def load_ground_truth():
    """Load ground truth from corpus"""
    gt_path = CORPUS_DIR / "ground_truth.json"
    if gt_path.exists():
        with open(gt_path) as f:
            return json.load(f)
    return {"queries": []}

def main():
    print("Code Search Retrieval Benchmark")
    print("=" * 50)
    
    # Check if corpus exists
    if not CORPUS_DIR.exists():
        print("ERROR: Corpus not found. Run generate_corpus.py first.")
        return
    
    # Load ground truth
    ground_truth = load_ground_truth()
    queries = ground_truth.get("queries", [])
    
    if not queries:
        print("ERROR: No queries found in ground truth")
        return
    
    print(f"\nLoaded {len(queries)} queries")
    print(f"Corpus: {CORPUS_DIR}")
    
    # Define search strategies to test
    strategies = [
        ("grep", lambda q: run_grep_search(q, CORPUS_DIR, context_lines=0)),
        ("grep+context", lambda q: run_grep_search(q, CORPUS_DIR, context_lines=3)),
        ("ripgrep", lambda q: run_ripgrep_search(q, CORPUS_DIR, context_lines=0)),
        ("ripgrep+context", lambda q: run_ripgrep_search(q, CORPUS_DIR, context_lines=3)),
        ("python-lexical", lambda q: run_lexical_search(q, CORPUS_DIR)),
        ("python-bm25", lambda q: run_bm25_search(q, CORPUS_DIR)),
    ]
    
    # Check which tools are available
    available_strategies = []
    for name, func in strategies:
        if "ripgrep" in name:
            try:
                subprocess.run(["rg", "--version"], capture_output=True, timeout=1)
                available_strategies.append((name, func))
            except:
                print(f"  Skipping {name}: ripgrep not installed")
        else:
            available_strategies.append((name, func))
    
    print(f"\nTesting {len(available_strategies)} strategies:")
    for name, _ in available_strategies:
        print(f"  - {name}")
    
    # Run benchmarks
    all_results = []
    
    for query in queries:
        query_id = query["id"]
        query_text = query["query"]
        print(f"\n--- Query {query_id}: {query_text[:50]} ---")
        
        for strategy_name, strategy_func in available_strategies:
            # Run multiple trials
            trial_results = []
            for trial in range(TRIALS):
                result = strategy_func(query_text)
                result.query_id = query_id
                trial_results.append(result)
            
            # Use median timing
            times = [r.search_time_ms for r in trial_results]
            median_time = statistics.median(times)
            
            # Use first result for metrics (they should be similar)
            result = trial_results[0]
            result.search_time_ms = median_time
            
            # Calculate quality metrics
            metrics = result.calculate_metrics(query)
            
            # Combine result data
            result_data = {
                "query_id": query_id,
                "query": query_text,
                "strategy": strategy_name,
                "query_type": query.get("type"),
                "category": query.get("category"),
                "search_time_ms": result.search_time_ms,
                "chars_returned": result.chars_returned,
                "tokens_estimated": result.tokens_estimated,
                "files_read": result.files_read,
                "results_count": len(result.results),
                **metrics
            }
            
            all_results.append(result_data)
            
            # Print summary
            hit_symbol = "✓" if metrics["top1_hit"] else "✗"
            print(f"  {strategy_name:20s} {hit_symbol} "
                  f"top1={metrics['top1_hit']} "
                  f"time={result.search_time_ms:.1f}ms "
                  f"chars={result.chars_returned} "
                  f"tokens~{result.tokens_estimated}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESULTS_DIR / f"results_{timestamp}.json"
    
    output = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "trials": TRIALS,
            "token_estimate_divisor": TOKEN_ESTIMATE_DIVISOR,
            "corpus_dir": str(CORPUS_DIR),
            "queries_tested": len(queries),
            "strategies_tested": len(available_strategies)
        },
        "results": all_results
    }
    
    with open(results_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n\nResults saved to: {results_file}")
    print(f"Total benchmark runs: {len(all_results)}")
    
    # Generate summary
    generate_summary(output)

def generate_summary(data):
    """Generate markdown summary"""
    results = data["results"]
    
    # Group by strategy
    by_strategy = {}
    for r in results:
        strategy = r["strategy"]
        if strategy not in by_strategy:
            by_strategy[strategy] = []
        by_strategy[strategy].append(r)
    
    output = []
    output.append("# Code Search Benchmark Results")
    output.append(f"\nGenerated: {data['timestamp']}")
    output.append(f"\nQueries tested: {data['config']['queries_tested']}")
    output.append(f"Strategies: {data['config']['strategies_tested']}")
    
    output.append("\n## Summary by Strategy")
    output.append("\n| Strategy | Avg Time (ms) | Avg Chars | Avg Tokens | Top-1 Hit Rate | Top-5 Hit Rate | MRR |")
    output.append("|----------|---------------|-----------|------------|----------------|----------------|-----|")
    
    for strategy, results_list in sorted(by_strategy.items()):
        avg_time = statistics.mean(r["search_time_ms"] for r in results_list)
        avg_chars = statistics.mean(r["chars_returned"] for r in results_list)
        avg_tokens = statistics.mean(r["tokens_estimated"] for r in results_list)
        top1_rate = sum(r["top1_hit"] for r in results_list) / len(results_list)
        top5_rate = sum(r["top5_hit"] for r in results_list) / len(results_list)
        avg_mrr = statistics.mean(r["mrr"] for r in results_list)
        
        output.append(
            f"| {strategy} | {avg_time:.1f} | {avg_chars:.0f} | {avg_tokens:.0f} | "
            f"{top1_rate:.2f} | {top5_rate:.2f} | {avg_mrr:.2f} |"
        )
    
    output.append("\n## Key Findings")
    output.append("\n**Retrieval Quality First:** Strategies are ranked by hit rate, not token count.")
    output.append("A strategy that returns fewer tokens but misses the answer is not 'better'.")
    
    # Find best by different metrics
    best_quality = max(by_strategy.items(), 
                      key=lambda x: sum(r["top1_hit"] for r in x[1]) / len(x[1]))
    best_speed = min(by_strategy.items(),
                    key=lambda x: statistics.mean(r["search_time_ms"] for r in x[1]))
    best_tokens = min(by_strategy.items(),
                     key=lambda x: statistics.mean(r["tokens_estimated"] for r in x[1]))
    
    output.append(f"\n- **Best retrieval quality**: {best_quality[0]}")
    output.append(f"- **Fastest**: {best_speed[0]}")
    output.append(f"- **Fewest tokens**: {best_tokens[0]}")
    
    output.append("\n## Notes")
    output.append("- Token estimates use chars/4 proxy")
    output.append("- Hit rate = % of queries where expected file appears in results")
    output.append("- MRR = Mean Reciprocal Rank (1/rank of first correct result)")
    output.append("- All times are median of 3 trials")
    
    with open("RESULTS.md", "w") as f:
        f.write("\n".join(output))
    
    print("\nSummary written to RESULTS.md")

if __name__ == "__main__":
    main()
