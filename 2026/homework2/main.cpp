#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstddef>
#include <cstring>
#include <iostream>
#include <omp.h>
#include <random>
#include <vector>

// Threshold to switch to sequential execution
const int SERIAL_THRESHOLD = 4096;

// ============================================================
// TASK 1: LOCK-FREE BUFFER POOL FOR MERGES
// ============================================================

// each node maintains a pointer to its data in the memory and a pointer to the
// next. implements a singly-linked list
struct PoolNode {
  std::vector<int> *data; // pointer to a vector of integers, the data
  PoolNode *next;         // pointer to the next PoolNode.
};

class AtomicBufferPool {
  std::atomic<PoolNode *> head; // reads and writes to a pointer to the head
                                // PoolNode without data races

public: // use public to make sure code outside of this class are able to access
        // this
  // constructor method for the AtomicBufferPool
  AtomicBufferPool() : head(nullptr) {} // assign head to a nullptr name(value)

  // destructor mehod, run when AtomicBufferPool object is destroyed and
  // frees allocated resources. have to delete the vector and the poolnode
  ~AtomicBufferPool() { // ~ marks this as a destructor
    PoolNode *curr =
        head.load(); // loads in the value of the atomic head
                     // and stores it in curr
                     // .load() is the method of reading an atomic
                     // currently points to the head node (or nullptr)
    while (curr) {
      PoolNode *next = curr->next; // use a temp pointer to save the next node
      delete curr->data; // delete the vector stored at the data pointer
                         // of the curr node
      delete curr;       // delete the PoolNode
      curr = next;       // go to the next in the list
    }
  }

  // TODO: Implement Lock-Free Pop using CAS loop
  std::vector<int> *acquire_buffer(size_t capacity) { // returns a pointer to an
                                                      // int vector
    std::vector<int> *vec_ptr = nullptr;

    // --- TODO: YOUR CODE HERE ---
    // 1. Load head. 2. CAS loop. 3. Handle empty case.
    PoolNode *old_head =
        head.load(std::memory_order_relaxed); // load the curr head
                                              // this is the "old"
                                              // head to be deleted
    while (old_head != nullptr) {
      PoolNode *new_head = old_head->next; // "pop" the old head
      if (head.compare_exchange_weak(old_head, new_head,
                                     std::memory_order_acquire,
                                     std::memory_order_relaxed)) {
        vec_ptr = old_head->data;
        delete old_head;
        break;
      }
    }

    // ----------------------

    // Fallback: If pool empty, allocate fresh
    if (vec_ptr == nullptr) {           // if the head is empty
      vec_ptr = new std::vector<int>(); // create a new empty vector
    }

    if (vec_ptr->size() < capacity) { // check size of the vector
      vec_ptr->resize(capacity); // resize to the correct capacity if needed
    }
    return vec_ptr;
  }

  // TODO: Implement Lock-Free Push using CAS loop
  void release_buffer(std::vector<int> *buf) {
    // --- TODO: YOUR CODE HERE ---
    // 1. Create node. 2. CAS loop to push to head.
    PoolNode *node = new PoolNode{buf, nullptr};
    PoolNode *old_head = head.load(std::memory_order_relaxed);
    do {
      node->next = old_head;
    } while (!head.compare_exchange_weak(
        old_head, node, std::memory_order_release, std::memory_order_relaxed));

    // ----------------------
  }
};

AtomicBufferPool pool;

// ============================================================
// TASK 2: PARALLEL MERGE OF TWO VECTORS
// ============================================================

void seq_merge(int *A, int nA, int *B, int nB, int *C) {
  std::merge(A, A + nA, B, B + nB, C);
}

// TODO: Implement the Divide-and-Conquer Parallel Merge
// Follow the algorithm described in the assignment PDF.
void parallel_binary_merge(int *A, int nA, int *B, int nB, int *C) {
  // 1. Base Case (use seq_merge)
  if (nA + nB < 4096) {
    seq_merge(A, nA, B, nB, C);
    return;
  }

  // 2. Ensure A is larger (Swap if needed)
  if (nA < nB) {
    int *T = A;
    int nT = nA;

    // swap
    A = B;
    nA = nB;
    B = T;
    nB = nT;
  }

  // 3. Find Median of A
  int mid = nA / 2;
  int median = A[mid];

  // 4. Binary Search Median in B
  int l = 0;
  int r = nB;
  int j = -1;
  while (l < r) {
    int m = l + (r - l) / 2;
    if (B[m] < median) {
        l = m + 1;
    } else if (B[m] >= median) {
        r = m;
    }
  }
  j = l;

  // 5. Place Median in C
  C[mid + j] = median;

  // 6. Spawn 2 Recursive Tasks (Left and Right)
  # pragma omp task
  parallel_binary_merge(A, mid, B, j, C);
  # pragma omp task
  parallel_binary_merge(A + mid + 1, nA - mid - 1, B + j, nB - j, C + mid + j + 1);

  // 7. Wait
  # pragma omp taskwait
}

// ============================================================
// TASK 3: 4-WAY MERGESORT
// ============================================================

void mergesort_4way(int *arr, int n) {
  if (n < SERIAL_THRESHOLD) {
    std::sort(arr, arr + n);
    return;
  }

  // 1. Calculate Splits
  int q = n / 4;
  int r = n % 4;
  int s1 = q, s2 = q, s3 = q, s4 = q + r;

  int *p1 = arr;
  int *p2 = p1 + s1;
  int *p3 = p2 + s2;
  int *p4 = p3 + s3;

  // TODO: Spawn 4 Parallel Tasks to sort p1, p2, p3, p4
  // Use #pragma omp task

  // --- TODO: YOUR CODE HERE ---
  # pragma omp task
  mergesort_4way(p1, s1);
  # pragma omp task
  mergesort_4way(p2, s2);
  # pragma omp task
  mergesort_4way(p3, s3);
  # pragma omp task
  mergesort_4way(p4, s4);
  # pragma omp taskwait

  // ----------------------

  // 2. Acquire Buffer
  std::vector<int> *temp_vec = pool.acquire_buffer(n);
  int *T = temp_vec->data();
  int *T_mid = T + (s1 + s2);

  // 3. Parallel Merge Phase
  // Merge (Q1+Q2) -> Left Half of T
  // Merge (Q3+Q4) -> Right Half of T
  // TODO: Launch in parallel tasks calling parallel_binary_merge

  // --- TODO: YOUR CODE HERE ---
  # pragma omp task
  parallel_binary_merge(p1, s1, p2, s2, T);
  # pragma omp task
  parallel_binary_merge(p3, s3, p4, s4, T_mid);
  # pragma omp taskwait
  // ----------------------

  // 4. Final Merge: Left+Right -> Original Array
  parallel_binary_merge(T, s1 + s2, T_mid, s3 + s4, arr);

  // 5. Cleanup
  pool.release_buffer(temp_vec);
}

// ============================================================
// COMMAND-LINE AND GRADESCOPE TESTS (DO NOT MODIFY)
// ============================================================
int main(int argc, char *argv[]) {
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