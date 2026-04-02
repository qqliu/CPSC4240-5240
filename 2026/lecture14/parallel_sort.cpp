#include "parlaylib/include/parlay/parallel.h"
#include "parlaylib/include/parlay/primitives.h"
#include "parlaylib/include/parlay/sequence.h"
#include "parlaylib/examples/mergesort.h"

int main() {
    // Use parlay sequence to create sequence of integers
    parlay::sequence<int> data = {5, 2, 9, 1, 5, 6};

    // Perform parallel merge sort
    merge_sort(data);

    for (int x : data) {
        std::cout << x << " ";
    }
    std::cout << std::endl;
    return 0;
}

