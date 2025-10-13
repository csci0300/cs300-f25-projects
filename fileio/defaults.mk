# This file specifies default parameters for the testing script

# SEED: Random seed for fuzz tests
# Default:  -1 (pick randomly)
# To set the seed for one test, run with:
#   make check SEED=1234
SEED ?= -1

# TRIALS:  Number of trials to use for each fuzz test
# Default: 1 (set in test_scripts/defaults.py)
# To set the number of trials for one test, run with:
#  make check TRIALS=5
TRIALS ?= 1

# TIMEOUT: Timeout for performance tests (in seconds)
# Default:  (see test_scripts/defaults.py)
# To set the timeout for one test, run with:
#   make check TIMEOUT=60
TIMEOUT ?= -1

# FILESIZE: File size for performance tests
# Default:  (see test_scripts/defaults.py)
# To set the test file size for one test, run with:
#   make check FILESIZE=1M
# (For large file sizes, you should also set a timeout)
FILESIZE ?= -1

# Location to write JSON test results (needed by grading server)
# Default:  -1 (do not use JSON format)
JSON ?= -1

# TMPFS:  Create test files in tmpfs filesystem
# see test_scripts/defaults.py for details
# Default:  enabled for correctness tests only
# To enable, run with:
#   make check TMPFS=1
TMPFS ?= -1

# TMPFS_CHECK:  Enable tmpfs filesystem for correctness tests
# see test_scripts/defaults.py for details
TMPFS_CHECK ?= -1

# TMPFS_PERF:  Enable tmpfs filesystem for performance tests
# see test_scripts/defaults.py for details
# To enable, run with:
#   make check TMPFS_PERF=1
TMPFS_PERF ?= -1

ifneq ($(SEED), -1)
	TESTFLAGS += --seed=$(SEED)
endif
ifneq ($(TIMEOUT), -1)
	TESTFLAGS += --timeout=$(TIMEOUT)
endif
ifneq ($(FILESIZE),-1)
	TESTFLAGS += --perf-file-size=$(FILESIZE)
endif
ifneq ($(JSON),-1)
	TESTFLAGS += --json=$(JSON)
endif

ifeq ($(TMPFS),1)
	TMPFS_CHECK = 1
	TMPFS_PERF = 1
endif
ifeq ($(TMPFS),0)
	TMPFS_CHECK = 0
	TMPFS_PERF = 0
endif

ifeq ($(TMPFS_CHECK),1)
	TESTFLAGS += --corr-use-tmpfs
endif
ifeq ($(TMPFS_CHECK),0)
	TESTFLAGS += --corr-no-tmpfs
endif

ifeq ($(TMPFS_PERF),1)
	TESTFLAGS += --perf-use-tmpfs
endif
ifeq ($(TMPFS_PERF),0)
	TESTFLAGS += --perf-no-tmpfs
endif


ifneq ($(TRIALS),1)
	TESTFLAGS += --fuzz-repeat=$(TRIALS)
endif
