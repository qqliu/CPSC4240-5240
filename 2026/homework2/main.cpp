#include <iostream>
#include <vector>
#include <atomic>
#include <algorithm>
#include <omp.h>
#include <random>
#include <chrono>
#include <cstring>
#include <cassert>

// Threshold to switch to sequential execution
const int SERIAL_THRESHOLD = 4096;

// ============================================================
// TASK 1: LOCK-FREE BUFFER POOL FOR MERGES
// ============================================================

struct PoolNode {
    std::vector<int>* data;
    PoolNode* next;
};

class AtomicBufferPool {
    std::atomic<PoolNode*> head;

public:
    AtomicBufferPool() : head(nullptr) {}

    ~AtomicBufferPool() {
        PoolNode* curr = head.load();
        while (curr) {
            PoolNode* next = curr->next;
            delete curr->data;
            delete curr;
            curr = next;
        }
    }

    // TODO: Implement Lock-Free Pop using CAS loop
    std::vector<int>* acquire_buffer(size_t capacity) {
        std::vector<int>* vec_ptr = nullptr;

        // --- TODO: YOUR CODE HERE ---
        // 1. Load head. 2. CAS loop. 3. Handle empty case.

        // ----------------------

        // Fallback: If pool empty, allocate fresh
        if (vec_ptr == nullptr) {
            vec_ptr = new std::vector<int>();
        }

        if (vec_ptr->size() < capacity) {
            vec_ptr->resize(capacity);
        }
        return vec_ptr;
    }

    // TODO: Implement Lock-Free Push using CAS loop
    void release_buffer(std::vector<int>* buf) {
        // --- TODO: YOUR CODE HERE ---
        // 1. Create node. 2. CAS loop to push to head.

        // ----------------------
    }
};

AtomicBufferPool pool;

// ============================================================
// TASK 2: PARALLEL MERGE OF TWO VECTORS
// ============================================================

void seq_merge(int* A, int nA, int* B, int nB, int* C) {
    std::merge(A, A + nA, B, B + nB, C);
}

// TODO: Implement the Divide-and-Conquer Parallel Merge
// Follow the algorithm described in the assignment PDF.
void parallel_binary_merge(int* A, int nA, int* B, int nB, int* C) {
    // 1. Base Case (use seq_merge)

    // 2. Ensure A is larger (Swap if needed)

    // 3. Find Median of A

    // 4. Binary Search Median in B

    // 5. Place Median in C

    // 6. Spawn 2 Recursive Tasks (Left and Right)

    // 7. Wait
}

// ============================================================
// TASK 3: 4-WAY MERGESORT
// ============================================================

void mergesort_4way(int* arr, int n) {
    if (n < SERIAL_THRESHOLD) {
        std::sort(arr, arr + n);
        return;
    }

    // 1. Calculate Splits
    int q = n / 4;
    int r = n % 4;
    int s1 = q, s2 = q, s3 = q, s4 = q + r;

    int* p1 = arr;
    int* p2 = p1 + s1;
    int* p3 = p2 + s2;
    int* p4 = p3 + s3;

    // TODO: Spawn 4 Parallel Tasks to sort p1, p2, p3, p4
    // Use #pragma omp task

    // --- TODO: YOUR CODE HERE ---

    // ----------------------

    // 2. Acquire Buffer
    std::vector<int>* temp_vec = pool.acquire_buffer(n);
    int* T = temp_vec->data();
    int* T_mid = T + (s1 + s2);

    // 3. Parallel Merge Phase
    // Merge (Q1+Q2) -> Left Half of T
    // Merge (Q3+Q4) -> Right Half of T
    // TODO: Launch in parallel tasks calling parallel_binary_merge

    // --- TODO: YOUR CODE HERE ---

    // ----------------------

    // 4. Final Merge: Left+Right -> Original Array
    parallel_binary_merge(T, s1 + s2, T_mid, s3 + s4, arr);

    // 5. Cleanup
    pool.release_buffer(temp_vec);
}

// ============================================================
// COMMAND-LINE AND GRADESCOPE TESTS (DO NOT MODIFY)
// ============================================================
int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "Usage: " << argv[0] << " <N> <num_threads> <seed>\n";
        return 1;
    }

    int N = std::stoi(argv[1]);
    int num_threads = std::stoi(argv[2]);
    unsigned int seed = std::stoul(argv[3]);

    std::vector<int> data(N);
    std::mt19937 rng(seed);
    for (int i = 0; i < N; ++i) {
        data[i] = rng();
    }

    std::vector<int> check = data;

    omp_set_num_threads(num_threads);
    omp_set_nested(1);
    omp_set_dynamic(0);

    double start_time = omp_get_wtime();

    #pragma omp parallel
    {
        #pragma omp single
        {
            mergesort_4way(data.data(), N);
        }
    }

    double end_time = omp_get_wtime();
    double elapsed = end_time - start_time;

    std::sort(check.begin(), check.end());
    bool passed = (data == check);

    // Output formatted string for Python tester
    if (passed) {
        std::cout << "RESULT:PASS," << elapsed << "\n";
        return 0;
    } else {
        std::cout << "RESULT:FAIL," << elapsed << "\n";
        return 1;
    }
}
