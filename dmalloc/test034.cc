#include "dmalloc.hh"
#include <cstdio>
#include <cassert>
#include <cstring>
// Diabolical wild free #2.

int main() {
    char* a = (char*) malloc(200);
    char* b = (char*) malloc(50);
    char* c = (char*) malloc(200);
    char* p = (char*) malloc(3000);
    (void) a, (void) c;

    // Save a copy of data around b, starting from 200 bytes before the allocation
    memcpy(p, b - 200, 450);

    // Free b (should work normally)
    free(b);

    // Restore the saved copy of the data back to where it was
    // (Why is this diabolical???)
    memcpy(b - 200, p, 450);

    // Try to free b again; should be a double-free error!
    free(b);

    print_statistics();
}

//! MEMORY BUG???: ??? free of pointer ???
//! ???
