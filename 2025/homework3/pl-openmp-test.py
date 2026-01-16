#!/usr/bin/env python3
import subprocess
import struct
import sys
import numpy as np

def compile_cpp():
    """
    Compiles the C++ source file (pl-openmp.cpp) to produce the executable 'openmp_test'.
    Adjust the compile command as needed for your platform.
    """
    # Example for Linux:
    compile_command = ["g++", "-O3", "-fopenmp", "-o", "openmp_test", "pl-openmp.cpp"]
    # If you are on macOS and have OpenMP installed via Homebrew, you might need:
    # compile_command = ["g++", "-O3", "-Xpreprocessor", "-fopenmp", "-lomp", "-o", "openmp_test", "pl-openmp.cpp"]

    try:
        print("Compiling C++ code...")
        subprocess.run(compile_command, check=True)
        print("Compilation successful.\n")
    except subprocess.CalledProcessError as e:
        print("Compilation failed!")
        sys.exit(1)

def parse_cpp_output(output):
    """
    Extract the final sum and the time taken from the C++ output.
    Expected output is two lines, for example:
        "Final sum: 1613\nTime taken: 0.001234 seconds\n"
    Returns a tuple: (final_sum, time_taken)
    """
    if isinstance(output, bytes):
        output = output.decode("utf-8")
    final_sum = None
    time_taken = None
    for line in output.splitlines():
        if line.startswith("Final sum:"):
            try:
                # Convert via float then int to handle scientific notation.
                final_sum = int(float(line[len("Final sum:"):].strip()))
            except Exception as e:
                raise ValueError(f"Error converting final sum to int: {e}")
        elif line.startswith("Time taken:"):
            try:
                # Remove the prefix and "seconds" suffix if present.
                s = line[len("Time taken:"):].strip()
                if s.endswith("seconds"):
                    s = s[:-len("seconds")].strip()
                time_taken = float(s)
            except Exception as e:
                raise ValueError(f"Error converting time taken to float: {e}")
    if final_sum is None:
        raise ValueError("Final sum not found in output")
    if time_taken is None:
        raise ValueError("Time taken not found in output")

    return final_sum, time_taken

def run_cpp_executable(N, A, B, executable="./openmp_test"):
    """
    Pack the data in binary (N as int64, then A and B as int64 arrays) and run the C++ executable.
    Returns the final sum (an integer) parsed from the executable's output.
    """
    # Pack N as a 64-bit signed integer.
    data = struct.pack("q", N)
    # Pack A and B as int64 arrays.
    data += A.astype(np.int64).tobytes()
    data += B.astype(np.int64).tobytes()

    proc = subprocess.run([executable],
                          input=data,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    if proc.returncode != 0:
        print("Error running executable:")
        print(proc.stderr.decode("utf-8"))
        sys.exit(1)
    try:
        result = parse_cpp_output(proc.stdout)
    except Exception as e:
        print("Error parsing result:", e)
        sys.exit(1)
    return result

def simulate_algorithm_py(A, B):
    """
    Pure Python simulation of the algorithm using integer arithmetic.
    A and B are assumed to be numpy arrays of int64.
    """
    N = len(A)
    A_sim = A.copy().astype(np.int64)
    B_sim = B.copy().astype(np.int64)

    # Step 1: A[i] = A[i] + i.
    for i in range(N):
        A_sim[i] += i

    # Step 2: For i in [0, N): B[i] = B[i] + (i % 2)
    for i in range(N):
        B_sim[i] += (i % 2)

    # Step 3a: For i in [0, N): B[i] += A[i] + B[2*i + (i % 2)]
    for i in range(N):
        idx = i + N
        if idx < 2 * N:
            B_sim[i] += A_sim[i] + B_sim[idx]

    # Step 3b: For i in [N, 2*N): B[i] += A[i-N] + A[i-N] + B[i-N]
    for i in range(N, 2 * N):
        j = i - N
        B_sim[i] += 2 * A_sim[j] + B_sim[j]

    # Step 4: For i in [1, N): A[i] = (B[i] + B[i-1]) / 2.0
    for i in range(0, N):
        A_sim[i] = (B_sim[i] + B_sim[N-i]) / 2.0

    return np.sum(A_sim)

def main():
    # First, compile the C++ code.
    compile_cpp()

    # Optionally, set a random seed for reproducibility.
    # np.random.seed(42)

    test_sizes = [10, 100, 1000, 10000, 1000000, 10000000, 100000000]
    # With integer arithmetic we expect an exact match.
    all_passed = True
    executable = "./openmp_test"  # Adjust the path if needed.

    for N in test_sizes:
        # Generate random integers in the range [1, 100].
        A = np.random.randint(1, 101, size=(N,)).astype(np.int64)
        B = np.random.randint(1, 101, size=(2 * N,)).astype(np.int64)

        expected = simulate_algorithm_py(A, B)
        result = run_cpp_executable(N, A, B, executable=executable)
        answer = result[0]
        seconds = result[1]

        print(f"Test with N = {N}: expected {expected}, got {answer}; seconds: {seconds}")
        if answer == expected:
            print("  PASS")
        else:
            print("  FAIL")
            all_passed = False

    if not all_passed:
        sys.exit(1)

if __name__ == '__main__':
    main()
