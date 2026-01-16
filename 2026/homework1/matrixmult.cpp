/*******************************************************
 * matrixmult.cpp
 *
 * Multiplies two square matrices of size n x n.
 *******************************************************/

#include <iostream>
#include <vector>

#include <omp.h>

#include "parlaylib/include/parlay/primitives.h"
#include "parlaylib/include/parlay/parallel.h"
#include "parlaylib/include/parlay/sequence.h"
#include "parlaylib/include/parlay/utilities.h"

int main() {
    int n;
    std::cin >> n;

    // Create matrices A, B, and C (all n x n)
    std::vector<std::vector<int>> A(n, std::vector<int>(n));
    std::vector<std::vector<int>> B(n, std::vector<int>(n));
    std::vector<std::vector<int>> C(n, std::vector<int>(n, 0));
    std::vector<std::vector<int>> D(n, std::vector<int>(n));
    std::vector<std::vector<int>> E(n, std::vector<int>(n));
    std::vector<std::vector<int>> F(n, std::vector<int>(n, 0));

    // Read matrix A
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cin >> A[i][j];
        }
    }

    // Read matrix B
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cin >> B[i][j];
        }
    }

    // Read matrix D
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cin >> D[i][j];
        }
    }

    // Read matrix E
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cin >> E[i][j];
        }
    }

    // TODO (OpenMP): perform matrix multiplication A x B and write into C: C = A x B
    // YOUR OpenMP CODE HERE

    std::cout << "The resulting matrix C = A x B is:\n";
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cout << C[i][j] << " ";
        }
        std::cout << "\n";
    }

    // TODO (ParlayLib): perform matrix multiplication D x E and write into F: F = D x E
    // YOUR ParlayLib CODE HERE

    std::cout << "The resulting matrix F = D x E is:\n";
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cout << F[i][j] << " ";
        }
        std::cout << "\n";
    }

    return 0;
}
