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
    For example:
      - M[i][i] = 1
      - M[i][j] = random small integer if i != j, but maybe not for all.
    This can make the multiplication more interesting than a pure identity matrix.
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

TEST_CASES = [
    # Some small visible tests
    {
        "name": "Test 1: 1x1 matrix",
        "input": """1
2
3
""",
        "expected_output": [
            "The resulting matrix C = A x B is:",
            "6"
        ]
    },
    {
        "name": "Test 2: 2x2 matrices (simple)",
        "input": """2
1 2
3 4
5 6
7 8
""",
        "expected_output": [
            "The resulting matrix C = A x B is:",
            "19 22",
            "43 50"
        ]
    },
    {
        "name": "Test 3: 2x2 matrices (another example)",
        "input": """2
2 0
0 2
1 1
2 2
""",
        "expected_output": [
            "The resulting matrix C = A x B is:",
            "2 2",
            "4 4"
        ]
    },
    {
        "name": "Test 4: 3x3 identity check",
        "input": """3
1 0 0
0 1 0
0 0 1
1 2 3
4 5 6
7 8 9
""",
        "expected_output": [
            "The resulting matrix C = A x B is:",
            "1 2 3",
            "4 5 6",
            "7 8 9"
        ],
        "hidden": False
    },
]

###############################################################################
# We'll add new tests dynamically below
###############################################################################

def build_large_test(n, name, hidden=False, timeout=5):
    """
    Build a test dictionary that does a partial-identity times random approach
    and includes a naive O(n^3) multiply for expected output.
    """
    test_dict = {
        "name": name,
        "hidden": hidden,
        "timeout": timeout
    }

    A = partial_identity_matrix(n)
    B = random_matrix(n, -2, 2)

    C = multiply_matrices(A, B)

    a_str = matrix_to_str(A)
    b_str = matrix_to_str(B)
    test_dict["input"] = f"{n}\n{a_str}\n{b_str}"

    c_lines = [" ".join(str(x) for x in row) for row in C]
    test_dict["expected_output"] = (
        ["The resulting matrix C = A x B is:"] + c_lines
    )
    return test_dict

# Build two n=500 tests (previously hidden, now fully visible)
TEST_CASES.append(build_large_test(500, "Large Test 5: n=500 #1", hidden=False))
TEST_CASES.append(build_large_test(500, "Large Test 6: n=500 #2", hidden=False))

###############################################################################
# Command-Line Autograder Logic
###############################################################################

def compile_cpp_source():
    """
    Compile matrixmult.cpp if it exists.
    Return True if successful, False otherwise.
    """
    if not os.path.exists("matrixmult.cpp"):
        print("Error: matrixmult.cpp not found.")
        return False

    compile_cmd = ["g++", "-std=c++17", "-O3", "-fopenmp", "-o", "matrixmult", "matrixmult.cpp"]
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
        if line.startswith("Enter the dimension") or line.startswith("Enter the elements"):
            continue
        filtered_output.append(line)

    return filtered_output

def grade_test_case(test_case):
    """
    Run a single test case, compare output, and return a dictionary of results,
    including the time taken to run the test.
    """
    start_time = time.time()  # <-- start timing
    output_lines = run_test(test_case)
    end_time = time.time()    # <-- end timing

    test_duration = end_time - start_time

    expected_lines = test_case["expected_output"]
    passed = (len(output_lines) == len(expected_lines))
    if passed:
        for out_line, exp_line in zip(output_lines, expected_lines):
            if out_line != exp_line:
                passed = False
                break

    score = 1 if passed else 0
    max_score = 1

    # Build feedback
    feedback = []
    feedback.append(f"Expected ({len(expected_lines)} lines):")
    for l in expected_lines:
        feedback.append(f"  {l}")
    feedback.append(f"Got ({len(output_lines)} lines):")
    for l in output_lines:
        feedback.append(f"  {l}")

    result = {
        "name": test_case["name"],
        "score": score,
        "max_score": max_score,
        "time_elapsed_seconds": test_duration,  # <-- store duration
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

    for test in TEST_CASES:
        t_res = grade_test_case(test)
        test_results.append(t_res)
        total_score += t_res["score"]
        total_max_score += t_res["max_score"]

        # Print time for each test
        print(f"Test '{t_res['name']}' took {t_res['time_elapsed_seconds']:.4f} seconds.")

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

    # 5. Uncomment to print full results to stdout
    # print(json.dumps(results, indent=4))

    sys.exit(0)

if __name__ == "__main__":
    main()
