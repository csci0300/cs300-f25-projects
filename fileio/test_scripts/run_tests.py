#!/usr/bin/env python3

import re
import os
import sys
import json
import argparse
import tempfile
import subprocess

from dataclasses import dataclass, field

import correctness_test
import performance_test

from performance_test import CALIBRATION_MODES, CALIBRATION_MODE_FREE, CALIBRATION_MODE_MAX

from util import TestResults
import defaults

def main(input_args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", help="random seed for fuzz tests",
                        type=int, default=-1)
    parser.add_argument("--grader", action="store_true")
    parser.add_argument("--timeout", type=int, default=0)
    parser.add_argument("--json", type=str, default=None)
    parser.add_argument("--fuzz-repeat", type=int, default=defaults.FUZZ_TEST_REPEATS)
    parser.add_argument("--perf-skip-correctness-check", action="store_true",
                        default=defaults.PERFORMANCE_TEST_CHECKS_CORRECTNESS,
                        help="(Performance tests only) measure performance even if associated correctness test fails" )
    parser.add_argument("--perf-file-size", type=str,
                        default=defaults.PERFORMANCE_TEST_FILE_SIZE,
                        help="(Performance tests only) Size of test file to use (eg. 10M); use 'auto' to calibrate automatically")
    parser.add_argument("--perf-benchmark-duration", type=float,
                        default=defaults.CALIBRATION_TIME,
                        help="(Performance tests only) Time to run calibration benchmark, in seconds")
    parser.add_argument("--perf-calibration-mode", type=str,
                        default=CALIBRATION_MODE_MAX,choices=CALIBRATION_MODES,
                        help="Calibration mode")
    parser.add_argument("--corr-use-tmpfs", dest="corr_use_tmpfs", action="store_const", const=True)
    parser.add_argument("--corr-no-tmpfs",  dest="corr_use_tmpfs", action="store_const", const=False)
    parser.add_argument("--perf-use-tmpfs", dest="perf_use_tmpfs", action="store_const", const=True)
    parser.add_argument("--perf-no-tmpfs",  dest="perf_use_tmpfs", action="store_const", const=False)

    parser.add_argument("test_group", type=str, default="all")


    args = parser.parse_args(input_args)

    test_group = args.test_group
    timeout = args.timeout
    perf_check_correctness = (not args.perf_skip_correctness_check)

    results = TestResults()

    corr_use_tmpfs = defaults.CORRECTNESS_USE_TMPFS
    if args.corr_use_tmpfs is not None:
        corr_use_tmpfs = args.corr_use_tmpfs

    perf_use_tmpfs = defaults.PERFORMANCE_USE_TMPFS
    if args.perf_use_tmpfs is not None:
        perf_use_tmpfs = args.perf_use_tmpfs

    impls_checked = None
    if test_group != "perf":
        _corr_group = test_group
        if test_group == "correctness":
            _corr_group = "all"

        correctness_test.run(test_group=_corr_group,
                             seed=args.seed,
                             try_tmpfs=corr_use_tmpfs,
                             fuzz_test_repeats=args.fuzz_repeat,
                             grader_mode=args.grader,
                             results=results)
        impls_checked = correctness_test.IMPLS_SEEN

    perf_run = False
    if test_group == "perf" or test_group == "all":
        perf_run = True
        performance_test.run(timeout=timeout,
                             file_size=args.perf_file_size,
                             grader_mode=args.grader,
                             calibration_time_sec=args.perf_benchmark_duration,
                             calibration_mode=args.perf_calibration_mode,
                             try_tmpfs=perf_use_tmpfs,
                             check_correctness=perf_check_correctness,
                             results=results)

    if not args.grader:
        order = correctness_test.TESTS_ORDER.copy()
        if perf_run:
            order.append("performance")

        results.show_summary(order, impls_seen=impls_checked)

    if args.json:
        results.write_json(args.json)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
