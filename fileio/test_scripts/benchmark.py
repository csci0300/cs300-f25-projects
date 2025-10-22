#!/usr/bin/env python3

import re
import os
import sys
import json
import signal
import pathlib
import argparse
import tempfile
import subprocess
import datetime

from dataclasses import dataclass, field

import util
from correctness_test import TestByteCat, TestReverseByteCat, \
    TestBlockCat, TestReverseBlockCat, TestRandomBlockCat, \
    TestStrideCat, TestDiabolicalByteCat, shell_return


HEADER = "\033[95m"
OKBLUE = "\033[94m"
OKCYAN = "\033[96m"
OKGREEN = "\033[92m"
WARNING = "\033[93m"
FAIL = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"


TIMEOUT_SEC = 15
GRADER_MODE = False

# PGID of running test program
RUNNING_PGID = None


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

def silent_shell(cmd, echo=False):
    if echo:
        print("-> {}".format(cmd))

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

def get_sec(time_str):
    parts = time_str.split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[0])
    else:
        return int(parts[0]) * 60 + float(parts[1])


def _get_usec(d: datetime.timedelta):
    return int((d.seconds * 1e6) + d.microseconds)

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
        #log(FAIL + f"timed out after {TIMEOUT_SEC} seconds" + ENDC)
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


def byte_cat(infile, outfile):
    return f'./byte_cat {infile} {outfile}'

def diabolical_byte_cat(infile, outfile):
    return f'./diabolical_byte_cat {infile} {outfile}'

def reverse_byte_cat(infile, outfile):
    return f'./reverse_byte_cat {infile} {outfile}'

def block_cat(infile, outfile):
    return f'./block_cat 32 {infile} {outfile}'

def reverse_block_cat(infile, outfile):
    return f'./reverse_block_cat 32 {infile} {outfile}'

def random_block_cat(infile, outfile):
    return f'./random_block_cat {infile} {outfile}'

def stride_cat(infile, outfile):
    return f'./stride_cat 1 1024 {infile} {outfile}'

def _run_benchmark(prefix, run_func, file_size):
    _prefix = pathlib.Path(prefix)
    infile = str(_prefix / "infile")
    outfile = str(_prefix / "outfile")

    silent_shell(f"rm -f {infile} {outfile}")
    silent_shell(f'dd if=/dev/urandom of={infile} bs={file_size} count=1')

    perf_results = time_program(run_func(infile, outfile))
    silent_shell(f"rm -f {infile} {outfile}")

    return perf_results


TIMEOUT_STR = "[timed out]"
SKIPPED_STR = "[skipped]"

def do_run(uname: str, impl: str, prefix: str, trials=1):
    global TIMEOUT_SEC
    global TMPFS_PREFIX

    def _signit_handler(sig, frame):
        global RUNNING_PGID
        if RUNNING_PGID is not None:
            log(f"Ending currently running test (PGID {RUNNING_PGID})...")
            os.killpg(RUNNING_PGID, signal.SIGTERM)

        raise KeyboardInterrupt

    def _fs_string(s):
        return "tmpfs" if s == TMPFS_PREFIX else "base"


    silent_shell("make clean")
    silent_shell('CFLAGS=-DCACHE_SIZE=4096 make -B IMPL={}'.format(impl), echo=True)

    size_min = 0.5 * 1024 * 1024
    size_max = 32 * 1024 * 1024
    size_inc = lambda x: x * 2
    sizes_mb = [0.5, 1, 4, 8, 16, 32]
    sizes_bytes = [int(x * (1024 * 1024)) for x in sizes_mb]

    benchmarks = {
        'byte_cat': byte_cat,
        'reverse_byte_cat': reverse_byte_cat,
        'block_cat': block_cat,
        'reverse_block_cat': reverse_block_cat,
        #'random_block_cat': random_block_cat,
        'stride_cat': stride_cat,
    }

    results = []
    skip = set()

    #curr_size = int(size_min)
    for curr_size in sizes_bytes:
        size_mb = curr_size / (1024 * 1024)
        size_key = "{}M".format(size_mb)
        res_this_size = {
            "prefix": _fs_string(prefix),
            "uname": uname,
            "impl": impl,
            "size": curr_size,
            "size_mb": size_key,
        }

        b_results = []
        for name, func in benchmarks.items():
            print("\nRunning benchmark {}:{}:{}:{}M => ".format(_fs_string(prefix), impl, name, size_mb), end="")
            sys.stdout.flush()

            if name in skip:
                print(SKIPPED_STR)
                continue

            times_this_benchmark = []
            for t in range(0, trials):
                signal.signal(signal.SIGINT, _signit_handler)

                runtime = _run_benchmark(prefix, func, curr_size)

                signal.signal(signal.SIGINT, signal.SIG_DFL)

                res: dict = {
                    "trial": t,
                    "benchmark": name,
                }

                t_run = runtime["wtime"] if runtime is not None else TIMEOUT_STR

                times_this_benchmark.append(t_run)
                res["time"] = t_run

                b_results.append(res)
                if runtime is None:
                    stats = "[timed out] "
                else:
                    runtime_shell_sec = runtime["wtime"]
                    stats = "{:.3f}s ".format(runtime_shell_sec)

                print(stats, end="")
                sys.stdout.flush()

            if all([x is TIMEOUT_STR for x in times_this_benchmark]):
                print(f"\nAll trials of {name} timed out, skipping for the rest of this batch")
                skip.add(name)

        #curr_size = size_inc(curr_size)
        print("")

        res_this_size["tests"] = b_results
        results.append(res_this_size)

    return results


IMPLS = [
    "stdio",
    "naive"
]


TMPFS_PREFIX = "/tmp/io300_benchmark"

PREFIXES = [
    "/tmp",
    TMPFS_PREFIX,
]



def _do_setup_tmpfs():
    chk = subprocess.check_output("mount | grep {} || true".format(TMPFS_PREFIX), shell=True, text=True)
    if "tmpfs" in chk:
        print("tmpfs found, not creating mount point")
        return True

    def _run(cmd):
        print("-> {}", cmd)
        subprocess.check_output(cmd, shell=True)

    _run("mkdir -p {}".format(TMPFS_PREFIX))
    _run("sudo mount -t tmpfs none {}".format(TMPFS_PREFIX))

    _chk = subprocess.check_output("mount | grep {} || true".format(TMPFS_PREFIX), shell=True, text=True)
    if "tmpfs" not in _chk:
        return False
    else:
        return True


DEFAULT_TRIALS = 3
def main(input_args):
    global TIMEOUT_SEC

    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=TIMEOUT_SEC)
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument("--output-file", default="benchmark.json")
    parser.add_argument("--key", type=str, default=None)

    args = parser.parse_args(input_args)


    uname_proc = subprocess.run("uname -a",
                                shell=True, text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    assert(uname_proc.returncode == 0)
    uname = uname_proc.stdout
    key = args.key

    if args.timeout:
        TIMEOUT_SEC = args.timeout

    tmpfs_ok = _do_setup_tmpfs()
    if (not tmpfs_ok):
        print("tmpfs setup failed, skipping tmpfs benchmarks")

    json_out = {
        "uname": uname,
        "timeout_usec": int(TIMEOUT_SEC * 1e6),
        "results": [],
    }

    if key:
        json_out["key"] = key

    results = []
    for prefix in PREFIXES:
        for impl in IMPLS:
            if prefix == TMPFS_PREFIX and (not tmpfs_ok):
                continue

            impl_results = do_run(uname, impl, prefix, trials=args.trials)
            results.extend(impl_results)

    json_out["results"] = results

    output_file = args.output_file if args.output_file is not None else \
        "{}.json".format(key)
    with open(output_file, "w") as fd:
        json.dump(json_out, fd,
                  indent=True, sort_keys=False)

    print("Done!  Output written to {}".format(output_file))

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
