#include "parlaylib/include/parlay/parallel.h"
#include "parlaylib/include/parlay/primitives.h"
#include "parlaylib/include/parlay/sequence.h"
#include "parlaylib/examples/mergesort.h"
#include <omp.h>
#include <random>

int main() {
    const size_t n = 100000000;
    const unsigned seed = 42;

    std::mt19937 gen(seed);
    std::uniform_int_distribution<int> dist(0, 100000000);

    // Parlay timing code
    parlay::internal::timer t("Time");

    // Use parlay sequence to create sequence of integers
    parlay::sequence<int> data(n);

    t.start();

    #pragma omp parallel for
    for (size_t i = 0; i < n; i++) {
        data[i] = dist(gen);
    }

    t.next("omp par_for");

    // Perform parallel merge sort
    merge_sort(data);
    t.next("mergesort time");

    std::cout << std::endl;
    return 0;
}

