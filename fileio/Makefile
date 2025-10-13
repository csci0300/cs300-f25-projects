# CC stands for C Compiler.
CC           := gcc

# Should sanitizers be enabled? Default is 1.
# Options are 0 or 1.
# You should run with SAN=0 when you are running under gdb or strace.
#
# To choose one, you can edit the variable below, or specify its value on the
# command line.
#    $ make check -B SAN=0
#
SAN ?= 1
ifeq ($(SAN),1)
SANS_ENABLED ?= -fsanitize=address -fsanitize=undefined
endif

# Flags to be passed to the C compiler.
# -ggdb3 says to embed as much debugging information as possible
# -Wall -Wextra says to enable all standard, and some extra warnings
# -Wshadow explicitly makes shadowing a local variable a warning
# -Werror changes all warnings to compilation errors
# -std=gnu11 says which version of the C language our source program is written in
# -fsigned-char specifies that `char`s are signed by default
CFLAGS       += -ggdb3 -Wall -Wextra -Wshadow -Werror -std=gnu11 -fsigned-char $(SANS_ENABLED)

# Get all of the test filenames
UNIT_TESTS = $(patsubst test_programs/%.c,%,$(sort $(wildcard test_programs/rtest[0-9][0-9][0-9]*.c)))

# These programs use your IO library. We will run them to make sure your code is
# working correctly
TEST_PROGRAMS := io300_test byte_cat diabolical_byte_cat reverse_byte_cat block_cat reverse_block_cat random_block_cat stride_cat rot13

REFERENCE_DIR := test_programs/reference
REFERENCE_PROGRAMS := $(patsubst $(REFERENCE_DIR)/%.c,$(REFERENCE_DIR)/%,$(wildcard $(REFERENCE_DIR)/*.c))

BINS := $(TEST_PROGRAMS) $(UNIT_TESTS) $(REFERENCE_PROGRAMS)

# Which implementation of io300_file do we want to use with our test programs?
# Options are student | naive | stdio
#
# To choose one, you can edit the variable below, or specify its value on the
# command line.
#    $ make -B IMPL=stdio
#
IMPL ?= student

IMPL_FLAGS_STDIO := -Dfputs=DO_NOT_USE_STDIO_fputs -Dfgets=DO_NOT_USE_STDIO_fgets

ifeq ($(IMPL), student)
	IMPL_FLAGS = -Dfread=DO_NOT_USE_STDIO_fread -Dfwrite=DO_NOT_USE_STDIO_fwrite -Dfputc=DO_NOT_USE_STDIO_fputc -Dfgetc=DO_NOT_USE_STDIO_fgetc
	IMPL_FLAGS = $(IMPL_FLAGS_STDIO)
endif

all: $(BINS) impl.o impl-c8.o

impl.o: impl/$(IMPL).c
	$(CC) $(CFLAGS) $(IMPL_FLAGS) $^ -c -o $@

impl-c8.o: impl/$(IMPL).c
	$(CC) $(CFLAGS) -UCACHE_SIZE -DCACHE_SIZE=8 $(IMPL_FLAGS) $^ -c -o $@

unit_tests.o: test_programs/unit_tests.c
	$(CC) $(CFLAGS) -UCACHE_SIZE -DCACHE_SIZE=8 $(IMPL_FLAGS) $^ -c -o $@

test_helpers.o: test_programs/test_helpers.c
	$(CC) $(CFLAGS) $(IMPL_FLAGS) $^ -c -o $@

$(UNIT_TESTS): %: test_programs/%.c impl-c8.o test_helpers.o unit_tests.o
	$(CC) $(CFLAGS) -UCACHE_SIZE -DCACHE_SIZE=8 $^ -o $@

$(TEST_PROGRAMS): %: test_programs/%.c impl.o test_helpers.o
	$(CC) $(CFLAGS) $^ -o $@

$(REFERENCE_PROGRAMS): %: %.c
	$(CC) $(CFLAGS) $^ -o $@

TESTFLAGS ?=

# Load test configuration options
# Take a look at defaults.mk to see what options are available
include defaults.mk


check: $(BINS)
	./test_scripts/run_tests.py $(TESTFLAGS) correctness

check-fuzz: $(BINS)
	./test_scripts/run_tests.py $(TESTFLAGS) fuzz

check-e2e: $(BINS)
	./test_scripts/run_tests.py $(TESTFLAGS) e2e

check-regression: $(BINS)
	./test_scripts/run_tests.py $(TESTFLAGS) regression

check-unit: check-fuzz

perf:
	./test_scripts/run_tests.py $(TESTFLAGS) perf

check-all: $(BINS)
	./test_scripts/run_tests.py $(TESTFLAGS) all

clean:
	rm -f -- $(BINS) *.o

validate-regression:
	$(MAKE) clean
	$(MAKE) IMPL=stdio check-regression
	$(MAKE) clean

check_testdata:
	dd if=/dev/urandom of=/tmp/check_testdata bs=4096 count=20
	@echo "80 KiB test file generated in /tmp/check_testdata"

perf_testdata:
	dd if=/dev/urandom of=/tmp/perf_testdata bs=1M count=1
	@echo "1 MiB test file generated in /tmp/perf_testdata"

tmpfs-cleanup:
	@sudo umount /tmp/io300
	@echo Done

.PHONY: all clean perf check check_testdata perf_testdata validate-regression tmpfs-cleanup
