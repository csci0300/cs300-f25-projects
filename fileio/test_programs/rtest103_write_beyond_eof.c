/*
 * rtest103 - Write very far after EOF
 */
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <string.h>
#include <unistd.h>

#include "unit_tests.h"

#include "../io300.h"

int main() {
    test_init();
    struct io300_file* f = create_empty_file(TEST_FILE);

    // Skip first 100 bytes
    io300_seek(f, 100);

    // Write 10 bytes
    char buffer[10];
    memset(buffer, 'a', 10);
    assert(io300_write(f, buffer, 10) == 10);
    io300_close(f);

    // Expected file should be <100 null bytes> + 10 a's
    char expected[110];
    memset(expected, 0, 110);
    memset(expected + 100, 'a', 10);

    check_file_matches_bytes(TEST_FILE, expected, 110);
}
