/*******************************************************
 * matrixmult.cpp
 *
 * Multiplies two square matrices of size n x n.
 *******************************************************/

#include <iostream>
#include <vector>
#include <chrono>
#include <omp.h>

#include "parlaylib/include/parlay/primitives.h"
#include "parlaylib/include/parlay/parallel.h"
#include "parlaylib/include/parlay/sequence.h"
#include "parlaylib/include/parlay/utilities.h"

using namespace std;

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

    auto startC = chrono::high_resolution_clock::now();
    // TODO (OpenMP): perform matrix multiplication A x B and write into C: C = A x B
    // YOUR OpenMP CODE HERE
    auto endC = chrono::high_resolution_clock::now();
    chrono::duration<double> elapsedC = endC - startC;

    std::cout << "The resulting matrix C = A x B is:\n";
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cout << C[i][j] << " ";
        }
        std::cout << "\n";
    }

    auto startF = chrono::high_resolution_clock::now();
    // TODO (ParlayLib): perform matrix multiplication D x E and write into F: F = D x E
    // YOUR ParlayLib CODE HERE
    auto endF = chrono::high_resolution_clock::now();
    chrono::duration<double> elapsedF = endF - startF;

    std::cout << "The resulting matrix F = D x E is:\n";
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cout << F[i][j] << " ";
        }
        std::cout << "\n";
    }

    cout << "TIME_C:" << elapsedC.count() << endl;
    cout << "TIME_F:" << elapsedF.count() << endl;

    return 0;
}
