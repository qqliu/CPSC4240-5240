#include <iostream>
#include <mutex>

class FineGrainedList {
private:
    struct Node {
        int value;
        Node* next;
        std::mutex m;

        Node(int val, Node* nxt = nullptr)
            : value(val), next(nxt) {}
    };

    Node* head; // Sentinel node

public:
    FineGrainedList() {
        head = new Node(-1); // sentinel node with dummy value
    }

    ~FineGrainedList() {
        Node* curr = head;
        while (curr) {
            Node* temp = curr;
            curr = curr->next;
            delete temp;
        }
    }

    // Insert 'val' in ascending order
    void insert(int val) {
        Node* pred = head;
        std::unique_lock<std::mutex> predLock(pred->m);

        Node* curr = pred->next;
        std::unique_lock<std::mutex> currLock;
        if (curr) {
            currLock = std::unique_lock<std::mutex>(curr->m);
        }

        // Traverse until we find the insertion position
        while (curr && curr->value < val) {
            // 1. Unlock the old predecessor
            predLock.unlock();

            // 2. Advance 'pred' to 'curr'
            pred = curr;

            // 3. Transfer lock ownership from 'currLock' to 'predLock'
            //    so we stay locked on 'pred' without relocking the same mutex.
            predLock = std::move(currLock);

            // 4. Move 'curr' forward and lock if it exists
            Node* next = pred->next;
            if (next) {
                currLock = std::unique_lock<std::mutex>(next->m);
            } else {
                // If next is null, 'currLock' is default-constructed (unowned).
                currLock = std::unique_lock<std::mutex>();
            }
            curr = next;
        }

        // Insert the new node between 'pred' and 'curr'
        Node* newNode = new Node(val, curr);
        pred->next = newNode;
        // Locks (predLock, currLock) are automatically released here by RAII
    }

    // Remove 'val' from the list, if it exists
    bool remove(int val) {
        Node* pred = head;
        std::unique_lock<std::mutex> predLock(pred->m);

        Node* curr = pred->next;
        std::unique_lock<std::mutex> currLock;
        if (curr) {
            currLock = std::unique_lock<std::mutex>(curr->m);
        }

        while (curr && curr->value < val) {
            predLock.unlock();
            pred = curr;
            predLock = std::move(currLock);

            Node* next = pred->next;
            if (next) {
                currLock = std::unique_lock<std::mutex>(next->m);
            } else {
                currLock = std::unique_lock<std::mutex>();
            }
            curr = next;
        }

        // If 'curr' is valid and matches 'val', remove it
        if (curr && curr->value == val) {
            pred->next = curr->next;

            // Manually unlock to safely delete 'curr'
            if (currLock.owns_lock()) {
                currLock.unlock();
            }
            if (predLock.owns_lock()) {
                predLock.unlock();
            }
            delete curr;

            return true;
        }
        return false;
    }

    // Check if 'val' exists in the list
    bool contains(int val) {
        Node* pred = head;
        std::unique_lock<std::mutex> predLock(pred->m);

        Node* curr = pred->next;
        std::unique_lock<std::mutex> currLock;
        if (curr) {
            currLock = std::unique_lock<std::mutex>(curr->m);
        }

        while (curr && curr->value < val) {
            predLock.unlock();
            pred = curr;
            predLock = std::move(currLock);

            Node* next = pred->next;
            if (next) {
                currLock = std::unique_lock<std::mutex>(next->m);
            } else {
                currLock = std::unique_lock<std::mutex>();
            }
            curr = next;
        }

        bool found = (curr && curr->value == val);
        // Locks release automatically at scope exit
        return found;
    }
};

// Example usage
int main() {
    FineGrainedList list;
    list.insert(10);
    list.insert(5);
    list.insert(20);

    std::cout << "Contains 10? "
              << (list.contains(10) ? "Yes" : "No") << std::endl;

    std::cout << "Removing 10... "
              << (list.remove(10) ? "Success" : "Fail") << std::endl;

    std::cout << "Contains 10? "
              << (list.contains(10) ? "Yes" : "No") << std::endl;

    return 0;
}

