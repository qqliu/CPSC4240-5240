#!/usr/bin/env python3
"""
Mac OS Test Suite for Homework 4: K-Core Decomposition Pipeline

Since Macs typically lack CUDA GPUs, this test suite:
  1. Compiles and tests the CPU-only CSR construction (Task A) thoroughly.
  2. If nvcc is available, also compiles and tests the full pipeline (Task A + B).

Tests include small, medium, and large graph instances.
"""

import os
import subprocess
import sys
import shutil
import random
import time

###############################################################################
# Reference Implementations
###############################################################################

def csr_reference(num_vertices, directed_edges):
    """
    Reference CSR construction. Returns (row_offsets, column_indices).
    Edges are sorted by (source, destination).
    """
    sorted_edges = sorted(directed_edges, key=lambda e: (e[0], e[1]))
    degrees = [0] * num_vertices
    for u, v in sorted_edges:
        degrees[u] += 1
    row_offsets = [0] * (num_vertices + 1)
    for i in range(num_vertices):
        row_offsets[i + 1] = row_offsets[i] + degrees[i]
    column_indices = [v for u, v in sorted_edges]
    return row_offsets, column_indices


def kcore_reference(num_vertices, directed_edges):
    """Reference k-core decomposition using level-synchronous peeling."""
    neighbors = [[] for _ in range(num_vertices)]
    degrees = [0] * num_vertices
    for u, v in directed_edges:
        neighbors[u].append(v)
        degrees[u] += 1

    coreness = [0] * num_vertices
    total_peeled = 0
    current_k = 1
    while total_peeled < num_vertices:
        while True:
            frontier = []
            for v in range(num_vertices):
                if coreness[v] == 0 and degrees[v] <= current_k:
                    frontier.append(v)
                    coreness[v] = current_k
            if not frontier:
                break
            total_peeled += len(frontier)
            for u in frontier:
                for v in neighbors[u]:
                    if coreness[v] == 0:
                        degrees[v] -= 1
        current_k += 1
    return coreness


###############################################################################
# Graph Generators
###############################################################################

def edges_to_file(directed_edges, filename):
    with open(filename, "w") as f:
        for u, v in directed_edges:
            f.write(f"{u} {v}\n")


def make_undirected(edge_pairs):
    directed = []
    for u, v in edge_pairs:
        directed.append((u, v))
        directed.append((v, u))
    return directed


def generate_complete_graph(n):
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    return n, make_undirected(pairs)


def generate_star_graph(n):
    pairs = [(0, i) for i in range(1, n)]
    return n, make_undirected(pairs)


def generate_mixed_coreness_graph():
    pairs = [
        (0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3),
        (3, 4), (4, 5), (5, 3),
        (5, 6),
    ]
    return 7, make_undirected(pairs)


def generate_grid_graph(rows, cols):
    n = rows * cols
    pairs = []
    for r in range(rows):
        for c in range(cols):
            v = r * cols + c
            if c + 1 < cols:
                pairs.append((v, v + 1))
            if r + 1 < rows:
                pairs.append((v, v + cols))
    return n, make_undirected(pairs)


def generate_disjoint_cliques(clique_sizes):
    n = sum(clique_sizes)
    pairs = []
    offset = 0
    for s in clique_sizes:
        for i in range(s):
            for j in range(i + 1, s):
                pairs.append((offset + i, offset + j))
        offset += s
    return n, make_undirected(pairs)


def generate_nested_clique_chain():
    pairs = []
    for i in range(8):
        for j in range(i + 1, 8):
            pairs.append((i, j))
    pairs.append((7, 8))
    for i in range(8, 13):
        for j in range(i + 1, 13):
            pairs.append((i, j))
    pairs.append((12, 13))
    for i in range(13, 16):
        for j in range(i + 1, 16):
            pairs.append((i, j))
    return 16, make_undirected(pairs)


def generate_random_graph(n, m, seed=42):
    rng = random.Random(seed)
    edge_set = set()
    directed = []
    attempts = 0
    while len(edge_set) < m and attempts < m * 20:
        u = rng.randint(0, n - 1)
        v = rng.randint(0, n - 1)
        if u != v:
            key = (min(u, v), max(u, v))
            if key not in edge_set:
                edge_set.add(key)
                directed.append((u, v))
                directed.append((v, u))
        attempts += 1
    return n, directed


###############################################################################
# CSR Test Cases
###############################################################################

CSR_TEST_CASES = []

n, e = 4, make_undirected([(0, 1), (1, 2), (2, 0), (0, 3)])
CSR_TEST_CASES.append({"name": "CSR Test 1: Triangle + Pendant (4V)", "nv": n, "edges": e, "timeout": 10})

n, e = generate_mixed_coreness_graph()
CSR_TEST_CASES.append({"name": "CSR Test 2: Mixed Coreness (7V)", "nv": n, "edges": e, "timeout": 10})

n, e = generate_complete_graph(5)
CSR_TEST_CASES.append({"name": "CSR Test 3: Complete K5 (5V)", "nv": n, "edges": e, "timeout": 10})

n, e = generate_star_graph(6)
CSR_TEST_CASES.append({"name": "CSR Test 4: Star (6V)", "nv": n, "edges": e, "timeout": 10})

n, e = generate_grid_graph(3, 3)
CSR_TEST_CASES.append({"name": "CSR Test 5: 3x3 Grid (9V)", "nv": n, "edges": e, "timeout": 10})

n, e = generate_nested_clique_chain()
CSR_TEST_CASES.append({"name": "CSR Test 6: Nested Clique Chain (16V)", "nv": n, "edges": e, "timeout": 10})

n, e = generate_disjoint_cliques([50, 30, 20, 15, 10, 8, 7, 5, 3, 2])
CSR_TEST_CASES.append({"name": "CSR Test 7: Disjoint Cliques (150V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_random_graph(200, 1000, seed=101)
CSR_TEST_CASES.append({"name": "CSR Test 8: Random Graph (200V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_random_graph(1000, 5000, seed=202)
CSR_TEST_CASES.append({"name": "CSR Test 9: Random Graph (1000V)", "nv": n, "edges": e, "timeout": 60})

n, e = generate_random_graph(5000, 25000, seed=303)
CSR_TEST_CASES.append({"name": "CSR Test 10: Random Graph (5000V)", "nv": n, "edges": e, "timeout": 120})

n, e = generate_random_graph(10000, 50000, seed=404)
CSR_TEST_CASES.append({"name": "CSR Test 11: Large Random Graph (10000V)", "nv": n, "edges": e, "timeout": 180})


###############################################################################
# Full Pipeline Test Cases (used only if nvcc is available)
###############################################################################

PIPELINE_TEST_CASES = []

n, e = 4, make_undirected([(0, 1), (1, 2), (2, 0), (0, 3)])
PIPELINE_TEST_CASES.append({"name": "Pipeline Test 1: Triangle + Pendant (4V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_mixed_coreness_graph()
PIPELINE_TEST_CASES.append({"name": "Pipeline Test 2: Mixed Coreness (7V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_complete_graph(5)
PIPELINE_TEST_CASES.append({"name": "Pipeline Test 3: Complete K5 (5V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_grid_graph(3, 3)
PIPELINE_TEST_CASES.append({"name": "Pipeline Test 4: 3x3 Grid (9V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_nested_clique_chain()
PIPELINE_TEST_CASES.append({"name": "Pipeline Test 5: Nested Clique Chain (16V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_random_graph(1000, 5000, seed=202)
PIPELINE_TEST_CASES.append({"name": "Pipeline Test 6: Random Graph (1000V)", "nv": n, "edges": e, "timeout": 120})

n, e = generate_random_graph(5000, 25000, seed=303)
PIPELINE_TEST_CASES.append({"name": "Pipeline Test 7: Random Graph (5000V)", "nv": n, "edges": e, "timeout": 180})

n, e = generate_random_graph(10000, 50000, seed=404)
PIPELINE_TEST_CASES.append({"name": "Pipeline Test 8: Large Random Graph (10000V)", "nv": n, "edges": e, "timeout": 300})


###############################################################################
# Main Test Runner
###############################################################################

def run_csr_tests():
    """Compile and run CPU-only CSR construction tests (Task A)."""
    print("\n" + "=" * 60)
    print("  Phase 1: CPU-Only CSR Construction Tests (Task A)")
    print("=" * 60)

    # Check for csr_test_main.cpp
    if not os.path.exists("csr_test_main.cpp"):
        print("WARNING: csr_test_main.cpp not found. Skipping CSR tests.")
        print("  (Copy csr_test_main.cpp from the homework distribution.)")
        return 0, 0

    # Compile CPU-only test (independent of student Makefile)
    print("\nCompiling CPU-only CSR test...")
    try:
        subprocess.run(
            ["g++", "-O3", "-std=c++17", "-Wall", "-pthread", "-c", "csr_test_main.cpp", "-o", "csr_test_main.o"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["g++", "-O3", "-std=c++17", "-Wall", "-pthread", "-c", "kcore_cpu_template.cpp", "-o", "kcore_cpu.o"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["g++", "-O3", "-std=c++17", "-Wall", "-pthread", "-o", "csr_test", "csr_test_main.o", "kcore_cpu.o"],
            check=True, capture_output=True, text=True,
        )
        print("  Compilation successful.\n")
    except subprocess.CalledProcessError as e:
        print("ERROR: CSR test compilation failed.")
        print(e.stderr)
        return 0, len(CSR_TEST_CASES)

    passed = 0
    failed = 0

    for test in CSR_TEST_CASES:
        name = test["name"]
        nv = test["nv"]
        edges = test["edges"]
        timeout = test["timeout"]

        print(f"--- {name} ---")

        # Compute reference CSR
        expected_offsets, expected_cols = csr_reference(nv, edges)

        # Write edge file
        edges_to_file(edges, "test_graph.txt")

        # Run csr_test
        t0 = time.time()
        try:
            proc = subprocess.run(
                ["./csr_test", "test_graph.txt"],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            print(f"  [FAIL] Timed out after {timeout}s.")
            failed += 1
            continue

        elapsed = time.time() - t0

        if proc.returncode != 0:
            print(f"  [FAIL] Non-zero exit code ({proc.returncode}).")
            failed += 1
            continue

        # Parse output
        actual_offsets = None
        actual_cols = None
        for line in proc.stdout.strip().splitlines():
            if line.startswith("ROW_OFFSETS:"):
                actual_offsets = list(map(int, line.split(":")[1].strip().split()))
            elif line.startswith("COLUMN_INDICES:"):
                actual_cols = list(map(int, line.split(":")[1].strip().split()))

        errors = []
        if actual_offsets is None:
            errors.append("ROW_OFFSETS not found in output.")
        elif actual_offsets != expected_offsets:
            errors.append("ROW_OFFSETS mismatch.")
            errors.append(f"  Expected first 15: {expected_offsets[:15]}")
            errors.append(f"  Got      first 15: {actual_offsets[:15]}")

        if actual_cols is None:
            errors.append("COLUMN_INDICES not found in output.")
        elif actual_cols != expected_cols:
            errors.append("COLUMN_INDICES mismatch.")
            errors.append(f"  Expected first 20: {expected_cols[:20]}")
            errors.append(f"  Got      first 20: {actual_cols[:20]}")

        if errors:
            print(f"  [FAIL]")
            for err in errors:
                print(f"    {err}")
            failed += 1
        else:
            print(f"  [PASS] CSR correct ({nv}V, {len(edges)}E). ({elapsed:.2f}s)")
            passed += 1

    return passed, failed


def run_pipeline_tests():
    """Compile and run full pipeline tests (Task A + B). Requires CUDA."""
    print("\n" + "=" * 60)
    print("  Phase 2: Full Pipeline Tests (Task A + B)")
    print("=" * 60)

    if not shutil.which("nvcc"):
        print("\nWARNING: nvcc not found. Skipping full pipeline tests.")
        print("  The full pipeline requires a CUDA-capable GPU.")
        return 0, 0

    # Compile full pipeline (independent of student Makefile)
    print("\nCompiling full pipeline...")
    try:
        subprocess.run(
            ["g++", "-O3", "-std=c++17", "-Wall", "-pthread", "-c", "main.cpp", "-o", "main.o"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["g++", "-O3", "-std=c++17", "-Wall", "-pthread", "-c", "kcore_cpu_template.cpp", "-o", "kcore_cpu.o"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["nvcc", "-O3", "-std=c++17", "-arch=native", "-c", "kcore_gpu_template.cu", "-o", "kcore_gpu.o"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["nvcc", "-O3", "-std=c++17", "-arch=native", "-Xcompiler", "-pthread",
             "-o", "test_pipeline", "main.o", "kcore_cpu.o", "kcore_gpu.o"],
            check=True, capture_output=True, text=True,
        )
        print("  Compilation successful.\n")
    except subprocess.CalledProcessError as e:
        print("ERROR: Full pipeline compilation failed.")
        print(e.stderr)
        return 0, len(PIPELINE_TEST_CASES)

    passed = 0
    failed = 0

    for test in PIPELINE_TEST_CASES:
        name = test["name"]
        nv = test["nv"]
        edges = test["edges"]
        timeout = test["timeout"]

        print(f"--- {name} ---")

        # Compute reference
        t0 = time.time()
        expected = kcore_reference(nv, edges)
        ref_time = time.time() - t0

        # Write edge file
        edges_to_file(edges, "test_graph.txt")

        # Run pipeline
        t0 = time.time()
        try:
            proc = subprocess.run(
                ["./test_pipeline", "test_graph.txt"],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            print(f"  [FAIL] Timed out after {timeout}s.")
            failed += 1
            continue

        run_time = time.time() - t0

        if proc.returncode != 0:
            print(f"  [FAIL] Non-zero exit code ({proc.returncode}).")
            if proc.stderr:
                print(f"  stderr: {proc.stderr[:300]}")
            failed += 1
            continue

        lines = proc.stdout.strip().splitlines()
        if len(lines) != len(expected):
            print(f"  [FAIL] Expected {len(expected)} lines, got {len(lines)}.")
            failed += 1
            continue

        mismatches = []
        for i, (line, exp_val) in enumerate(zip(lines, expected)):
            try:
                actual_val = int(line.strip())
            except ValueError:
                mismatches.append((i, exp_val, line.strip()))
                continue
            if actual_val != exp_val:
                mismatches.append((i, exp_val, actual_val))

        if mismatches:
            print(f"  [FAIL] {len(mismatches)} coreness mismatches.")
            for v, exp, act in mismatches[:5]:
                print(f"    Vertex {v}: expected {exp}, got {act}")
            if len(mismatches) > 5:
                print(f"    ... and {len(mismatches) - 5} more.")
            failed += 1
        else:
            print(f"  [PASS] All {nv} vertices correct. (ref={ref_time:.2f}s, run={run_time:.2f}s)")
            passed += 1

    return passed, failed


def main():
    print("=" * 60)
    print("  Homework 4 — Mac OS Test Suite")
    print("=" * 60)

    # Check basic dependencies
    print("\nChecking dependencies...")
    if not shutil.which("g++"):
        print("ERROR: g++ not found. Install Command Line Tools: xcode-select --install")
        sys.exit(1)
    print("  g++ found.")

    if shutil.which("nvcc"):
        print("  nvcc found. Full pipeline tests will be run.")
    else:
        print("  nvcc not found. Only CPU CSR tests will be run.")

    csr_passed, csr_failed = run_csr_tests()
    pipe_passed, pipe_failed = run_pipeline_tests()

    total_passed = csr_passed + pipe_passed
    total_failed = csr_failed + pipe_failed

    # Cleanup temp files
    for f in ["test_graph.txt", "csr_test_main.o", "kcore_cpu.o", "csr_test"]:
        if os.path.exists(f):
            os.remove(f)

    print("\n" + "=" * 60)
    print(f"  Final Results: {total_passed} passed, {total_failed} failed")
    print("=" * 60)

    if total_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
