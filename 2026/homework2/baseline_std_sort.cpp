// Baseline: measures std::sort time for comparison with parallel mergesort.
// Usage: ./baseline_std_sort <N> <seed>
// Output: BASELINE,<time_seconds>

#include <chrono>
#include <iostream>
#include <random>
#include <vector>

int main(int argc, char *argv[]) {
  if (argc < 3) {
    std::cerr << "Usage: " << argv[0] << " <N> <seed>\n";
    return 1;
  }

  int N = std::stoi(argv[1]);
  unsigned int seed = std::stoul(argv[2]);

  std::vector<int> data(N);
  std::mt19937 rng(seed);
  for (int i = 0; i < N; ++i) {
    data[i] = rng();
  }

  auto start = std::chrono::high_resolution_clock::now();
  std::sort(data.begin(), data.end());
  auto end = std::chrono::high_resolution_clock::now();

  double elapsed = std::chrono::duration<double>(end - start).count();
  std::cout << "BASELINE," << elapsed << "\n";
  return 0;
}
