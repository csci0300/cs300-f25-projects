# defaults.py - Default parameters used by the testing scripts


#######################################################
#       Default parameters for correctness tests
#######################################################

# Number of times to repeat each fuzz test. Increasing this can help
# check for spurious issues or undefined behavior.
FUZZ_TEST_REPEATS = 1

# Use a tmpfs filesystem for correctness tests
CORRECTNESS_USE_TMPFS = True

#######################################################
#       Default parameters for performance tests
#######################################################

# Fail a performance test if it takes longer than this time
# (specified in seconds).  Use 0 to disable.
TIMEOUT_SEC = 0

# File size to use in performance tests
# Examples:  512K for a 512KB test file, 10M for a 10MB file.  Larger
# files will produce more accurate results, but will be slower.
# use "auto" to calibrate file size automatically.
# Note: if you are testing using a large size, consider setting a
# timeout of at least 60-120 seconds
PERFORMANCE_TEST_FILE_SIZE = "512K"

# True if performance tests should also check correctness
# Disabling this will reduce testing time, but may produce false
# positive results, since performance tests are not valid unless they
# also produce correct output!
PERFORMANCE_TEST_CHECKS_CORRECTNESS = True

# Target time for file size calibration (in seconds)
# The calibration phase will try increasing file sizes until a
# benchmark takes longer than this time
CALIBRATION_TIME = 0.05

# File size calibration mode.  Two possible values:
#  - max: pick a file size based on the fastest benchmark
#  - free: select a size for each benchmark separately
CALIBRATION_MODE = "max"

# Display a warning if stdio tests finish in less time than this
# value, specified in seconds.  This is used to warn if results may
# not be accurate.
WARN_TIME_THRESHOLD = 0.02

# Experimental:  use a tmpfs filesystem for performance tests
#
# WARNING: Enabling this option will speed up the performance tests,
# but may cause false positive results, especially for small file
# sizes.  Use with caution and be sure to verify results on the
# grading server.
PERFORMANCE_USE_TMPFS = False
