#!/usr/bin/env python3

import re
import os
import sys
import json
import signal
import argparse
import tempfile
import subprocess

GRADER_MODE = False

TIMEOUT_SEC = 0

HEADER = "\033[95m"
OKBLUE = "\033[94m"
OKCYAN = "\033[96m"
OKGREEN = "\033[92m"
WARNING = "\033[93m"
FAIL = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"

TEST_FILE_PREFIX = "/tmp"

# Set if ratio computation saw a result that was too small
WARN_TIME_TOO_SHORT = False

# PGID of running test program
RUNNING_PGID = None

import util
import defaults

from correctness_test import TestSpec, TestByteCat, TestReverseByteCat, \
    TestBlockCat, TestReverseBlockCat, TestRandomBlockCat, \
    TestStrideCat, TestDiabolicalByteCat

log_lines = []

def log(msg, end="\n", flush=False):
    global GRADER_MODE
    global log_lines

    if not GRADER_MODE:
        print(msg, end=end, flush=flush)
        if flush:
            sys.stdout.flush()
            sys.stdout.buffer.flush()
        if end == "\n" or len(log_lines) == 0:
            log_lines.append(msg)
        else:
            log_lines[-1] += msg


def clear_log():
    global log_lines
    log_lines = []


def get_log_output():
    global log_lines
    return "\n".join(log_lines)


def silent_shell(cmd):
    sp = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )
    if sp.returncode != 0:
        print(f'fatal: the command `${cmd}` failed')
        print(str(sp.stdout, encoding='utf-8', errors="backslashreplace"))
        print(str(sp.stderr, encoding='utf-8', errors="backslashreplace"))
        sys.exit(1)


def parse_size(size):
    if isinstance(size, int):
        return size

    units = {"B": 1, "K": 2**10, "M": 2**20, "G": 2**30, "T": 2**40}
    size = size.upper()

    if not re.match(r' ', size):
        size = re.sub(r'([KMGTB])(?:[B]?)', r' \1', size)
    x = [string.strip() for string in size.split()]
    number, unit = x

    c = unit[0]
    if c not in units:
        raise ValueError(f"Invalid size prefix {c}")

    return int(float(number)*units[unit[0]])


def get_sec(time_str):
    parts = time_str.split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[0])
    else:
        return int(parts[0]) * 60 + float(parts[1])


def get_time_field(output, fieldname) -> int:
    try:
        fieldstart = output.index(fieldname) + len(fieldname)
        fieldend = output.index('\\n', fieldstart)
        # parse the number in the field (might be a percentage)
        if "wall" in fieldname:
            return get_sec(output[fieldstart:fieldend])
        else:
            return float(output[fieldstart:fieldend].replace('%', ''))
    except:
        return None

def time_program(progcmd):
    global TIMEOUT_SEC
    global RUNNING_PGID

    timeout_arg = TIMEOUT_SEC if TIMEOUT_SEC > 0 else None

    sp = None
    failed = False
    cmd = ['/usr/bin/time', '--verbose', '--'] + progcmd.split(' ')
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            preexec_fn=os.setpgrp)

    RUNNING_PGID = os.getpgid(proc.pid)
    stdout, stderr = bytes(), bytes()
    try:
        stdout, stderr = proc.communicate(timeout=timeout_arg)
    except subprocess.TimeoutExpired:
        proc.kill()
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        log(FAIL + f"timed out after {TIMEOUT_SEC} seconds" + ENDC)
        failed = True

    returncode = proc.returncode
    if failed or returncode != 0:
        if sp is not None:
            log(str(stdout, encoding='utf-8', errors="backslashreplace"))
            log(str(stderr, encoding='utf-8', errors="backslashreplace"))
        return None

    time_output = str(stderr)

    perf_data = {
        'cpu': get_time_field(time_output, 'Percent of CPU this job got:'),
        'stime': get_time_field(time_output, 'System time (seconds):'),
        'utime': get_time_field(time_output, 'User time (seconds):'),
        'wtime': get_time_field(time_output, 'Elapsed (wall clock) time (h:mm:ss or m:ss):'),
        'mrss': get_time_field(time_output, 'Maximum resident set size (kbytes):'),
        'arss': get_time_field(time_output, 'Average resident set size (kbytes):'),
    }

    if None in perf_data.values():
        # we couldn't parse the output, so the command probably failed
        return None
    else:
        return perf_data

CALIBRATION_MODE_MAX = "max"
CALIBRATION_MODE_FREE = "free"
CALIBRATION_MODES = [CALIBRATION_MODE_MAX, CALIBRATION_MODE_FREE]

def determine_test_size(test_map: dict[str,TestSpec], calibration_time,
                        verbose=False, mode=CALIBRATION_MODE_MAX):
    silent_shell("make clean")
    silent_shell('CFLAGS=-DCACHE_SIZE=4096 make -B IMPL=stdio')

    size_min = 1 * 1024 * 1024
    size_max = 512 * 1024 * 1024
    target_sec = calibration_time
    size_inc = lambda x: x * 2

    def _run_benchmark(run_func, file_size):
        infile = f'{TEST_FILE_PREFIX}/infile'
        outfile = f'{TEST_FILE_PREFIX}/outfile'

        silent_shell(f"rm -f {infile} {outfile}")
        silent_shell(f"touch {outfile}")
        silent_shell(f'dd if=/dev/urandom of={infile} bs={file_size} count=1')

        perf_results = time_program(run_func(infile, outfile, "/dev/null"))
        silent_shell(f"rm -f {infile} {outfile}")

        if not perf_results:
            print("Unable to calibrate")
            sys.exit(1)

        runtime = perf_results["wtime"]
        return runtime

    initial_size_map: dict[str,int] = {}
    for name, spec in test_map.items():
        curr_size = size_min
        found = False
        while curr_size < size_max:
            if verbose:
                print(".", end="", flush=True)

            func = spec.run_cmd
            runtime = _run_benchmark(func, curr_size)
            #print("{} {}M => {:.2f}s".format(name, curr_size / (1024 * 1024), runtime))
            if runtime > target_sec:
                found = True
                break
            else:
                curr_size = size_inc(curr_size)

        if not found:
            print(f"Warning:  {name} exceeded max option finding test file size")

        initial_size_map[name] = curr_size

    final_size_map: dict[str,int] = {}
    if mode == CALIBRATION_MODE_MAX:
        sorted_pairs = sorted(initial_size_map.items(), key=lambda kv: kv[1])
        target_testname, target_size = sorted_pairs[-1]
        _size_mb = target_size / (1024*1024)
        print(f"Using test file size {_size_mb}M (from benchmark {target_testname})")

        for testname in initial_size_map.keys():
            final_size_map[testname] = target_size
    elif mode == CALIBRATION_MODE_FREE:
        final_size_map = initial_size_map.copy()
    else:
        raise ValueError(f"Unsupported calibration mode {mode}")

    return final_size_map


def runtests(tests, size_map, res: util.TestResults,
             check_correctness=False):
    global GRADER_MODE

    results = {}
    for testname in tests:
        results[testname] = {}

    infile = f'{TEST_FILE_PREFIX}/infile'
    outfile = f'{TEST_FILE_PREFIX}/outfile'
    outfile2 = f'{TEST_FILE_PREFIX}/expected'

    def _is_pass(test_name, ratio):
        if ratio == "student test failed":
            return False
        elif "byte" in test_name and ratio <= 10.0:
            return True
        elif ratio <= 5.0:
            return True
        else:
            return False

    def _fmt_float(ratio):
        return round(ratio, 2) if isinstance(ratio, int) or isinstance(ratio, float) else ""

    def _print_result(test, ratio, indent=False):
        if ratio == 'student test failed':
            s = "{}: \033[31;1mfailed\033[0m".format(test)
        elif _is_pass(test, ratio):
            s = "{}: \033[32;1m{}x\033[0m stdio's runtime".format(test, _fmt_float(ratio))
        else:
            s = "{}: \033[31;1m{}x\033[0m stdio's runtime".format(test, _fmt_float(ratio))

        if indent:
            print("\t{}\n".format(s))
        else:
            print(s)

    def _compute_log_result(testname, file_size, stdio, student, print_log=False):
        global WARN_TIME_TOO_SHORT
        stdio_time = stdio['wtime']
        student_time = student['wtime']

        if stdio_time == 0.0:
            stdio_time = 0.001

        ratio = student_time / stdio_time
        if print_log:
            _print_log(testname, file_size, stdio_time, student_time, indent=True)

        if stdio_time < defaults.WARN_TIME_THRESHOLD:
            WARN_TIME_TOO_SHORT = True
            log("\t\t{}WARNING:  stdio time is very short, results may be inaccurate{}".format(WARNING, ENDC))

        return ratio, stdio_time, student_time

    def _print_log(testname, file_size, stdio_time, student_time, indent=False):
        _size = int(file_size) if file_size >= 1.0 else round(file_size, 2)
        log('%sperformance result: %s: size=%sM, stdio=%.2fs, student=%.2fs, ratio=%.2f' \
            % ('\t' if indent else '', testname, _size, stdio_time, student_time, student_time / stdio_time))

    def _signit_handler(sig, frame):
        global RUNNING_PGID
        if RUNNING_PGID is not None:
            log(f"Ending currently running test (PGID {RUNNING_PGID})...")
            os.killpg(RUNNING_PGID, signal.SIGTERM)

        raise KeyboardInterrupt

    def suite(makecmd, impl):
        log(f'\033[31mrunning test suite: {impl}\033[0m')
        silent_shell('make clean')
        silent_shell(makecmd)

        for (i, testname) in enumerate(tests):
            log(f'\033[32m{i + 1}. {impl}::{testname}\033[0m')

            def _truncate_file(f):
                silent_shell(f"rm -f {f}")
                silent_shell(f"touch {f}")

            _truncate_file(infile)
            _truncate_file(outfile)
            _truncate_file(outfile2)

            test_file_size = size_map[testname]
            _test_size_mb = test_file_size / (1024 * 1024)
            silent_shell(f'dd if=/dev/urandom of={infile} bs={test_file_size} count=1')

            test_class = tests[testname]
            prog_str = test_class.run_cmd(infile, outfile, outfile2)
            log('-> ' + prog_str)

            clear_log()
            this_result = time_program(prog_str)
            if check_correctness and (this_result is not None) and (impl != "stdio"):
                is_correct = test_class.check(infile, outfile,
                                              outfile2)
                if not is_correct:
                    log("\t" + FAIL + "Test program finished, but output file was not correct.  Make sure correctness tests are passing." + ENDC)
                    this_result = None

            results_this_test = results[testname]
            results_this_test[impl] = this_result

            if (not GRADER_MODE) and (impl == "student"):
                if "stdio" in results_this_test:
                    ratio = ""
                    time_stdio = ""
                    time_student = ""

                    if this_result is None:
                        log("\t" + FAIL + "student test failed" + ENDC)
                    else:
                        stdio_result = results_this_test["stdio"]

                        ratio, time_stdio, time_student = \
                            _compute_log_result(testname,
                                                _test_size_mb,
                                                stdio=stdio_result,
                                                student=this_result, print_log=True)
                        _print_result(testname, ratio, indent=True)

                    if res:
                        output = get_log_output()
                        is_pass = ratio != "" and _is_pass(testname, ratio)
                        res.add_test(testname, "performance", is_pass, output)
                        res.add_extra("size_{}".format(testname), test_file_size)
                        res.add_extra("ratio_{}".format(testname), _fmt_float(ratio))
                        res.add_extra("time_{}_{}".format(testname, "stdio"),
                                      _fmt_float(time_stdio))
                        res.add_extra("time_{}_{}".format(testname, "student"),
                                      _fmt_float(time_student))

    signal.signal(signal.SIGINT, _signit_handler)

    suite('make -B IMPL=stdio', 'stdio')
    suite('CFLAGS=-DCACHE_SIZE=4096 make -B IMPL=student', 'student')

    signal.signal(signal.SIGINT, signal.SIG_DFL)


    metrics = {}
    for testname in tests:
        if type(results[testname]['stdio']) is not dict:
            print('ERROR: stdio program failed. This should not happen, please contact the course staff')
            print(results[testname]['stdio'])
            sys.exit(1)
        if results[testname]['student'] is None:
            #log('student program failed')
            metrics[testname] = 'student test failed'
            continue

        stdio_time = results[testname]['stdio']['wtime']
        student_time = results[testname]['student']['wtime']

        if stdio_time == 0.0:
            stdio_time = 0.001

        ratio = student_time / stdio_time
        metrics[testname] = ratio
        test_file_size = size_map[testname]
        test_size_mb = test_file_size / (1024 * 1024)
        _print_log(testname, test_size_mb, stdio_time, student_time)

    log('======= PERFORMANCE RESULTS =======')
    if not GRADER_MODE:
        for (test, ratio) in metrics.items():
            _print_result(test, ratio)
    else:
        print(json.dumps(metrics, indent=4))

    silent_shell('make clean')
    silent_shell(f'rm -- {infile} {outfile}')

def run(timeout=0,
        file_size=None,
        grader_mode=False,
        check_correctness=True,
        try_tmpfs=True,
        calibration_time_sec=defaults.CALIBRATION_TIME,
        calibration_mode=defaults.CALIBRATION_MODE,
        results: util.TestResults|None=None):
    global TIMEOUT_SEC
    global GRADER_MODE
    global WARN_TIME_TOO_SHORT
    global TEST_FILE_PREFIX

    if grader_mode:
        GRADER_MODE = True

    if timeout != 0:
        TIMEOUT_SEC = timeout

    tmpfs_ok = False
    if try_tmpfs:
        tmpfs_ok = util.tmpfs_try_setup(util.TMPFS_PREFIX)
        if tmpfs_ok:
            TEST_FILE_PREFIX = util.TMPFS_PREFIX
    log('======= PERFORMANCE TESTS =======')

    TESTS_TO_RUN = {
        'byte_cat': TestByteCat(),
    #    'diabolical_byte_cat': TestDiabolicalByteCat,
        'reverse_byte_cat': TestReverseByteCat(),
        'block_cat': TestBlockCat(32),
        'reverse_block_cat': TestReverseBlockCat(32),
        'random_block_cat': TestRandomBlockCat(),
        'stride_cat': TestStrideCat(1, 1024),
    }

    _verbose = (not GRADER_MODE)
    size_map: dict[str,int] = {}

    if file_size == "auto":
        file_size=None

    if file_size is None:
        log("Checking optimal file size to use for tests (test dir {}) ...".format(TEST_FILE_PREFIX),
            end="" if _verbose else "\n", flush=_verbose)
        size_map = determine_test_size(TESTS_TO_RUN, calibration_time_sec,
                                       mode=calibration_mode,
                                       verbose=(not GRADER_MODE))
    else:
        file_size = parse_size(file_size)
        for name, spec in TESTS_TO_RUN.items():
            size_map[name] = file_size

    if results:
        results.add_extra("perf_calibration_time", calibration_time_sec)
        results.add_extra("tmpfs", tmpfs_ok);


    runtests(TESTS_TO_RUN, size_map, res=results, check_correctness=check_correctness)

    if WARN_TIME_TOO_SHORT:
        if results:
            results.add_extra("perf_warn_stdio_too_short", True);
        if not GRADER_MODE:
            min_size = min(size_map.values())
            min_size_mb = min_size / (1024 * 1024)
            print("{}WARNING:  some stdio benchmarks completed too quickly (< {}s)\n"
                  "which may lead to inaccurate results.  To fix this, re-run the\n"
                  "performance tests with a larger filesize, e.g.:"
            "\n\tmake perf FILESIZE={}M\n"
            "or try running on the grading server{}"
            .format(WARNING, defaults.WARN_TIME_THRESHOLD, 2 * min_size_mb, ENDC))


def main(input_args):
    global TIMEOUT_SEC
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=0)
    parser.add_argument("--grader", action="store_true")
    parser.add_argument("--skip-correctness-check", action="store_true",
                        default=defaults.PERFORMANCE_TEST_CHECKS_CORRECTNESS)
    parser.add_argument("--file-size", type=str,
                        default=defaults.PERFORMANCE_TEST_FILE_SIZE,
                        help="Size of test file to use (eg. 10M); use 'auto' to calibrate automatically")
    parser.add_argument("--benchmark-duration", type=float,
                        default=defaults.CALIBRATION_TIME,
                        help="Time to run calibration benchmark, in seconds")
    parser.add_argument("--calibration-mode", type=str,
                        default=CALIBRATION_MODE_MAX,choices=CALIBRATION_MODES,
                        help="Calibration mode")
    parser.add_argument("--create-tmpfs", dest="create_tmpfs", action="store_const", const=True)
    parser.add_argument("--no-create-tmpfs", dest="create_tmpfs", action="store_const", const=False)

    args = parser.parse_args(input_args)

    create_tmpfs = defaults.PERFORMANCE_USE_TMPFS
    if args.create_tmpfs is not None:
        create_tmpfs = args.create_tmpfs

    results = util.TestResults()
    run(timeout=args.timeout,
        file_size=args.file_size,
        grader_mode=args.grader,
        calibration_time_sec=args.benchmark_duration,
        results=results,
        try_tmpfs=create_tmpfs,
        calibration_mode=args.calibration_mode,
        check_correctness=(not args.skip_correctness_check))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
