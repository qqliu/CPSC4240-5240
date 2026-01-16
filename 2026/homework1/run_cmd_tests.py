#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import random
import time

###############################################################################
# Helper Functions
###############################################################################

def matrix_to_str(mat):
    """
    Convert a 2D list (matrix) into a multiline string, row by row.
    """
    return "\n".join(" ".join(str(x) for x in row) for row in mat)

def multiply_matrices(A, B):
    """
    Naive O(n^3) multiply for A, B (square, same dimension).
    Returns new matrix C.
    """
    n = len(A)
    C = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            s = 0
            for k in range(n):
                s += A[i][k]*B[k][j]
            C[i][j] = s
    return C

def identity_matrix(n):
    """
    n x n identity matrix
    """
    return [[1 if i == j else 0 for j in range(n)] for i in range(n)]

def random_matrix(n, min_val=0, max_val=2):
    """
    n x n random matrix with entries in [min_val, max_val].
    """
    return [[random.randint(min_val, max_val) for _ in range(n)] for _ in range(n)]

def partial_identity_matrix(n):
    """
    Creates a matrix that is 'mostly' identity but with some random offsets.
    """
    mat = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                mat[i][j] = 1
            else:
                if random.random() < 0.1:
                    mat[i][j] = random.randint(-1, 1)
                else:
                    mat[i][j] = 0
    return mat

###############################################################################
# Test Cases
###############################################################################

# We need to provide inputs for A, B, D, E and expect outputs for C and F.

TEST_CASES = [
    # Test 1: 1x1 matrix
    # A=[2], B=[3] -> C=[6]
    # D=[4], E=[5] -> F=[20]
    {
        "name": "Test 1: 1x1 matrix",
        "input": """1
2
3
4
5
""",
        "expected_output": [
            "The resulting matrix C = A x B is:",
            "6",
            "The resulting matrix F = D x E is:",
            "20"
        ]
    },

    # Test 2: 2x2 matrices
    # A, B defined manually.
    # D, E defined manually (simple identity/zeros for easy mental check).
    {
        "name": "Test 2: 2x2 matrices (simple)",
        "input": """2
1 2
3 4
5 6
7 8
1 0
0 1
1 1
1 1
""",
        "expected_output": [
            "The resulting matrix C = A x B is:",
            "19 22",
            "43 50",
            "The resulting matrix F = D x E is:",
            "1 1",
            "1 1"
        ]
    },

    # Test 3: 2x2 matrices (another example)
    # Here we can just reuse the same numbers for D,E as A,B to check consistency
    {
        "name": "Test 3: 2x2 matrices (consistency check)",
        "input": """2
2 0
0 2
1 1
2 2
2 0
0 2
1 1
2 2
""",
        "expected_output": [
            "The resulting matrix C = A x B is:",
            "2 2",
            "4 4",
            "The resulting matrix F = D x E is:",
            "2 2",
            "4 4"
        ]
    },
]

###############################################################################
# Dynamic Test Generation
###############################################################################

def build_large_test(n, name, hidden=False, timeout=10):
    """
    Build a test dictionary with 4 random matrices (A, B, D, E).
    Calculates expected C = A x B and F = D x E.
    """
    test_dict = {
        "name": name,
        "hidden": hidden,
        "timeout": timeout
    }

    # Generate A, B for OpenMP part
    A = partial_identity_matrix(n)
    B = random_matrix(n, -2, 2)
    C = multiply_matrices(A, B)

    # Generate D, E for ParlayLib part
    # We use different matrices to ensure the code isn't just printing C twice
    D = random_matrix(n, 0, 1)
    E = partial_identity_matrix(n)
    F = multiply_matrices(D, E)

    # Convert to strings
    a_str = matrix_to_str(A)
    b_str = matrix_to_str(B)
    d_str = matrix_to_str(D)
    e_str = matrix_to_str(E)

    # Input format: n, then A, B, D, E
    test_dict["input"] = f"{n}\n{a_str}\n{b_str}\n{d_str}\n{e_str}"

    c_lines = [" ".join(str(x) for x in row) for row in C]
    f_lines = [" ".join(str(x) for x in row) for row in F]

    test_dict["expected_output"] = (
        ["The resulting matrix C = A x B is:"] +
        c_lines +
        ["The resulting matrix F = D x E is:"] +
        f_lines
    )
    return test_dict

# Note: Pure Python matrix mult O(N^3) is slow.
# Reducing N to 50 for the auto-generated test to ensure the Python script
# finishes generating the answer key quickly.
# (Real compilation checks happen in the C++ execution)
TEST_CASES.append(build_large_test(50, "Generated Test: n=50 (OpenMP & Parlay)", hidden=False))

###############################################################################
# Command-Line Autograder Logic
###############################################################################

def compile_cpp_source():
    """
    Compile matrixmult.cpp if it exists.
    Return True if successful, False otherwise.
    Added -pthread for ParlayLib/OpenMP safety.
    """
    if not os.path.exists("matrixmult.cpp"):
        print("Error: matrixmult.cpp not found.")
        return False

    # Added -pthread here
    compile_cmd = ["g++", "-std=c++17", "-O3", "-fopenmp", "-pthread", "-o", "matrixmult", "matrixmult.cpp"]
    try:
        subprocess.run(compile_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print("Compilation failed.")
        print("stdout:", e.stdout.decode())
        print("stderr:", e.stderr.decode())
        return False

def run_test(test_case):
    """
    Run the compiled ./matrixmult against a single test case.
    Return the lines of output after ignoring user prompts.
    """
    test_timeout = test_case.get("timeout", 10)
    prog_input = test_case["input"]

    try:
        proc = subprocess.run(
            ["./matrixmult"],
            input=prog_input.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=test_timeout
        )
    except subprocess.TimeoutExpired:
        return ["[TIMEOUT]"]

    output = proc.stdout.decode("utf-8").strip().splitlines()

    # Filter out interactive prompts if they exist
    filtered_output = []
    for line in output:
        line = line.strip()
        if not line: continue
        if line.startswith("Enter"):
            continue
        filtered_output.append(line)

    return filtered_output

def grade_test_case(test_case):
    """
    Run a single test case, compare output, and return results.
    """
    start_time = time.time()
    output_lines = run_test(test_case)
    end_time = time.time()

    test_duration = end_time - start_time

    expected_lines = test_case["expected_output"]

    # Basic line count check
    if len(output_lines) != len(expected_lines):
        passed = False
    else:
        passed = True
        for out_line, exp_line in zip(output_lines, expected_lines):
            # Strip whitespace to be lenient on trailing spaces
            if out_line.strip() != exp_line.strip():
                passed = False
                break

    score = 1 if passed else 0
    max_score = 1

    feedback = []
    if not passed:
        feedback.append(f"Expected ({len(expected_lines)} lines):")
        # Print first few expected
        for l in expected_lines[:5]:
            feedback.append(f"  {l}")
        if len(expected_lines) > 5: feedback.append("  ...")

        feedback.append(f"Got ({len(output_lines)} lines):")
        # Print first few got
        for l in output_lines[:5]:
            feedback.append(f"  {l}")
        if len(output_lines) > 5: feedback.append("  ...")
    else:
        feedback.append("Output matched successfully.")

    result = {
        "name": test_case["name"],
        "score": score,
        "max_score": max_score,
        "time_elapsed_seconds": test_duration,
        "output": "\n".join(feedback)
    }

    return result

def main():
    # 1. Compile C++ code
    if not compile_cpp_source():
        results = {
            "score": 0,
            "output": "Compilation failed. Please check your code.",
            "tests": []
        }
        with open("results.json", "w") as f:
            json.dump(results, f, indent=4)
        print(json.dumps(results, indent=4))
        sys.exit(1)

    # 2. Run each test
    test_results = []
    total_score = 0
    total_max_score = 0

    print(f"Running {len(TEST_CASES)} tests...")

    for test in TEST_CASES:
        t_res = grade_test_case(test)
        test_results.append(t_res)
        total_score += t_res["score"]
        total_max_score += t_res["max_score"]

        status = "PASSED" if t_res["score"] == 1 else "FAILED"
        print(f"Test '{t_res['name']}': {status} ({t_res['time_elapsed_seconds']:.4f}s)")

    # 3. Summarize
    if total_max_score > 0:
        final_score = (total_score / total_max_score) * 100.0
    else:
        final_score = 0.0

    results = {
        "score": final_score,
        "output": "Autograder completed.",
        "tests": test_results
    }

    # 4. Write results to a local JSON file
    with open("results.json", "w") as f:
        json.dump(results, f, indent=4)

    sys.exit(0)

if __name__ == "__main__":
    main()
