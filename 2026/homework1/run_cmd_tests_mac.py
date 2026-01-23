#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import random
import time

VERIFY_THRESHOLD = 150
TEST_SIZES = [10, 50, 100, 150, 500, 1000]

# Timeout for large tests (seconds)
TIMEOUT_SEC = 60

###############################################################################
# Helper Functions
###############################################################################

def matrix_to_str(mat):
    return "\n".join(" ".join(str(x) for x in row) for row in mat)

def generate_random_input(n):
    # Create random matrices
    A = [[random.randint(-2, 2) for _ in range(n)] for _ in range(n)]
    B = [[random.randint(-2, 2) for _ in range(n)] for _ in range(n)]

    # D and E are duplicates of A and B
    D = [row[:] for row in A]
    E = [row[:] for row in B]

    input_parts = [str(n)]
    input_parts.append(matrix_to_str(A))
    input_parts.append(matrix_to_str(B))
    input_parts.append(matrix_to_str(D))
    input_parts.append(matrix_to_str(E))

    input_str = "\n".join(input_parts) + "\n"

    # Expected output for verification (only for small N)
    expected_flat = None
    if n < VERIFY_THRESHOLD:
        C = [[0]*n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                s = 0
                for k in range(n):
                    s += A[i][k] * B[k][j]
                C[i][j] = s
        c_flat = [x for row in C for x in row]
        expected_flat = c_flat + c_flat # For C and F

    return input_str, expected_flat

###############################################################################
# macOS Robust Compilation Logic
###############################################################################

def compile_cpp_source():
    if not os.path.exists("matrixmult.cpp"):
        print("Error: matrixmult.cpp not found.")
        return False

    compiler = "g++"

    # Default Flags (Linux/Standard)
    flags = ["-std=c++17", "-O3", "-fopenmp", "-pthread", "-I."]

    # macOS Specific Logic
    if sys.platform == "darwin":
        print("Detected macOS. Configuring OpenMP flags...")
        # Apple Clang requires -Xpreprocessor -fopenmp and linking libomp explicitly
        flags = [
            "-std=c++17",
            "-O3",
            "-Xpreprocessor", "-fopenmp",
            "-lomp",
            "-pthread",
            "-I."
        ]

        # 1. Try finding libomp via brew (Most robust method)
        found_libomp = False
        try:
            brew_prefix = subprocess.check_output(["brew", "--prefix", "libomp"]).decode().strip()
            flags.extend([f"-I{brew_prefix}/include", f"-L{brew_prefix}/lib"])
            print(f"  -> Found libomp via brew at: {brew_prefix}")
            found_libomp = True
        except Exception:
            pass

        # 2. Fallback paths if brew command failed
        if not found_libomp:
            if os.path.exists("/opt/homebrew/include"): # Apple Silicon default
                flags.extend(["-I/opt/homebrew/include", "-L/opt/homebrew/lib"])
                print("  -> Using fallback path: /opt/homebrew")
            elif os.path.exists("/usr/local/include"): # Intel Mac default
                flags.extend(["-I/usr/local/include", "-L/usr/local/lib"])
                print("  -> Using fallback path: /usr/local")

    compile_cmd = [compiler] + flags + ["-o", "matrixmult", "matrixmult.cpp"]
    print(f"Compiling: {' '.join(compile_cmd)}")

    try:
        subprocess.run(compile_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print("\nCompilation failed!")
        print("Ensure you have installed libomp: 'brew install libomp'")
        print("stderr:", e.stderr.decode())
        return False

###############################################################################
# Execution Logic (Parses Separate Times)
###############################################################################

def run_test_and_parse(n, input_str, expected_flat):
    """
    Runs the C++ binary.
    Returns: (time_c, time_f, status)
    """
    try:
        proc = subprocess.run(
            ["./matrixmult"],
            input=input_str.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_SEC
        )
    except subprocess.TimeoutExpired:
        return -1, -1, "TIMEOUT"

    output_lines = proc.stdout.decode("utf-8").strip().splitlines()

    # 1. Verification (Check correctness of math)
    if expected_flat is not None:
        try:
            flat_output = []
            for line in output_lines:
                line = line.strip()
                if not line: continue
                # Skip the TIME_ tags during matrix number parsing
                if line.startswith("TIME_"): continue

                parts = line.split()
                # If line starts with a number or minus sign, treat as matrix row
                if len(parts) > 0 and parts[0].lstrip("-").isdigit():
                    flat_output.extend([int(x) for x in parts])

            if flat_output != expected_flat:
                return -1, -1, "MISMATCH"
        except Exception:
            return -1, -1, "PARSE_ERR"

    # 2. Extract internal C++ times
    time_c = -1.0
    time_f = -1.0

    for line in output_lines:
        if line.startswith("TIME_C:"):
            try:
                time_c = float(line.split(":")[1])
            except: pass
        if line.startswith("TIME_F:"):
            try:
                time_f = float(line.split(":")[1])
            except: pass

    if time_c == -1.0 or time_f == -1.0:
        return -1, -1, "NO_TIME_DATA"

    return time_c, time_f, "OK"

###############################################################################
# Main
###############################################################################

def main():
    if not compile_cpp_source():
        sys.exit(1)

    print(f"\nRunning Performance Tests for Sizes: {TEST_SIZES}")
    print(f"{'SIZE':<10} | {'TIME C (sec)':<15} | {'TIME F (sec)':<15} | {'STATUS'}")
    print("-" * 60)

    results = []

    for n in TEST_SIZES:
        # Generate Input
        input_str, expected_flat = generate_random_input(n)

        # Run once (C++ code calculates both C and F times internally)
        t_c, t_f, status = run_test_and_parse(n, input_str, expected_flat)

        if n >= VERIFY_THRESHOLD and status == "OK":
            status = "Perf Only"

        # Format output
        sc = f"{t_c:.6f}" if t_c >= 0 else "N/A"
        sf = f"{t_f:.6f}" if t_f >= 0 else "N/A"

        print(f"{n:<10} | {sc:<15} | {sf:<15} | {status}")

        results.append({
            "size": n,
            "time_c": t_c,
            "time_f": t_f,
            "status": status
        })

    with open("results.json", "w") as f:
        json.dump(results, f, indent=4)

    print("-" * 60)
    print("Done. Results saved to results.json")

if __name__ == "__main__":
    main()
