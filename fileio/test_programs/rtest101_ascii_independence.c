/*
 * rtest101 - Make sure files can contain non-ASCII characters and null bytes
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "unit_tests.h"

#include "../io300.h"
#include <assert.h>

char* expected_string = "Make\x00sure\x00your\x00approach\x00can\x00handle\x00null\x00bytes! "
    "가정하는 것은 안전하지 않습니다 प्रत्येकं पात्रं इति 'n ASCII-karakter.";

int main() {
    test_init();

    prepare_file_from_string(TEST_FILE, expected_string);

    struct io300_file* in = io300_open(TEST_FILE, MODE_READ, "in");
    struct io300_file* out = io300_open(TEST_FILE_2, MODE_WRITE, "out");

    char buffer[20];

    // Block cat logic
    while (1) {
        ssize_t r = io300_read(in, buffer, 17);
        if (r == 0 || r == -1) {
            break;
        }

        if (io300_write(out, buffer, r) == -1) {
            fprintf(stderr, "error: all writes should succeed\n");
            assert(0);
        }
    }

    io300_close(in);
    io300_close(out);

    check_file_matches_string(TEST_FILE_2, expected_string);
    return 0;
}
