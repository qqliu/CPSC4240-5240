#!/usr/bin/env python3
import subprocess
import sys
import re
import os
import platform

TEST_CASES = [
    {"name": "Warmup (100k ints)",    "N": 100000,   "threads": 4, "seed": 42},
    {"name": "Medium (1M) - Serial",  "N": 1000000,  "threads": 1, "seed": 123},
    {"name": "Medium (1M) - Par(4)",  "N": 1000000,  "threads": 4, "seed": 123},
    {"name": "Medium (1M) - Par(8)",  "N": 1000000,  "threads": 8, "seed": 123},
    {"name": "Large (25M) - Serial",  "N": 25000000, "threads": 1, "seed": 777},
    {"name": "Large (25M) - Par(4)",  "N": 25000000, "threads": 4, "seed": 777},
    {"name": "Large (25M) - Par(8)",  "N": 25000000, "threads": 8, "seed": 777},
]

def get_m3_compile_cmd(cpp_file, exec_file):
    """
    Constructs the correct clang++ command for Apple Silicon.
    Apple's default clang requires libomp from Homebrew.
    """
    print("[*] Detecting Apple Silicon OpenMP installation...")
    try:
        omp_prefix = subprocess.check_output(["brew", "--prefix", "libomp"], text=True).strip()
    except FileNotFoundError:
        print("\n[\033[91mFAIL\033[0m] 'brew' command not found.")
        print("    You must install Homebrew first: https://brew.sh/")
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("\n[\033[91mFAIL\033[0m] OpenMP library not found on your Mac.")
        print("    Please open your terminal and run:")
        print("    \033[96mbrew install libomp\033[0m\n")
        sys.exit(1)

    print(f"[*] Found libomp at: {omp_prefix}")

    return [
        "clang++", "-O3", "-std=c++17",
        "-Xpreprocessor", "-fopenmp",      # Apple clang OpenMP flags
        f"-I{omp_prefix}/include",         # Header files
        f"-L{omp_prefix}/lib",             # Library files
        "-lomp",                           # Link OpenMP
        cpp_file, "-o", exec_file
    ]

def compile_code(cpp_file, exec_file):
    print(f"[*] Compiling \033[96m{cpp_file}\033[0m...")

    if platform.system() == "Darwin" and platform.machine() == "arm64":
        compile_cmd = get_m3_compile_cmd(cpp_file, exec_file)
    else:
        print("[\033[93mWARNING\033[0m] You do not appear to be on a Mac M-Series (Apple Silicon).")
        print("          Falling back to standard GCC compilation...")
        compile_cmd = ["g++", "-O3", "-std=c++17", "-fopenmp", "-pthread", cpp_file, "-o", exec_file]

    try:
        subprocess.run(compile_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("[\033[92mSUCCESS\033[0m] Compilation finished.\n")
    except subprocess.CalledProcessError as e:
        print("[\033[91mCOMPILE ERROR\033[0m]\n")
        print(e.stderr.decode('utf-8'))
        sys.exit(1)

def run_test(exec_file, test):
    cmd = [exec_file, str(test["N"]), str(test["threads"]), str(test["seed"])]
    try:
        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = str(test["threads"])

        result = subprocess.run(cmd, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        match = re.search(r"RESULT:(PASS|FAIL),([0-9.]+)", result.stdout)
        if match:
            return match.group(1), float(match.group(2))
        else:
            print(f"[-] Missing valid output format on test {test['name']}")
            print(f"    Raw Output: {result.stdout.strip()}")
            return "ERROR", 0.0

    except subprocess.CalledProcessError as e:
        print(f"[-] Execution crashed on test {test['name']}.")
        return "CRASH", 0.0

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <your_cpp_file.cpp>")
        sys.exit(1)

    cpp_file = sys.argv[1]
    exec_file = "./mergesort_m3_eval"

    if not os.path.exists(cpp_file):
        print(f"[-] Error: Could not find '{cpp_file}'.")
        sys.exit(1)

    compile_code(cpp_file, exec_file)

    print(f"{'Test Name':<25} | {'N':<10} | {'Threads':<7} | {'Status':<6} | {'Time (s)':<10}")
    print("-" * 67)

    results_map = {}

    for test in TEST_CASES:
        status, time_sec = run_test(exec_file, test)

        if status == "PASS":
            status_str = f"\033[92m{status}\033[0m"
        elif status == "FAIL":
            status_str = f"\033[91m{status}\033[0m"
        else:
            status_str = f"\033[93m{status}\033[0m"

        print(f"{test['name']:<25} | {test['N']:<10} | {test['threads']:<7} | {status_str:<15} | {time_sec:.4f}s")

        key = f"{test['N']}_{test['seed']}"
        if key not in results_map:
            results_map[key] = {}
        results_map[key][test['threads']] = time_sec

    print("\n[*] --- M3 Scaling Analysis ---")
    print("    Note: M-Series chips have asymmetric Performance (P) and Efficiency (E) cores.")
    print("    Scaling may not be perfectly linear when pushing past the P-core limit.\n")

    for key, thread_times in results_map.items():
        if 1 in thread_times:
            serial_time = thread_times[1]
            for threads, par_time in sorted(thread_times.items()):
                if threads > 1 and par_time > 0:
                    speedup = serial_time / par_time
                    N = key.split('_')[0]

                    color = "\033[96m" if speedup >= (threads * 0.6) else "\033[93m"
                    print(f"    N = {N:<10} ({threads} threads): {color}{speedup:.2f}x speedup\033[0m")

    if os.path.exists(exec_file):
        os.remove(exec_file)

if __name__ == "__main__":
    main()
