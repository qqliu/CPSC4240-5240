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
    return "\n".join(" ".join(str(x) for x in row) for row in mat)

def multiply_matrices(A, B):
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
    return [[1 if i == j else 0 for j in range(n)] for i in range(n)]

def random_matrix(n, min_val=0, max_val=2):
    return [[random.randint(min_val, max_val) for _ in range(n)] for _ in range(n)]

def partial_identity_matrix(n):
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

TEST_CASES = [
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

def build_large_test(n, name, hidden=False, timeout=10):
    test_dict = {
        "name": name,
        "hidden": hidden,
        "timeout": timeout
    }
    A = partial_identity_matrix(n)
    B = random_matrix(n, -2, 2)
    C = multiply_matrices(A, B)
    D = random_matrix(n, 0, 1)
    E = partial_identity_matrix(n)
    F = multiply_matrices(D, E)

    a_str = matrix_to_str(A)
    b_str = matrix_to_str(B)
    d_str = matrix_to_str(D)
    e_str = matrix_to_str(E)

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

TEST_CASES.append(build_large_test(50, "Generated Test: n=50", hidden=False))

###############################################################################
# Robust Compilation Logic (The Fix)
###############################################################################

def compile_cpp_source():
    if not os.path.exists("matrixmult.cpp"):
        print("Error: matrixmult.cpp not found.")
        return False

    compiler = "g++"
    # Added -I. so it can find parlay folder if it's in the current dir
    flags = ["-std=c++17", "-O3", "-fopenmp", "-pthread", "-I."]

    if sys.platform == "darwin":
        compiler = "g++" # Apple Clang
        # Flags for Apple Clang to support OpenMP
        flags = [
            "-std=c++17",
            "-O3",
            "-Xpreprocessor", "-fopenmp",
            "-lomp",
            "-pthread",
            "-I."
        ]

        # DYNAMIC PATH DETECTION
        # We ask 'brew' where libomp lives instead of guessing
        try:
            brew_prefix = subprocess.check_output(["brew", "--prefix", "libomp"]).decode().strip()
            flags.extend([f"-I{brew_prefix}/include", f"-L{brew_prefix}/lib"])
            print(f"Found libomp at: {brew_prefix}")
        except Exception:
            # Fallback for when brew command fails or isn't in path
            print("Warning: Could not auto-detect libomp path via 'brew'. Trying default paths.")
            if os.path.exists("/opt/homebrew/include"):
                flags.extend(["-I/opt/homebrew/include", "-L/opt/homebrew/lib"])
            elif os.path.exists("/usr/local/include"):
                flags.extend(["-I/usr/local/include", "-L/usr/local/lib"])

    compile_cmd = [compiler] + flags + ["-o", "matrixmult", "matrixmult.cpp"]

    print(f"Compiling with: {' '.join(compile_cmd)}")

    try:
        subprocess.run(compile_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print("Compilation failed.")
        print("stdout:", e.stdout.decode())
        print("stderr:", e.stderr.decode())
        return False

def run_test(test_case):
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
    filtered_output = []
    for line in output:
        line = line.strip()
        if not line or line.startswith("Enter"): continue
        filtered_output.append(line)
    return filtered_output

def grade_test_case(test_case):
    start_time = time.time()
    output_lines = run_test(test_case)
    end_time = time.time()
    test_duration = end_time - start_time

    expected_lines = test_case["expected_output"]

    passed = True
    if len(output_lines) != len(expected_lines):
        passed = False
    else:
        for out_line, exp_line in zip(output_lines, expected_lines):
            if out_line.strip() != exp_line.strip():
                passed = False
                break

    score = 1 if passed else 0
    feedback = []
    if not passed:
        feedback.append(f"Expected ({len(expected_lines)} lines) vs Got ({len(output_lines)} lines).")
        # Show sample mismatch
        for i in range(min(5, len(expected_lines), len(output_lines))):
            feedback.append(f"Exp: {expected_lines[i]}")
            feedback.append(f"Got: {output_lines[i]}")
    else:
        feedback.append("Output matched.")

    return {
        "name": test_case["name"],
        "score": score,
        "max_score": 1,
        "time_elapsed_seconds": test_duration,
        "output": "\n".join(feedback)
    }

def main():
    if not compile_cpp_source():
        results = {"score": 0, "output": "Compilation failed.", "tests": []}
        print(json.dumps(results, indent=4))
        sys.exit(1)

    test_results = []
    total_score = 0
    total_max = 0

    for test in TEST_CASES:
        t_res = grade_test_case(test)
        test_results.append(t_res)
        total_score += t_res["score"]
        total_max += t_res["max_score"]
        status = "PASSED" if t_res["score"] == 1 else "FAILED"
        print(f"Test '{t_res['name']}': {status}")

    final_score = (total_score / total_max) * 100.0 if total_max > 0 else 0
    results = {"score": final_score, "output": "Autograder completed.", "tests": test_results}

    with open("results.json", "w") as f:
        json.dump(results, f, indent=4)

    sys.exit(0)

if __name__ == "__main__":
    main()
