/*
 * rtest102 - writec to position after EOF fills with null bytes
 */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "unit_tests.h"

#include "../io300.h"


int main() {
    test_init();

    char buf[9];
    struct io300_file* f = create_empty_file(TEST_FILE);

    io300_seek(f, 5);
    assert(io300_writec(f, 'Y') == 'Y');

    io300_seek(f, 0);
    assert(io300_read(f, buf, 6) == 6);
    assert(strncmp(buf, "\0\0\0\0\0Y", 6) == 0);

    io300_close(f);

    check_file_matches_string(TEST_FILE, "\0\0\0\0\0Y");
}
