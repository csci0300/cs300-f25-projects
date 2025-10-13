/*
 * rtest001.c - basic readc 1
 */
#include <stdio.h>
#include <stdlib.h>

#include "../io300.h"
#include "unit_tests.h"


int main() {
    test_init();

    // *** For this and all unit tests, assume CACHE_SIZE == 8 ***
    assert(CACHE_SIZE == 8);

    // Create and open a test file containing the string "hello world"
    struct io300_file* f = create_file_from_string(TEST_FILE, "hello world");

    // Do some readc operations
    char c1 = io300_readc(f);
    char c2 = io300_readc(f);
    char c3 = io300_readc(f);

    // Make sure the results from readc are what we expect
    assert(c1 == 'h');
    assert(c2 == 'e');
    assert(c3 == 'l');

    // Close the file
    io300_close(f);

    // Make sure the input file wasn't modified
    // (In tests using write/writec, you can use this to assert that the file contains specific data)
    check_file_matches_string(TEST_FILE, "hello world");

    return 0;
}
