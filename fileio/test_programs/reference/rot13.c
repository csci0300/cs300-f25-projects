/*
 * rot13.c - Reference program for rot13
 *
 * This program computes the rot13-encoded version of a file, but does
 * not use our io300 library.
 *
 * Our testing scripts use this problem to compute the expected output
 * when running rot13.  You can use it to help create example
 * files to check your own implementation, or feel free to ignore it.
 *
 * To run this program to check your own output, you can run:
 *   test_programs/reference/rot13 <infile> <outfile>
 * and then compare <outfile> to a file produced by running ./rot13
 * on the same file, and with the same parameters.
 *
 * A block size may be optionally specified, e.g.,:
 *   test_programs/example/rot13 <block_size> <infile> <outfile>
 */

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>

#define DEFAULT_BLOCK_SIZE 8192

unsigned char rot13(unsigned char const ch) {
    if (ch >= 'A' && ch <= 'Z') {
        return 'A' + (((ch - 'A') + 13) % 26);
    }
    if (ch >= 'a' && ch <= 'z') {
        return 'a' + (((ch - 'a') + 13) % 26);
    }
    return ch;
}


off_t get_file_size(int fd) {
    struct stat s;
    int const r = fstat(fd, &s);
    if (r >= 0 && S_ISREG(s.st_mode)) {
        return s.st_size;
    } else {
	perror("Unable to get filesize");
	exit(1);
    }
}


int main(int argc, char* argv[]) {
    char* infile;

    if (argc == 2) {
	infile = argv[1];
    } else {
	fprintf(stderr, "Usage:  %s <infile>\n", argv[0]);
	exit(1);
    }

    FILE* f = fopen(infile, "r+");
    if (!f) {
	fprintf(stderr, "Unable to open file:  %s\n", strerror(errno));
	exit(1);
    }

    off_t file_size = get_file_size(fileno(f));
    if (file_size == -1) {
	fprintf(stderr, "Could not compute filesize:  %s\n", strerror(errno));
	fclose(f);
	exit(1);
    }

    int rv = 0;

    for (int i = 0; i < file_size; i++) {
	if (fseek(f, i, SEEK_SET) == -1) {
            fprintf(stderr, "error: seek should not fail.\n");
	    rv = 1;
	    break;
        }
        int c = fgetc(f);
        if (c == -1) {
            fprintf(stderr, "error: read should not fail.\n");
	    rv = 1;
	    break;
        }
        if (fseek(f, i, SEEK_SET) == -1) {
            fprintf(stderr, "error: seek should not fail.\n");
	    rv = 1;
	    break;
        }

	int c_rotated = rot13(c);
        if (fputc(c_rotated, f) == -1) {
            fprintf(stderr, "error: write should not fail.\n");
	    rv = 1;
	    break;
        }
    }

    fclose(f);
    return rv;
}
