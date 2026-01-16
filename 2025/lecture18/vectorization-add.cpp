#include <iostream>
#include <chrono>
#include <immintrin.h>
#include <cstdlib>
#include <random>

// Scalar addition: adds each element one by one
void scalar_add(const float* __restrict A, const float* __restrict B, float* __restrict C, size_t N) {
    for (size_t i = 0; i < N; ++i) {
        C[i] = A[i] + B[i];
    }
}

// Vector addition: AVX intrinsics over 16 floats per iteration
void vectorized_add_aligned_unrolled(const float* __restrict A,
                                       const float* __restrict B,
                                       float* __restrict C,
                                       size_t N) {
    size_t i = 0;
    for (; i + 15 < N; i += 16) {
        __m256 a1 = _mm256_load_ps(A + i);
        __m256 a2 = _mm256_load_ps(A + i + 8);
        __m256 b1 = _mm256_load_ps(B + i);
        __m256 b2 = _mm256_load_ps(B + i + 8);
        __m256 c1 = _mm256_add_ps(a1, b1);
        __m256 c2 = _mm256_add_ps(a2, b2);
        _mm256_store_ps(C + i, c1);
        _mm256_store_ps(C + i + 8, c2);
    }

    for (; i < N; i++) {
        C[i] = A[i] + B[i];
    }
}

int main() {
    const size_t N = 1000000000;
    float *A, *B, *C_scalar, *C_vectorized;

    if (posix_memalign(reinterpret_cast<void**>(&A), 32, N * sizeof(float)) != 0 ||
        posix_memalign(reinterpret_cast<void**>(&B), 32, N * sizeof(float)) != 0 ||
        posix_memalign(reinterpret_cast<void**>(&C_scalar), 32, N * sizeof(float)) != 0 ||
        posix_memalign(reinterpret_cast<void**>(&C_vectorized), 32, N * sizeof(float)) != 0) {
        std::cerr << "Memory allocation failed.\n";
        return 1;
    }

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<float> dis(0.0f, 1.0f);

    for (size_t i = 0; i < N; ++i) {
        A[i] = dis(gen);
        B[i] = dis(gen);
    }

    scalar_add(A, B, C_scalar, N);
    vectorized_add_aligned_unrolled(A, B, C_vectorized, N);

    auto start = std::chrono::steady_clock::now();
    scalar_add(A, B, C_scalar, N);
    auto end = std::chrono::steady_clock::now();
    std::chrono::duration<double> scalar_duration = end - start;
    std::cout << "Scalar addition took " << scalar_duration.count() << " seconds.\n";

    start = std::chrono::steady_clock::now();
    vectorized_add_aligned_unrolled(A, B, C_vectorized, N);
    end = std::chrono::steady_clock::now();
    std::chrono::duration<double> vectorized_duration = end - start;
    std::cout << "Optimized vectorized addition took " << vectorized_duration.count() << " seconds.\n";

    for (size_t i = 0; i < 10; ++i) {
        if (C_scalar[i] != C_vectorized[i]) {
            std::cerr << "Mismatch at index " << i << ": " << C_scalar[i] << " != " << C_vectorized[i] << "\n";
        }
    }

    return 0;
}

