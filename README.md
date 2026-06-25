# Code Search Retrieval Benchmark Lab

A local, reproducible benchmark for code search retrieval quality and token efficiency.

## Quick Start

```bash
# Generate synthetic codebase
python3 generate_corpus.py

# Run benchmarks
python3 benchmark.py
```

## Overview

This benchmark measures code search retrieval quality BEFORE token efficiency, inspired by HN discussion on Semble's "98% fewer tokens than grep" claim.

**Key principle**: A search tool that returns 0 tokens but misses the answer is not "efficient" - it's broken.

See README.md for full documentation.
