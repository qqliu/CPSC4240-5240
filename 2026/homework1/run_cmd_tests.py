#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import random
import time

VERIFY_THRESHOLD = 150

# The specific test sizes requested
TEST_SIZES = [10, 50, 100, 150, 500, 1000]

###############################################################################
# Helper Functions
###############################################################################

def matrix_to_str(mat):
    """
    Convert a 2D list (matrix) into a multiline string, row by row.
    """
    return "\n".join(" ".join(str(x) for x in row) for row in mat)

def generate_random_input(n):
    """
    Generates the full input string for the C++ program:
    N, then Matrix A, B, D, E.
    Returns (input_string, expected_C_flattened)

    Note: expected_C will be None if n >= VERIFY_THRESHOLD
    """
    # Create random matrices
    # Range -2 to 2 keeps numbers small to prevent overflow parsing issues
    A = [[random.randint(-2, 2) for _ in range(n)] for _ in range(n)]
    B = [[random.randint(-2, 2) for _ in range(n)] for _ in range(n)]

    # D and E are duplicates of A and B for consistent timing checks
    D = [row[:] for row in A]
    E = [row[:] for row in B]

    # Convert to input string
    input_parts = [str(n)]
    input_parts.append(matrix_to_str(A))
    input_parts.append(matrix_to_str(B))
    input_parts.append(matrix_to_str(D))
    input_parts.append(matrix_to_str(E))

    input_str = "\n".join(input_parts) + "\n"

    # Only calculate expected output if N is small enough
    expected_flat = None

    if n < VERIFY_THRESHOLD:
        # Naive Python Multiply for verification
        C = [[0]*n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                s = 0
                for k in range(n):
                    s += A[i][k] * B[k][j]
                C[i][j] = s

        # Flatten C for easy comparison
        c_flat = [x for row in C for x in row]
        # Since D=A and E=B, F must equal C.
        # The output order is C then F, so we duplicate the expected data.
        expected_flat = c_flat + c_flat

    return input_str, expected_flat

###############################################################################
# Compilation Logic (Robust)
###############################################################################

def compile_cpp_source():
    """
    Compile matrixmult.cpp. Includes macOS specific flags for OpenMP.
    """
    if not os.path.exists("matrixmult.cpp"):
        print("Error: matrixmult.cpp not found.")
        return False

    compiler = "g++"
    flags = ["-std=c++17", "-O3", "-fopenmp", "-pthread", "-I."]

    # macOS Logic (Apple Clang support)
    if sys.platform == "darwin":
        flags = [
            "-std=c++17", "-O3", "-Xpreprocessor", "-fopenmp",
            "-lomp", "-pthread", "-I."
        ]
        # Auto-detect libomp
        try:
            brew_prefix = subprocess.check_output(["brew", "--prefix", "libomp"]).decode().strip()
            flags.extend([f"-I{brew_prefix}/include", f"-L{brew_prefix}/lib"])
        except Exception:
            if os.path.exists("/opt/homebrew/include"):
                flags.extend(["-I/opt/homebrew/include", "-L/opt/homebrew/lib"])
            elif os.path.exists("/usr/local/include"):
                flags.extend(["-I/usr/local/include", "-L/usr/local/lib"])

    compile_cmd = [compiler] + flags + ["-o", "matrixmult", "matrixmult.cpp"]
    print(f"Compiling: {' '.join(compile_cmd)}")

    try:
        subprocess.run(compile_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print("Compilation failed.")
        print("stderr:", e.stderr.decode())
        return False

###############################################################################
# Execution Logic
###############################################################################

def run_performance_test(n, input_str, expected_flat):
    """
    Runs the C++ binary with the given input.
    Returns: (time_elapsed, passed_boolean)
    """
    start_time = time.time()

    try:
        # Timeout scales with N. N=1000 might take a few seconds.
        # Giving generous timeout (60s) for the largest cases.
        proc = subprocess.run(
            ["./matrixmult"],
            input=input_str.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )
    except subprocess.TimeoutExpired:
        return -1.0, False

    end_time = time.time()
    duration = end_time - start_time

    # Validation (Only if expected_flat is provided)
    passed = True
    if expected_flat is not None:
        output_lines = proc.stdout.decode("utf-8").strip().splitlines()

        # Parse output to find matrix numbers.
        try:
            flat_output = []
            for line in output_lines:
                # Ignore text headers, look for lines starting with numbers or minus signs
                if not line: continue
                parts = line.split()
                # Check if the line looks like matrix data
                if parts[0].lstrip("-").isdigit():
                    flat_output.extend([int(x) for x in parts])

            if flat_output != expected_flat:
                passed = False
        except Exception:
            passed = False

    return duration, passed

###############################################################################
# Main
###############################################################################

def main():
    if not compile_cpp_source():
        sys.exit(1)

    print(f"\nRunning Performance Tests for Sizes: {TEST_SIZES}")
    print(f"{'SIZE':<10} | {'RUN 1 (C) TIME':<20} | {'RUN 2 (F) TIME':<20} | {'STATUS'}")
    print("-" * 75)

    results = []

    # Iterate through the requested sizes
    for n in TEST_SIZES:
        # 1. Generate Input
        # (Done once per size, used for both runs)
        input_str, expected_flat = generate_random_input(n)

        # 2. Run 1 (Simulating "Run for C")
        time_c, passed_c = run_performance_test(n, input_str, expected_flat)

        # 3. Run 2 (Simulating "Run for F")
        time_f, passed_f = run_performance_test(n, input_str, expected_flat)

        # 4. Determine Status
        status = "OK"
        if time_c < 0 or time_f < 0:
            status = "TIMEOUT"
        elif n < VERIFY_THRESHOLD and (not passed_c or not passed_f):
            status = "MISMATCH"
        elif n >= VERIFY_THRESHOLD:
            status = "Perf Only"

        # 5. Output Row
        c_str = f"{time_c:.4f}s" if time_c >= 0 else "TIMEOUT"
        f_str = f"{time_f:.4f}s" if time_f >= 0 else "TIMEOUT"

        print(f"{n:<10} | {c_str:<20} | {f_str:<20} | {status}")

        results.append({
            "size": n,
            "time_c": time_c,
            "time_f": time_f,
            "status": status
        })

    # Save results to JSON (maintaining original script's behavior)
    with open("results.json", "w") as f:
        json.dump(results, f, indent=4)

    print("-" * 75)
    print("Done. Results saved to results.json")

if __name__ == "__main__":
    main()
