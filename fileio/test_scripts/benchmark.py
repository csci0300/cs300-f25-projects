#!/usr/bin/env python3

import re
import os
import sys
import json
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


TIMEOUT_SEC = 120
GRADER_MODE = False

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

    timeout_arg = TIMEOUT_SEC if TIMEOUT_SEC > 0 else None

    sp = None
    failed = False
    try:
        sp = subprocess.run(
            ['/usr/bin/time', '--verbose', '--'] + progcmd.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_arg,
        )
    except subprocess.TimeoutExpired:
        log(FAIL + f"timed out after {TIMEOUT_SEC} seconds" + ENDC)
        failed = True

    if failed or sp.returncode != 0:
        if sp is not None:
            log(str(sp.stdout, encoding='utf-8', errors="backslashreplace"))
            log(str(sp.stderr, encoding='utf-8', errors="backslashreplace"))
        return None

    time_output = str(sp.stderr)

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


def time_program_dt(progcmd):
    global TIMEOUT_SEC

    timeout_arg = TIMEOUT_SEC if TIMEOUT_SEC > 0 else None

    sp = None
    failed = False
    time_start = None
    time_end = None

    try:
        time_start = datetime.datetime.now()
        sp = subprocess.run(
            ['/usr/bin/time', '--verbose', '--'] + progcmd.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_arg,
        )
        time_end = datetime.datetime.now()
    except subprocess.TimeoutExpired:
        log(FAIL + f"timed out after {TIMEOUT_SEC} seconds" + ENDC)
        failed = True

    if failed or sp.returncode != 0:
        if sp is not None:
            log(str(sp.stdout, encoding='utf-8', errors="backslashreplace"))
            log(str(sp.stderr, encoding='utf-8', errors="backslashreplace"))
        return None

    assert(time_start is not None)
    assert(time_end is not None)
    t_diff = (time_end - time_start)
    t_usec = _get_usec(t_diff)

    time_output = str(sp.stderr)

    perf_data = {
        'cpu': get_time_field(time_output, 'Percent of CPU this job got:'),
        'stime': get_time_field(time_output, 'System time (seconds):'),
        'utime': get_time_field(time_output, 'User time (seconds):'),
        'wtime': get_time_field(time_output, 'Elapsed (wall clock) time (h:mm:ss or m:ss):'),
        'mrss': get_time_field(time_output, 'Maximum resident set size (kbytes):'),
        'arss': get_time_field(time_output, 'Average resident set size (kbytes):'),
        "usec": t_usec,
    }

    if None in perf_data.values():
        # we couldn't parse the output, so the command probably failed
        return None
    else:
        return perf_data

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

    perf_results = time_program_dt(run_func(infile, outfile))
    silent_shell(f"rm -f {infile} {outfile}")

    return perf_results


def do_run(uname: str, impl: str, prefix: str):
    global TIMEOUT_SEC

    silent_shell("make clean")
    silent_shell('CFLAGS=-DCACHE_SIZE=4096 make -B IMPL={}'.format(impl), echo=True)

    size_min = 1 * 1024 * 1024
    size_max = 256 * 1024 * 1024
    size_inc = lambda x: x * 2

    benchmarks = {
        'byte_cat': byte_cat,
        #'diabolical_byte_cat': diabolical_byte_cat,
        'reverse_byte_cat': reverse_byte_cat,
        'block_cat': block_cat,
        'reverse_block_cat': reverse_block_cat,
        'random_block_cat': random_block_cat,
        'stride_cat': stride_cat,
        '_no_op': lambda inf, outf: f'/bin/true',
    }

    results = []

    curr_size = int(size_min)
    while curr_size <= size_max:
        size_mb = curr_size / (1024 * 1024)
        size_key = "{}M".format(size_mb)
        res_this_size = {
            "prefix": prefix,
            "uname": uname,
            "impl": impl,
            "size": curr_size,
            "size_mb": size_key,
        }

        b_results = []
        for name, func in benchmarks.items():
            print("Running {}:{}:{}:{}M".format(prefix, impl, name, size_mb), end="")
            sys.stdout.flush()

            runtime = _run_benchmark(prefix, func, curr_size)
            res: dict = {
                "benchmark": name,
            }
            res["t_shell"] = runtime["wtime"] if runtime is not None else float(TIMEOUT_SEC)
            res["t_usec"] = runtime["usec"] if runtime is not None else int(TIMEOUT_SEC * 1e6)

            b_results.append(res)
            if runtime is None:
                print("=> TIMED OUT")
            else:
                runtime_shell_sec = runtime["wtime"]
                runtime_dt_sec = float(runtime["usec"]) / 1e6
                stats = "=> {:.3f}s, {:.3f}s".format(runtime_shell_sec, runtime_dt_sec)
                print("{:>35}".format(stats))

        curr_size = size_inc(curr_size)

        res_this_size["tests"] = b_results
        results.append(res_this_size)

    return results


IMPLS = [
    "stdio",
    "naive"
]


TMPFS_PREFIX = "/tmp/tmp"

PREFIXES = [
    "/tmp",
    TMPFS_PREFIX,
]


def _do_setup_tmpfs():
    chk = subprocess.check_output("mount | grep {} || true".format(TMPFS_PREFIX), shell=True, text=True)
    if "tmpfs" in chk:
        print("tmpfs found, not creating mount point")
        return

    def _run(cmd):
        print("-> {}", cmd)
        subprocess.check_output(cmd, shell=True)

    _run("mkdir -p {}".format(TMPFS_PREFIX))
    _run("sudo mount -t tmpfs none {}".format(TMPFS_PREFIX))

    _chk = subprocess.check_output("mount | grep {} || true".format(TMPFS_PREFIX), shell=True, text=True)
    if "tmpfs" not in _chk:
        import pdb; pdb.set_trace()
        raise OSError("Unable to set up tmpfs")

def main(input_args):
    global TIMEOUT_SEC

    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=TIMEOUT_SEC)
    parser.add_argument("--output-file", default=None)
    parser.add_argument("key")

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

    _do_setup_tmpfs()

    json_out = {
        "uname": uname,
        "key": key,
        "timeout_usec": int(TIMEOUT_SEC * 1e6),
        "results": [],
    }

    results = []
    for prefix in PREFIXES:
        for impl in IMPLS:
            impl_results = do_run(uname, impl, prefix)
            results.extend(impl_results)

    json_out["results"] = results

    output_file = args.output_file if args.output_file is not None else \
        "{}.json".format(key)
    with open(output_file, "w") as fd:
        json.dump(json_out, fd,
                  indent=True, sort_keys=False)

    print("Wrote {}".format(output_file))

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
