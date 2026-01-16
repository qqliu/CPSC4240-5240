#!/usr/bin/env python3
import subprocess
import sys
import time
import random
import re
import os

###############################################################################
# Helper Functions for File I/O and Number Formatting
###############################################################################

def write_file(filename, content):
    """Write the provided content to a file."""
    with open(filename, "w") as f:
        f.write(content)

def format_number(n):
    """
    Format a number to two decimal places.
    This is used to create "expected" output from
    which we'll compare in a tolerance-based way.
    """
    return f"{n:.2f}"

def parse_points(s):
    """
    Parse a point file string into a list of (x,y) floats.
    Expected format:
      First line: integer N
      Next N lines: "x y"
    """
    lines = s.strip().splitlines()
    if not lines:
        return []
    n = int(lines[0])
    pts = []
    for line in lines[1:]:
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        x, y = map(float, parts[:2])
        pts.append((x, y))
    return pts

def generate_points(n, low=0, high=1000):
    """
    Generate n random 2D points in [low, high], each with two decimals.
    Return as the file format: first line is N, then N lines of "x y".
    """
    pts = [f"{n}"]
    for _ in range(n):
        x = random.uniform(low, high)
        y = random.uniform(low, high)
        pts.append(f"{x:.2f} {y:.2f}")
    return "\n".join(pts) + "\n"

def generate_queries(q, low=0, high=1000):
    """
    Generate q random 2D query points in [low, high], each with two decimals.
    Return as the file format: first line is Q, then Q lines of "x y".
    """
    pts = [f"{q}"]
    for _ in range(q):
        x = random.uniform(low, high)
        y = random.uniform(low, high)
        pts.append(f"{x:.2f} {y:.2f}")
    return "\n".join(pts) + "\n"

###############################################################################
# Comparison Helper
###############################################################################

def compare_lines(expected, actual):
    """
    Compare two lines by splitting them into alternating non-numeric and numeric parts.
    For numeric parts, values are compared with a ±0.1 tolerance (two-decimal notion).
    For text parts, compare after stripping whitespace.

    Returns a list of error messages (empty if no errors).
    """
    # Use regex to capture numeric substrings
    expected_parts = re.split(r"([-+]?[0-9]*\.?[0-9]+)", expected)
    actual_parts   = re.split(r"([-+]?[0-9]*\.?[0-9]+)", actual)
    errors = []

    # Quick structure check
    if len(expected_parts) != len(actual_parts):
        errors.append(
            "Line structure mismatch.\n"
            f"Expected parts: {expected_parts}\nGot: {actual_parts}"
        )
        return errors

    # Compare each segment in turn
    for idx, (exp, act) in enumerate(zip(expected_parts, actual_parts)):
        # Even indices are text segments, odd indices are numeric
        if idx % 2 == 0:
            # Compare text segments after stripping
            if exp.strip() != act.strip():
                errors.append(
                    f"Mismatch in text segment:\nExpected: '{exp.strip()}'\nGot: '{act.strip()}'"
                )
        else:
            # Compare numeric segments with tolerance ±0.1
            try:
                exp_val = float(exp)
                act_val = float(act)
            except ValueError:
                errors.append(
                    f"Error parsing numbers: Expected '{exp}', Got '{act}'"
                )
                continue

            # If the difference is more than 0.1, fail
            diff = abs(exp_val - act_val)
            if diff > 0.1:
                errors.append(
                    f"Mismatch in numeric value: expected {exp_val:.2f}, got {act_val:.2f} "
                    f"(diff={diff:.2f} > 0.1)"
                )

    return errors

###############################################################################
# Grading Logic
###############################################################################

def compute_expected_output(data_str, query_str, k):
    """
    Given data and query strings plus k, compute the expected output lines.
    Example logic that prints all queries, each with its k nearest neighbors.
    Adjust to match your program's logic as needed.
    """
    data_points  = parse_points(data_str)
    query_points = parse_points(query_str)
    out_lines = []

    for q_idx, (qx, qy) in enumerate(query_points):
        # Compute distances from query (qx, qy) to each data point
        dists = []
        for i, (dx, dy) in enumerate(data_points):
            dd = (qx - dx)**2 + (qy - dy)**2
            dists.append((dd, i))

        # sort by distance then index
        dists.sort(key=lambda x: (x[0], x[1]))
        neighbors = dists[:k]  # take k nearest

        # Build output lines
        out_lines.append(f"Query {q_idx}: ({format_number(qx)}, {format_number(qy)})")
        n_line = "  kNN: " + "".join(
            f"(dist2={format_number(dist)}, idx={idx}) " for dist, idx in neighbors
        )
        out_lines.append(n_line)

    return out_lines

###############################################################################
# Test Cases
###############################################################################

# Reproducible seed
random.seed(42)

TEST_CASES = [
    {
        "name": "Test 1: Simple 3 data, 1 query",
        "data": "3\n0.00 0.00\n3.00 0.00\n0.00 4.00\n",
        "query": "1\n1.00 1.00\n",
        "k": 2,
        "timeout": 5
    },
    {
        "name": "Test 2: 4 data, 2 queries",
        "data": "4\n0.00 0.00\n0.00 1.00\n1.00 0.00\n1.00 1.00\n",
        "query": "2\n0.00 0.00\n1.00 1.00\n",
        "k": 1,
        "timeout": 5
    },
]

# ---------------------- ADDING LARGE TEST CASES ---------------------- #
TEST_CASES += [
    {
        "name": "Large Test 3: 10^3 data, 10^3 queries",
        "data": generate_points(10**3),
        "query": generate_queries(10**3),
        "k": 5,
        "timeout": 30
    },
    {
        "name": "Large Test 4: 10^4 data, 10^4 queries",
        # data: 10^4 points
        "data": generate_points(10**4),
        # queries: 10^3 queries
        "query": generate_queries(10**4),
        "k": 5,
        "timeout": 60
    },
    {
        "name": "Large Test 5: 10^5 data, 10^5 queries",
        # data: 10^5 points
        "data": generate_points(10**5),
        # queries: 10^4 queries
        "query": generate_queries(10**5),
        "k": 5,
        "timeout": 120
    }
    # You can add an even larger test if desired, but these should suffice.
]

###############################################################################
# Compile / Run / Compare
###############################################################################

def compile_cpp_source():
    """
    Attempt to compile 'template.cpp' into an executable 'kd_tree'.
    Return True if successful, False otherwise.
    """
    if not os.path.exists("template.cpp"):
        print("[Error] template.cpp not found.")
        return False

    compile_cmd = ["g++", "-O2", "-std=c++17", "-pthread", "-I./parlaylib", "-o", "kd_tree", "template.cpp"]
    try:
        result = subprocess.run(
            compile_cmd, capture_output=True, text=True, check=True
        )
        print("[Info] Compilation succeeded.")
        return True
    except subprocess.CalledProcessError as e:
        print("[Error] Compilation failed.")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        return False

def run_student_program(test_case):
    """
    Run the compiled kd_tree program on the given test case.
    Return the list of stripped, non-empty output lines or ["[TIMEOUT]"] if it times out.
    """
    write_file("data.txt", test_case["data"])
    write_file("query.txt", test_case["query"])
    cmd = ["./kd_tree", "data.txt", "query.txt", str(test_case["k"])]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=test_case.get("timeout", 5)
        )
    except subprocess.TimeoutExpired:
        return ["[TIMEOUT]"]

    # Clean output lines
    out_lines = proc.stdout.strip().splitlines()
    out_lines = [ln.strip() for ln in out_lines if ln.strip()]
    return out_lines

def run_tests():
    """
    Compile once, then run all tests, printing results to stdout.
    Exit code 0 if all pass, 1 if any fail.
    """
    # 1. Compile
    if not compile_cpp_source():
        sys.exit(1)

    # 2. Run tests
    all_passed = True
    for i, test in enumerate(TEST_CASES, start=1):
        print(f"\n=== Running Test {i}: {test['name']} ===")
        start = time.time()

        # Expected lines
        expected_lines = compute_expected_output(test["data"], test["query"], test["k"])
        # Actual lines
        actual_lines = run_student_program(test)

        duration = time.time() - start
        if actual_lines == ["[TIMEOUT]"]:
            print("[FAIL] Program timed out.")
            all_passed = False
            continue

        # Compare line counts
        if len(actual_lines) != len(expected_lines):
            print(f"[FAIL] Expected {len(expected_lines)} lines, got {len(actual_lines)}.")
            all_passed = False
        else:
            # Compare lines
            test_failed = False
            for idx, (exp, act) in enumerate(zip(expected_lines, actual_lines), start=1):
                errors = compare_lines(exp, act)
                if errors:
                    print(f"[FAIL] Mismatch on line {idx}:")
                    for err in errors:
                        print("   ", err)
                    test_failed = True
            if not test_failed:
                print("[PASS] All lines match.")

            all_passed = all_passed and (not test_failed)

        print(f"[Info] Test finished in {duration:.2f}s")

    if all_passed:
        print("\nAll tests passed.")
        sys.exit(0)
    else:
        print("\nSome tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()

