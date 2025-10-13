/*
 * rtest100:  This test may look familiar....
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "unit_tests.h"

#include "../io300.h"
#include <assert.h>

int main() {
    test_init();

    char buffer[5];

    struct io300_file* f = create_file_from_string(TEST_FILE, "this is a test");

    assert(io300_read(f, buffer, 5) == 5);
    assert(io300_write(f, "aaa", 3) == 3);
    assert(io300_read(f, buffer, 2) == 2);
    io300_seek(f, 12);
    assert(io300_write(f, "aaa", 3) == 3);
    assert(io300_readc(f) == -1);
    io300_close(f);

    check_file_matches_string(TEST_FILE, "this aaaa teaaa");
}
