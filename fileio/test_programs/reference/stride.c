/*
 * stride.c - Reference program for stride_cat
 * This is a program that performs the same operations as stride_cat.c,
 * but does not use our io300 library.
 *
 * Our testing scripts use this problem to compute the expected output
 * when running stride_cat.  You can use it to help create example
 * files to check your own implementation, or feel free to ignore it.
 *
 * To run this program to check your stride_cat output, you can run:
 * test_programs/reference/stride <block_size> <stride> <infile> <outfile>
 * (just like normal stride_cat).  Example:
 *  test_programs/example/stride 1 1024 <infile> <outfile>
 * ... and then compare <outfile> to a file produced by running your ./stride_cat
 * on the same file, and with the same parameters.
 */

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <unistd.h>
#include <sys/stat.h>


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
    size_t block_size;
    size_t stride;
    char* infile;
    char* outfile;

    if (argc == 5) {
	block_size = atoi(argv[1]);
	stride = atoi(argv[2]);
	infile = argv[3];
	outfile = argv[4];
    } else {
	fprintf(stderr, "Usage:  %s <block size> <stride> <infile> <outflie>\n", argv[0]);
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

    size_t file_size = (size_t)get_file_size(ifd);
    char* buffer = (char*) malloc(block_size);
    if (!buffer) {
	fprintf(stderr, "Could not allocate memory");
	exit(1);
    }

    int rv = 0;

    // Copy file data
    size_t pos = 0, written = 0;
    while (written < file_size) {
        // Copy a block
        ssize_t amount = read(ifd, buffer, block_size);
        if (amount <= 0) {
            break;
        }
        if (write(ofd, buffer, amount) <= 0) {
	    fprintf(stderr, "write failed:  %s\n", strerror(errno));
	    rv = 1;
	    break;
	}
        written += amount;

        // Move `inf` file position to next stride
        pos += stride;
        if (pos >= file_size) {
            pos = (pos % stride) + block_size;
            if (pos + block_size > stride) {
                block_size = stride - pos;
            }
        }
        if (lseek(ifd, pos, SEEK_SET) == -1) {
            fprintf(stderr, "error: seek should not fail\n");
	    rv = 1;
	    break;
        }
    }

    free(buffer);
    close(ifd);
    close(ofd);

    return rv;
}
