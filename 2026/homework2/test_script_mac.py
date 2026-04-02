import subprocess
import sys
import re
import os
import statistics
import platform

TEST_CASES = [
    {"name": "Small (100k ints)",     "N": 100000,     "threads": 4, "seed": 99},
    {"name": "Medium (1M) - Serial",  "N": 1000000,    "threads": 1, "seed": 123},
    {"name": "Medium (1M) - Parallel","N": 1000000,    "threads": 4, "seed": 123},
    {"name": "Large (10M) - Serial",  "N": 10000000,   "threads": 1, "seed": 777},
    {"name": "Large (10M) - Parallel","N": 10000000,   "threads": 8, "seed": 777},
]

NUM_ATTEMPTS=5


def get_m3_compile_cmd(cpp_file, exec_file):
    """
    Constructs the clang++ command for Apple Silicon Macs using Homebrew libomp.
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
        print("    Please run: \033[96mbrew install libomp\033[0m\n")
        sys.exit(1)

    print(f"[*] Found libomp at: {omp_prefix}")
    return [
        "clang++", "-O3", "-std=c++17",
        "-Xpreprocessor", "-fopenmp",
        f"-I{omp_prefix}/include",
        f"-L{omp_prefix}/lib",
        "-lomp",
        cpp_file, "-o", exec_file
    ]

def compile_code(cpp_file, exec_file):
    print(f"[*] Compiling {cpp_file}...")
    if platform.system() == "Darwin":
        compile_cmd = get_m3_compile_cmd(cpp_file, exec_file)
    else:
        compile_cmd = ["g++", "-O3", "-std=c++17", "-fopenmp", "-pthread", cpp_file, "-o", exec_file]
    try:
        subprocess.run(compile_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("[+] Compilation successful!\n")
    except subprocess.CalledProcessError as e:
        print("[-] Compilation FAILED:\n")
        print(e.stderr.decode('utf-8'))
        sys.exit(1)


def compile_baseline(baseline_cpp, baseline_exec):
    """Compile std::sort baseline (no OpenMP)."""
    print(f"[*] Compiling baseline (std::sort)...")
    cmd = ["clang++", "-O3", "-std=c++17", baseline_cpp, "-o", baseline_exec]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("[+] Baseline compiled.\n")
    except subprocess.CalledProcessError as e:
        print("[-] Baseline compilation failed:", e.stderr.decode('utf-8')[:200])
        sys.exit(1)


def run_baseline(baseline_exec, N, seed):
    """Run std::sort baseline, return time in seconds."""
    result = subprocess.run([baseline_exec, str(N), str(seed)], capture_output=True, text=True)
    match = re.search(r"BASELINE,([0-9.]+)", result.stdout)
    if match:
        return float(match.group(1))
    return None

def run_test(exec_file, test):
    cmd = [exec_file, str(test["N"]), str(test["threads"]), str(test["seed"])]
    result = subprocess.run(cmd, capture_output=True, text=True)

    match = re.search(r"RESULT:(PASS|FAIL),([0-9.]+)", result.stdout)
    if match:
        return match.group(1), float(match.group(2))
    else:
        # No valid RESULT line — likely crashed (segfault, etc.)
        if result.returncode != 0 and result.stderr:
            print(f"[-] Execution crashed on test {test['name']}: {result.stderr[:200]}")
        else:
            print(f"[-] Missing valid output format on test {test['name']}")
        return "CRASH" if result.returncode != 0 else "ERROR", 0.0

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

    script_dir = os.path.dirname(os.path.abspath(cpp_file)) or "."
    baseline_cpp = os.path.join(script_dir, "baseline_std_sort.cpp")
    baseline_exec = os.path.join(script_dir, "baseline_std_sort")
    if os.path.exists(baseline_cpp):
        compile_baseline(baseline_cpp, baseline_exec)

    # Run std::sort baseline for each unique (N, seed)
    baseline_times = {}
    if os.path.exists(baseline_exec):
        for test in TEST_CASES:
            key = f"{test['N']}_{test['seed']}"
            if key not in baseline_times:
                times = []
                for _ in range(NUM_ATTEMPTS):
                    t = run_baseline(baseline_exec, test["N"], test["seed"])
                    if t is not None:
                        times.append(t)
                baseline_times[key] = statistics.median(times) if times else None

    print(f"{'Test Name':<25} | {'N':<10} | {'Threads':<7} | {'Status':<6} | {'Time (s)':<10} | {'vs std::sort':<12}")
    print("-" * 95)

    results_map = {}

    for test in TEST_CASES:
        overall_status = "PASS"
        attempt_times = []
        for iteration in range(NUM_ATTEMPTS):
            status, time_sec = run_test(exec_file, test)
            if status != "PASS":
                overall_status = status
                break
            attempt_times.append(time_sec)

        time_sec = statistics.median(attempt_times) if attempt_times else 0.0
        status_str = f"\033[92m{status}\033[0m" if status == "PASS" else f"\033[91m{status}\033[0m"

        key = f"{test['N']}_{test['seed']}"
        vs_std = ""
        if key in baseline_times and baseline_times[key] and time_sec > 0:
            speedup = baseline_times[key] / time_sec
            vs_std = f"{speedup:.2f}x"
            if test["threads"] > 1 and speedup < 3.0:
                vs_std = f"\033[91m{speedup:.2f}x (<3x)\033[0m"
            elif speedup >= 3.0:
                vs_std = f"\033[96m{speedup:.2f}x\033[0m"
        else:
            vs_std = "—"

        print(f"{test['name']:<25} | {test['N']:<10} | {test['threads']:<7} | {status_str:<15} | {time_sec:.4f}s   | {vs_std}")

        if key not in results_map:
            results_map[key] = {}
        results_map[key][test['threads']] = time_sec

    print("\n[*] --- Scaling Analysis (parallel vs serial mergesort) ---")
    for key, thread_times in results_map.items():
        if 1 in thread_times:
            serial_time = thread_times[1]
            for threads, par_time in thread_times.items():
                if threads > 1 and par_time > 0:
                    speedup = serial_time / par_time
                    N = key.split('_')[0]
                    print(f"    N = {N:<10} ({threads} threads): \033[96m{speedup:.2f}x speedup\033[0m")

    print("\n[*] --- vs std::sort (need ≥3x for parallel cases) ---")
    for test in TEST_CASES:
        if test["threads"] > 1:
            key = f"{test['N']}_{test['seed']}"
            if key in baseline_times and baseline_times[key] and key in results_map:
                par_time = results_map[key].get(test["threads"])
                if par_time and par_time > 0:
                    speedup = baseline_times[key] / par_time
                    status = "\033[92mOK\033[0m" if speedup >= 3.0 else "\033[91mBELOW 3x\033[0m"
                    print(f"    {test['name']}: {speedup:.2f}x vs std::sort  [{status}]")

if __name__ == "__main__":
    main()