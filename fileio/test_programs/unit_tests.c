#include <fcntl.h>
#include <errno.h>
#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>


#include "../io300.h"

#include "unit_tests.h"

#define ENV_USING_TESTER "IO300_TEST_RUN"

/**
 * test_init - Test setup:  run before each test
 */
void test_init(void) {
    assert(CACHE_SIZE == 8);
    delete_if_exists(TEST_FILE);
    delete_if_exists(TEST_FILE_2);
    delete_if_exists(TEST_EXPECTED_FILE);
    delete_if_exists(TEST_OUTPUT);
    delete_if_exists(TEST_OUTPUT_2);
}

/**
 * prepare_empty_file:  Create an empty test file
 *
 * Arguments:
 *  - file_path:  path to the file
 *
 * Returns:  nothing
 */
void prepare_empty_file(char* file_path) {
    FILE* f = fopen(file_path, "w");
    fclose(f);
}

/**
 * prepare_file_from_bytes: Create a file containing the bytes
 * provided
 *
 * Arguments:
 *  - file_path:  path to the file
 *  - contents:  pointer to data that should go in the file
 *  - size:  number of bytes in contents
 *
 * Returns:  nothing
 */
void prepare_file_from_bytes(char* file_path, char* contents, size_t size) {
    FILE* f = fopen(file_path, "w");
    fwrite(contents, size, 1, f);
    fclose(f);
}


/**
 * prepare_file_from_string: Create a file from a null-terminated
 * string.  This is a shorthand version of prepare_file_from_bytes if
 * you're using a string.
 *
 * Arguments:
 *  - file_path:  path to the file
 *  - contents: string containing the data from the file, must be
 *    null-terminated like an ordinary "C-style string"
 *
 * Returns:  nothing
 */
void prepare_file_from_string(char* file_path, char* contents) {
    prepare_file_from_bytes(file_path, contents, strlen(contents));
}

/**
 * create_empty_file:  Make a test file and open it
 *
 * Arguments:
 *  - file_path:  path to the file
 *
 * Returns:  pointer to file, suitable for io300_* operations
 */
struct io300_file* create_empty_file(char* file_path) {
    prepare_empty_file(file_path);
    struct io300_file* f = io300_open(file_path, MODE_RDWR, file_path);
    if (!f) {
	fprintf(stderr, "Unable to create file %s\n", file_path);
	abort();
    }
    return f;
}

/**
 * create_file_from_bytes: Create a file containing the bytes
 * provided, then open it
 *
 * Arguments:
 *  - file_path:  path to the file
 *  - contents:  pointer to data that should go in the file
 *  - size:  number of bytes in contents
 *
 * Returns:  pointer to file, suitable for io300_* operations
 */
struct io300_file* create_file_from_bytes(char* file_path, char* contents,
                                          size_t size) {
    prepare_file_from_bytes(file_path, contents, size);
    struct io300_file* f = io300_open(file_path, MODE_RDWR, file_path);
    if (!f) {
	fprintf(stderr, "Unable to create file %s\n", file_path);
	abort();
    }
    return f;
}



/**
 * create_file_from_string: Create a file from a null-terminated
 * string, then open it.  This is a shorthand version of
 * create_file_from_bytes if you're using a string.
 *
 * Arguments:
 *  - file_path:  path to the file
 *  - contents: string containing the data from the file, must be
 *    null-terminated like an ordinary "C-style string"
 *
 * Returns:  pointer to file, suitable for io300_* operations
 */
struct io300_file* create_file_from_string(char* file_path, char* contents) {
    return create_file_from_bytes(file_path, contents, strlen(contents));
}


/**
 * check_file_matches_bytes: Check that a file contains the bytes
 * specified; abort the program if the file does not match.  You can
 * use this like you would an assert statement, except that it checks
 * files.
 *
 * Arguments:
 *  - file_path:  path to the file
 *  - expected_contents:  pointer to bytes expected to be in the file
 *  - size:  number of expected bytes
 *
 * Returns:  nothing, terminates program if error found
 */
void check_file_matches_bytes(char* file_path,
			      char* expected_contents, size_t sz) {
    prepare_file_from_bytes(TEST_EXPECTED_FILE, expected_contents, sz);

    char* actual = (char*)malloc(sz);
    memset(actual, 0, sz);

    int fd = open(file_path, O_RDONLY);
    if (fd < 0) {
	fprintf(stderr, "Unable to open test file %s:  %s\n", file_path, strerror(errno));
	exit(1);
    }

    char* ptr = actual;
    size_t bytes_read = 0;
    int b;
    while ((b = read(fd, ptr, sz - bytes_read)) > 0) {
	ptr += b;
	bytes_read += b;
    }

    int ok = 1;
    for (size_t i = 0; i < bytes_read; i++) {
	if (actual[i] != expected_contents[i]) {
	    fprintf(stderr, "File contents did not match, first incorrect byte at offset %zu:  expected 0x%02x, got 0x%02x (try hexdump for more info)\n",
		    i, expected_contents[i], actual[i]);
	    ok = 0;
	    break;
	}
    }

    if (bytes_read != sz) {
	fprintf(stderr, "Output file size is incorrect:  expected %zu bytes but was %zu\n", sz, bytes_read);
	ok = 0;
    }

    if(!getenv(ENV_USING_TESTER)) {
	fprintf(stderr, "Expected file:  %s\nActual file:  %s\n", TEST_EXPECTED_FILE, file_path);
    } else {
	fprintf(stderr, "Run test manually to check files involved\n");
    }

    free(actual);
    if (!ok) {
	abort();
    }
}

/**
 * check_file_matches_string: Check that a file contains the string
 * specified; abort the program if the file does not match.  This is a
 * shorthand version of check_file_matches_bytes, if you're working
 * with an ordinary string.  You can use this like you would an assert
 * statement, except that it checks files.
 *
 * Arguments:
 *  - file_path:  path to the file
 * - expected_contents: string expected to match file contents, must
 *   be a null-terminated string, like any ordinary "C-style string""
 *
 * Returns:  nothing, terminates program if error found
 */
void check_file_matches_string(char* file_path, char* expected_contents) {
    check_file_matches_bytes(file_path, expected_contents, strlen(expected_contents));
}

// Test setup helper:  if the file exists, delete it
// You should not need to use this
void delete_if_exists(const char* path) {
    if (access(path, F_OK) == 0) {
	if (unlink(path)) {
	    fprintf(stderr, "Unable to remove test file %s\n", path);
	    exit(1);
	}
    }
}
