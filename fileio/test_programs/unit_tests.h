#ifndef __UNIT_TESTS_H__
#include <fcntl.h>
#include <errno.h>
#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>


#include "../io300.h"

#ifndef CACHE_SIZE
#define CACHE_SIZE 8
#endif

#if (CACHE_SIZE != 8)
#error "Error:  Unit tests require compilation with -DCACHE_SIZE=8"
#endif

#define TEST_FILE "/tmp/testfile"
#define TEST_FILE_2 "/tmp/testfile2"
#define TEST_OUTPUT "/tmp/outfile"
#define TEST_OUTPUT_2 "/tmp/outfile2"
#define TEST_EXPECTED_FILE "/tmp/expected"

#define TEST_INPUT TEST_FILE

// See unit_tests.c for descriptions
void test_init(void);

void make_input_file(const char* contents, size_t size, char* file_path);
void make_input_file_str(const char* contents, char* file_path);


struct io300_file* create_file_from_bytes(char* file_path, char* contents,
                                          size_t size);
struct io300_file* create_file_from_string(char* file_path, char* contents);

void prepare_file_from_bytes(char* file_path, char* contents, size_t size);
void prepare_file_from_string(char* file_path, char* contents);

void prepare_empty_file(char* file_path);
struct io300_file* create_empty_file(char* file_path);


void check_file_matches_bytes(char* file_path, char* expected_contents, size_t sz);
void check_file_matches_string(char* file_path, char* expected_contents);


void delete_if_exists(const char* path);

#endif
