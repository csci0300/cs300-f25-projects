/*
 * reverse.c - Reference program for reverse_*_cat
 *
 * This program reverses the bytes of a file like the
 * reverse_{byte,block}_cat tests, but does not use our io300 library.
 *
 * Our testing scripts use this problem to compute the expected output
 * when running these tests.  You can use it to help create example
 * files to check your own implementation, or feel free to ignore it.
 *
 * To run this program to check your own output, you can run:
 *   test_programs/reference/reverse <infile> <outfile>
 * and then compare <outfile> to a file produced by running a reverse_*_cat
 * on the same file, and with the same parameters.
 *
 * A block size may be optionally specified, e.g.,:
 *   test_programs/example/reverse <block_size> <infile> <outfile>
 */

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>

#define DEFAULT_BLOCK_SIZE 8192

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
    size_t buffer_size;
    char* infile;
    char* outfile;

    if (argc == 3) {
	buffer_size = DEFAULT_BLOCK_SIZE;
	infile = argv[1];
	outfile = argv[2];
    } else if (argc == 4) {
	buffer_size = atoi(argv[1]);
	infile = argv[2];
	outfile = argv[3];
    } else {
	fprintf(stderr, "Usage:  %s [block size] <infile> <outflie>\n", argv[0]);
	exit(1);
    }

    int ifd = open(infile, O_RDONLY, 0);
    if (ifd < 0) {
	perror("open infile");
	exit(1);
    }

    int ofd = open(outfile, O_CREAT | O_WRONLY | O_TRUNC, S_IRUSR | S_IWUSR);
    if (ofd < 0) {
	perror("open outfile");
	exit(1);
    }

    off_t file_size = get_file_size(ifd);
    char* in_buffer = (char*) malloc(buffer_size);
    if (!in_buffer) {
	fprintf(stderr, "Could not allocate memory");
	exit(1);
    }
    char* out_buffer = (char*) malloc(buffer_size);
    if (!out_buffer) {
	fprintf(stderr, "Could not allocate memory");
	exit(1);
    }

    int rv = 0;

    for (int i = file_size - (file_size % buffer_size); i >= 0;
         i -= buffer_size) {
        if (lseek(ifd, i, SEEK_SET) == -1) {
            perror("lseek");
            rv = 1;
            break;
        }
        int const n = read(ifd, in_buffer, buffer_size);
        if (n == -1) {
            break;
        }
        for (int j = 0; j < n; j++) {
            out_buffer[j] = in_buffer[(n - 1) - j];
        }

        if (write(ofd, out_buffer, n) == -1) {
	    perror("write");
            rv = 1;
            break;
        }
    }

    free(in_buffer);
    free(out_buffer);
    close(ifd);
    close(ofd);

    return rv;
}
