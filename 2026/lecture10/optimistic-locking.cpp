#include <iostream>
#include <mutex>
#include <thread>
#include <vector>
#include <random>
#include <atomic>

// ------------------------------------------------------
// Optimistic (Lazy) Linked List with Marking
// ------------------------------------------------------
class MarkedList {
private:
    struct Node {
        int value;
        Node* next;
        mutable std::mutex m;  // Protects this node
        bool removed;          // 'true' if this node is logically removed

        Node(int val, Node* nxt = nullptr)
            : value(val), next(nxt), removed(false) {}
    };

    Node* head; // Sentinel node: never removed

    // Validate that 'pred->next == curr', and that both are not removed
    bool validate(Node* pred, Node* curr) {
        return (!pred->removed && ! (curr && curr->removed) && pred->next == curr);
    }

public:
    MarkedList() {
        // Sentinel with dummy value; never removed
        head = new Node(-1);
    }

    ~MarkedList() {
        // We do NOT fully reclaim “removed” nodes here.
        // For a real system, you'd add a safe reclamation scheme.
        Node* curr = head;
        while (curr) {
            Node* temp = curr;
            curr = curr->next;
            delete temp;
        }
    }

    // Insert 'val' in ascending order
    void insert(int val) {
        while (true) {
            Node* pred = head;
            Node* curr = pred->next;

            // (1) Traverse without locks
            while (curr && curr->value < val) {
                pred = curr;
                curr = curr->next;
            }

            // (2) Lock pred
            std::unique_lock<std::mutex> lockPred(pred->m);
            // (3) Lock curr if it's not null
            std::unique_lock<std::mutex> lockCurr;
            if (curr) {
                lockCurr = std::unique_lock<std::mutex>(curr->m);
            }

            // (4) Validate links and removed flags
            if (!validate(pred, curr)) {
                // If invalid, unlock & retry
                continue;
            }

            // Now we can safely insert if 'curr' is either null or has a value >= val
            Node* newNode = new Node(val, curr);
            pred->next = newNode;
            // locks unlock automatically at scope exit
            return;
        }
    }

    // Remove 'val' if it exists
    bool remove(int val) {
        while (true) {
            Node* pred = head;
            Node* curr = pred->next;

            // (1) Traverse without locks
            while (curr && curr->value < val) {
                pred = curr;
                curr = curr->next;
            }

            // (2) Lock pred
            std::unique_lock<std::mutex> lockPred(pred->m);
            // (3) Lock curr if not null
            std::unique_lock<std::mutex> lockCurr;
            if (curr) {
                lockCurr = std::unique_lock<std::mutex>(curr->m);
            }

            // (4) Validate
            if (!validate(pred, curr)) {
                continue;
            }

            // If 'curr' is null or doesn't match val, not found
            if (!curr || curr->value != val) {
                return false;
            }

            // (5) Logically remove by setting 'removed = true'
            curr->removed = true;

            // (6) Physically unlink from pred
            pred->next = curr->next;
            // 'curr' is not freed; it remains for potential safe reclamation
            return true;
        }
    }

    // Check if 'val' is in the list
    bool contains(int val) {
        while (true) {
            Node* pred = head;
            Node* curr = pred->next;
            // (1) Traverse (unlocked)
            while (curr && curr->value < val) {
                pred = curr;
                curr = curr->next;
            }

            // (2) Lock pred
            std::unique_lock<std::mutex> lockPred(pred->m);

            // (3) Lock curr if it exists
            std::unique_lock<std::mutex> lockCurr;
            if (curr) {
                lockCurr = std::unique_lock<std::mutex>(curr->m);
            }

            // (4) Validate again
            if (!validate(pred, curr)) {
                continue;
            }

            // Found if curr exists, not removed, and equals val
            return (curr && !curr->removed && curr->value == val);
        }
    }

    // Print the list contents in ascending order (not thread-safe if concurrent)
    void printList() {
        Node* curr = head->next;
        while (curr) {
            if (!curr->removed) {
                std::cout << curr->value << " ";
            }
            curr = curr->next;
        }
        std::cout << std::endl;
    }
};

// --------------------
// Multi-Threaded Test
// --------------------
int main() {
    MarkedList list;

    // We'll have multiple inserter and remover threads
    const int numInsertThreads = 4;
    const int numRemoveThreads = 4;
    const int opsPerThread = 1000;

    // A random seed
    auto seed = std::random_device{}();

    // Inserter function
    auto inserter = [&](int id) {
        std::mt19937 rng(seed + id);
        std::uniform_int_distribution<int> dist(0, 200);
        for (int i = 0; i < opsPerThread; ++i) {
            int val = dist(rng);
            list.insert(val);
        }
        std::cout << "[Inserter " << id << "] done.\n";
    };

    // Remover function
    auto remover = [&](int id) {
        std::mt19937 rng(seed + 100 + id);
        std::uniform_int_distribution<int> dist(0, 200);
        for (int i = 0; i < opsPerThread; ++i) {
            int val = dist(rng);
            list.remove(val);
        }
        std::cout << "[Remover " << id << "] done.\n";
    };

    // Create threads
    std::vector<std::thread> threads;
    threads.reserve(numInsertThreads + numRemoveThreads);

    // Launch inserter threads
    for (int i = 0; i < numInsertThreads; ++i) {
        threads.emplace_back(inserter, i);
    }
    // Launch remover threads
    for (int i = 0; i < numRemoveThreads; ++i) {
        threads.emplace_back(remover, i);
    }

    // Join all
    for (auto &t : threads) {
        t.join();
    }

    // Print final list contents
    std::cout << "Final list contents (unmarked nodes):\n";
    list.printList();

    int checkVal = 50;
    std::cout << "Contains " << checkVal << "? "
              << (list.contains(checkVal) ? "Yes" : "No") << std::endl;

    return 0;
}

