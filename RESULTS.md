# Code Search Benchmark Results

Generated: 2026-06-25T18:31:33

## Test Environment
- Python: 3.12.3
- ripgrep: 14.1.1
- GNU grep: 3.11
- Corpus: Synthetic codebase (16 files, ~8KB)

## Summary

Initial benchmark run completed successfully. 

## Strategies Tested
1. grep - Basic grep search
2. grep+context - grep with 3 lines context
3. ripgrep - Fast grep alternative
4. ripgrep+context - ripgrep with context
5. python-lexical - Pure Python baseline
6. python-bm25 - BM25-inspired ranking

## Running the Benchmark

```bash
python3 generate_corpus.py  # Generate test corpus
python3 benchmark.py        # Run benchmarks
```

Results are saved to `results/` directory with detailed metrics.

## Key Metrics

The benchmark measures:
- **Retrieval Quality**: Hit rate, MRR, recall@k, precision@k
- **Efficiency**: Characters returned, estimated tokens, files read
- **Performance**: Query time, indexing time

See README.md for full methodology.
