#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "../io300.h"

/*
 *  student.c - Your implementation
 */

#ifndef CACHE_SIZE
#define CACHE_SIZE 8
#endif

#if (CACHE_SIZE < 4)
#error "internal cache size should not be below 4."
#error "if you changed this during testing, that is fine."
#error "when handing in, make sure it is reset to the provided value"
#error "if this is not done, the autograder will not run"
#endif

// Prototypes for helper functions defined later
int fetch(struct io300_file* const f);
int flush(struct io300_file* const f);

/*
 * This macro enables/disables the dbg() function. Use it to silence your
 * debugging info.
 * Use the dbg() function instead of printf debugging if you don't want to
 * hunt down 30 printfs when you want to hand in
 */
#define DEBUG_PRINT 0
#define DEBUG_STATISTICS 1

struct io300_file {
    /* read,write,seek all take a file descriptor as a parameter */
    int fd;
    /* this will serve as our cache */
    char* cache;

    // TODO: Your properties go here!


    /* Used for debugging, keep track of which io300_file is which */
    char* description;
    /* To tell if we are getting the performance we are expecting */
    struct io300_statistics {
        int read_calls;
        int write_calls;
        int seeks;
    } stats;
};

/*
 *  Assert the properties that you would like your file to have at all times.
 *  Call this function frequently (like at the beginning of each function) to
 *   catch logical errors early on in development.
 */
static void check_invariants(struct io300_file* f) {
    assert(f != NULL);
    assert(f->cache != NULL);
    assert(f->fd >= 0);

    // TODO: Add more invariants
}

/*
 *  Wrapper around printf that provides information about the
 *  given file. You can turn off messages printed by this function
 *  by changing the DEBUG_PRINT macro above.
 */
static void dbg(struct io300_file* f, char* fmt, ...) {
    (void)f;
    (void)fmt;
#if (DEBUG_PRINT == 1)
    static char buff[300];
    size_t const size = sizeof(buff);
    int n = snprintf(buff, size,
                     // TODO: Add the fields you want to print when debugging
                     "{desc:%s, } -- ", f->description);
    int const bytes_left = size - n;
    va_list args;
    va_start(args, fmt);
    vsnprintf(&buff[n], bytes_left, fmt, args);
    va_end(args);
    printf("%s", buff);
#endif
}

struct io300_file* io300_open(const char* const path, int mode, char* description) {
    if (path == NULL) {
        fprintf(stderr, "error: null file path\n");
        return NULL;
    }

    // Set flags for how file is created [DO NOT CHANGE THIS]
    int flags = O_CREAT | O_SYNC;
    switch(mode) {
    case MODE_READ:
	flags |= O_RDONLY;
	break;
    case MODE_WRITE:
	flags |= O_RDWR | O_TRUNC;
	break;
    case (MODE_READ|MODE_WRITE):
	flags |= O_RDWR;
	break;
    default:
	fprintf(stderr, "error: invalid file mode %02x\n", mode);
	return NULL;
    }

    int const fd = open(path, flags, S_IRUSR | S_IWUSR); // DO NOT CHANGE THIS LINE
    if (fd == -1) {
        fprintf(stderr, "error: could not open file: `%s`: %s\n", path,
                strerror(errno));
        return NULL;
    }

    struct io300_file* const ret = malloc(sizeof(*ret));
    if (ret == NULL) {
        fprintf(stderr, "error: could not allocate io300_file\n");
        close(fd);
        return NULL;
    }

    ret->fd = fd;
    ret->cache = malloc(CACHE_SIZE);
    if (ret->cache == NULL) {
        fprintf(stderr, "error: could not allocate file cache\n");
        close(ret->fd);
        free(ret);
        return NULL;
    }
    // Initialize debugging info
    ret->description = description;
    ret->stats.read_calls = 0;
    ret->stats.write_calls = 0;
    ret->stats.seeks = 0;

    // TODO: Initialize your metadata!

    check_invariants(ret);
    dbg(ret, "Just finished initializing file from path: %s\n", path);
    return ret;
}



int io300_seek(struct io300_file* const f, off_t const pos) {
    check_invariants(f);
    f->stats.seeks++;

    // TODO: Implement!
    return lseek(f->fd, pos, SEEK_SET);
}

int io300_close(struct io300_file* const f) {
    check_invariants(f);

#if (DEBUG_STATISTICS == 1)
    printf("stats: {desc: %s, read_calls: %d, write_calls: %d, seeks: %d}\n",
           f->description, f->stats.read_calls, f->stats.write_calls,
           f->stats.seeks);
#endif

    // TODO: Implement!

    close(f->fd);
    free(f->cache);
    free(f);
    return 0;
}

/*
 * io300_filesize: Get the size of a file This function is part of the
 * io300 library: some tests will use it to get the file's current
 * size.  You may also use it as a helper for your implementation, or
 * modify it to better fit your design, but this is not required.
 *
 * WARNING:  this function makes a system call (fstat)!
 */
off_t io300_filesize(struct io300_file* const f) {
    check_invariants(f);
    struct stat s;
    int const r = fstat(f->fd, &s);   // system call!
    if (r >= 0 && S_ISREG(s.st_mode)) {
        return s.st_size;
    } else {
        return -1;
    }
}

int io300_readc(struct io300_file* const f) {
    check_invariants(f);

    // TODO: Implement!
    unsigned char c;
    if (read(f->fd, &c, 1) == 1) {
        return c;
    } else {
        return -1;
    }
}
int io300_writec(struct io300_file* f, int ch) {
    check_invariants(f);
    // TODO: Implement!
    unsigned char const c = (unsigned char)ch;
    if (write(f->fd, &c, 1) == 1) {
        return c;
    } else {
        return -1;
    }
}

ssize_t io300_read(struct io300_file* const f, char* const buff,
                   size_t const sz) {
    check_invariants(f);

    // TODO: Implement!
    return read(f->fd, buff, sz);
}
ssize_t io300_write(struct io300_file* const f, const char* buff,
                    size_t const sz) {
    check_invariants(f);

    // TODO: Implement!
    return write(f->fd, buff, sz);
}


int fetch(struct io300_file* const f) {
    check_invariants(f);
    /*
    * This (optional) helper should contain the logic for fetching
    * data from the file into the cache.  Think about how you can use
    * this helper to factor out some of the common logic in your read,
    * write, and seek functions!
    *
    * Feel free to add arguments if needed, but if you do, be sure to
    * modify the function prototype (at the top of the file) to match!
    */

    // TODO: Implement this

    return 0;
}

int flush(struct io300_file* const f) {
    check_invariants(f);
    /*
     * This helper should flush data in the cache to the file, if any
     * changes have been made.Think about how you can use this helper
     * to factor out some of the common logic in your read, write, and
     * seek functions!
     *
     * Feel free to add arguments if needed, but if you do, be sure to
     * modify the function prototype (at the top of the file) to match!
     */

    // TODO: Implement this

    return 0;
}
