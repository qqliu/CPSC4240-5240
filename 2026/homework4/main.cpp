#include "kcore_pipeline.cuh"
#include <iostream>
#include <fstream>
#include <vector>
#include <string>

// Helper to load edges from a simple edge list file where each line has "u v"
parlay::sequence<Edge> load_edges(const std::string& filename, int& num_vertices) {
    std::ifstream infile(filename);
    if (!infile.is_open()) {
        std::cerr << "Failed to open " << filename << std::endl;
        exit(1);
    }

    int max_vertex = -1;
    std::vector<Edge> edges_vec;
    int u, v;
    while (infile >> u >> v) {
        edges_vec.push_back({u, v});
        if (u > max_vertex) max_vertex = u;
        if (v > max_vertex) max_vertex = v;
    }

    num_vertices = max_vertex + 1;
    return parlay::sequence<Edge>(edges_vec.begin(), edges_vec.end());
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <edge_list_file>\n";
        return 1;
    }

    std::string filename = argv[1];
    int num_vertices = 0;
    auto edges = load_edges(filename, num_vertices);

    // Build the CSR Graph using CPU (Task A)
    CSRGraph graph = build_csr_cpu(edges, num_vertices);

    // Compute K-Core on GPU (Task B)
    std::vector<int> coreness(num_vertices, 0);
    compute_kcore_gpu(graph, coreness.data());

    // Print all coreness values, one per line (parseable by test runner)
    for (int i = 0; i < num_vertices; i++) {
        std::cout << coreness[i] << "\n";
    }

    // Cleanup
    delete[] graph.row_offsets;
    delete[] graph.column_indices;

    return 0;
}
