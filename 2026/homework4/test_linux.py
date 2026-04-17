#!/usr/bin/env python3
"""
Linux Test Suite for Homework 4: K-Core Decomposition Pipeline
Requires: nvcc (CUDA compiler), g++, and a CUDA-capable GPU.

Tests the full pipeline (Task A: CSR Construction + Task B: GPU K-Core)
with small, medium, and large graph instances.
"""

import os
import subprocess
import sys
import shutil
import random
import time

###############################################################################
# Reference Implementation
###############################################################################

def kcore_reference(num_vertices, directed_edges):
    """
    Reference k-core decomposition using level-synchronous peeling.
    Matches the C++ GPU implementation behavior exactly.
    """
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
    """Write directed edges to a file (one 'u v' pair per line)."""
    with open(filename, "w") as f:
        for u, v in directed_edges:
            f.write(f"{u} {v}\n")


def make_undirected(edge_pairs):
    """Given undirected edge pairs, return directed edges (both directions)."""
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
    """K4 (0-3) + triangle (3,4,5) + pendant (5,6). Expected: [3,3,3,3,2,2,1]"""
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
    """K8(0-7) -- K5(8-12) -- K3(13-15) connected by bridge edges."""
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
# Test Case Definitions
###############################################################################

TEST_CASES = []

# --- Small tests ---
n, e = 4, make_undirected([(0, 1), (1, 2), (2, 0), (0, 3)])
TEST_CASES.append({"name": "Test 1: Triangle + Pendant (4V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_mixed_coreness_graph()
TEST_CASES.append({"name": "Test 2: Mixed Coreness K4+Tri+Pendant (7V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_complete_graph(5)
TEST_CASES.append({"name": "Test 3: Complete K5 (5V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_star_graph(6)
TEST_CASES.append({"name": "Test 4: Star Graph (6V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_grid_graph(3, 3)
TEST_CASES.append({"name": "Test 5: 3x3 Grid (9V)", "nv": n, "edges": e, "timeout": 30})

n, e = generate_nested_clique_chain()
TEST_CASES.append({"name": "Test 6: Nested Clique Chain K8-K5-K3 (16V)", "nv": n, "edges": e, "timeout": 30})

# --- Medium tests ---
n, e = generate_disjoint_cliques([50, 30, 20, 15, 10, 8, 7, 5, 3, 2])
TEST_CASES.append({"name": "Test 7: Disjoint Cliques (150V)", "nv": n, "edges": e, "timeout": 60})

n, e = generate_random_graph(200, 1000, seed=101)
TEST_CASES.append({"name": "Test 8: Random Graph (200V, ~2000E)", "nv": n, "edges": e, "timeout": 60})

n, e = generate_grid_graph(10, 10)
TEST_CASES.append({"name": "Test 9: 10x10 Grid (100V)", "nv": n, "edges": e, "timeout": 60})

# --- Large tests ---
n, e = generate_random_graph(1000, 5000, seed=202)
TEST_CASES.append({"name": "Test 10: Random Graph (1000V, ~10000E)", "nv": n, "edges": e, "timeout": 120})

n, e = generate_random_graph(5000, 25000, seed=303)
TEST_CASES.append({"name": "Test 11: Random Graph (5000V, ~50000E)", "nv": n, "edges": e, "timeout": 180})

n, e = generate_disjoint_cliques([100, 80, 60, 40, 30, 20, 15, 10, 5])
TEST_CASES.append({"name": "Test 12: Large Disjoint Cliques (360V)", "nv": n, "edges": e, "timeout": 120})

n, e = generate_random_graph(10000, 50000, seed=404)
TEST_CASES.append({"name": "Test 13: Large Random Graph (10000V, ~100000E)", "nv": n, "edges": e, "timeout": 300})


###############################################################################
# Main Test Runner
###############################################################################

def main():
    print("=" * 60)
    print("  Homework 4 — Linux Full Pipeline Test Suite")
    print("=" * 60)

    # 1. Check dependencies
    print("\n1. Checking dependencies...")
    if not shutil.which("nvcc"):
        print("ERROR: nvcc (CUDA compiler) not found. Please ensure CUDA is installed.")
        sys.exit(1)
    if not shutil.which("g++"):
        print("ERROR: g++ not found. Please install GCC.")
        sys.exit(1)
    print("   nvcc and g++ found.")

    # 2. Compile test pipeline (independent of student Makefile)
    print("\n2. Compiling the test pipeline...")
    # Clean any stale objects
    for f in ["main.o", "kcore_cpu.o", "kcore_gpu.o", "test_pipeline"]:
        if os.path.exists(f):
            os.remove(f)
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
        print("   Compilation successful.")
    except subprocess.CalledProcessError as e:
        print("ERROR: Compilation failed.")
        print(e.stderr)
        sys.exit(1)

    # 3. Run tests
    print(f"\n3. Running {len(TEST_CASES)} tests...\n")
    passed = 0
    failed = 0

    for test in TEST_CASES:
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

        # Parse output
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

    # Summary
    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed out of {len(TEST_CASES)}")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
