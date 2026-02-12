import subprocess
import sys
import re
import os

TEST_CASES = [
    {"name": "Small (100k ints)",     "N": 100000,     "threads": 4, "seed": 99},
    {"name": "Medium (1M) - Serial",  "N": 1000000,    "threads": 1, "seed": 123},
    {"name": "Medium (1M) - Parallel","N": 1000000,    "threads": 4, "seed": 123},
    {"name": "Large (10M) - Serial",  "N": 10000000,   "threads": 1, "seed": 777},
    {"name": "Large (10M) - Parallel","N": 10000000,   "threads": 8, "seed": 777},
]

def compile_code(cpp_file, exec_file):
    print(f"[*] Compiling {cpp_file}...")
    compile_cmd = ["g++", "-O3", "-std=c++17", "-fopenmp", "-pthread", cpp_file, "-o", exec_file]
    try:
        subprocess.run(compile_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("[+] Compilation successful!\n")
    except subprocess.CalledProcessError as e:
        print("[-] Compilation FAILED:\n")
        print(e.stderr.decode('utf-8'))
        sys.exit(1)

def run_test(exec_file, test):
    cmd = [exec_file, str(test["N"]), str(test["threads"]), str(test["seed"])]
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        match = re.search(r"RESULT:(PASS|FAIL),([0-9.]+)", result.stdout)
        if match:
            return match.group(1), float(match.group(2))
        else:
            print(f"[-] Missing valid output format on test {test['name']}")
            return "ERROR", 0.0

    except subprocess.CalledProcessError as e:
        print(f"[-] Execution crashed on test {test['name']}.")
        return "CRASH", 0.0

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <your_cpp_file.cpp>")
        sys.exit(1)

    cpp_file = sys.argv[1]
    exec_file = "./mergesort_eval"
    if os.name == 'nt':
        exec_file += ".exe"

    if not os.path.exists(cpp_file):
        print(f"[-] Error: Could not find '{cpp_file}'.")
        sys.exit(1)

    compile_code(cpp_file, exec_file)

    print(f"{'Test Name':<25} | {'N':<10} | {'Threads':<7} | {'Status':<6} | {'Time (s)':<10}")
    print("-" * 67)

    results_map = {}

    for test in TEST_CASES:
        status, time_sec = run_test(exec_file, test)

        status_str = f"\033[92m{status}\033[0m" if status == "PASS" else f"\033[91m{status}\033[0m"
        print(f"{test['name']:<25} | {test['N']:<10} | {test['threads']:<7} | {status_str:<15} | {time_sec:.4f}s")

        key = f"{test['N']}_{test['seed']}"
        if key not in results_map:
            results_map[key] = {}
        results_map[key][test['threads']] = time_sec

    print("\n[*] --- Scaling Analysis ---")
    for key, thread_times in results_map.items():
        if 1 in thread_times:
            serial_time = thread_times[1]
            for threads, par_time in thread_times.items():
                if threads > 1 and par_time > 0:
                    speedup = serial_time / par_time
                    N = key.split('_')[0]
                    print(f"    N = {N:<10} ({threads} threads): \033[96m{speedup:.2f}x speedup\033[0m")

if __name__ == "__main__":
    main()
