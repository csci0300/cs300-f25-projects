#!/usr/bin/env python3

import os
import sys
import json
import random
import pathlib
import argparse
import subprocess
from typing import List

from dataclasses import dataclass

import find_impl

HEADER = "\033[95m"
OKBLUE = "\033[94m"
OKCYAN = "\033[96m"
OKGREEN = "\033[32;1m"
WARNING = "\033[93m"
FAIL = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"


MAX_LINES = 20

GRADER_MODE = False

last_log = None

TEST_FILE_PREFIX = "/tmp"
IMPLS_SEEN = set()

import util
import defaults

######################################################################
#########          Test definitions                          #########
######################################################################

@dataclass
class TestSpec:
    def bin_path(self):
        raise NotImplementedError("Subclass must implement")

    def run_cmd(self, infile, outfile, outfile2):
        raise NotImplementedError("Subclass must implement")

    def run(self, infile, outfile, outfile2):
        return shell_return(self.run_cmd(infile, outfile, outfile2)) == 0

    def check(self, infile, outfile, outfile2) -> bool:
        return files_same(infile, outfile) # Default implementation

    def run_and_check(self, infile, outfile, outfile2) -> bool:
        return self.run(infile, outfile, outfile2) \
            and self.check(infile, outfile, outfile2)

@dataclass
class TestByteCat(TestSpec):
    def bin_path(self):
        return './byte_cat'

    def run_cmd(self, infile, outfile, outfile2):
        return f'./byte_cat {infile} {outfile}'

@dataclass
class TestDiabolicalByteCat(TestSpec):
    def bin_path(self):
        return './diabolical_byte_cat'

    def run_cmd(self, infile, outfile, outfile2):
        return f'./diabolical_byte_cat {infile} {outfile}'

@dataclass
class TestReverseByteCat(TestSpec):
    def bin_path(self):
        return './reverse_byte_cat'

    def run_cmd(self, infile, outfile, outfile2):
        return f'./reverse_byte_cat {infile} {outfile}'

    def check(self, infile, outfile, outfile2):
        def _check(inf, outf, outf2):
            return shell_return(f'./test_programs/reference/reverse {inf} {outf2}') == 0
        return check_reference(_check, infile, outfile, outfile2)

@dataclass
class TestBlockCat(TestSpec):
    block_size: int

    def bin_path(self):
        return './block_cat'

    def run_cmd(self, infile, outfile, outfile2):
        return f'./block_cat {self.block_size} {infile} {outfile}'

    def check(self, infile, outfile, outfile2):
        return files_same(infile, outfile)

@dataclass
class TestReverseBlockCat(TestSpec):
    block_size: int

    def bin_path(self):
        return './reverse_block_cat'

    def run_cmd(self, infile, outfile, outfile2):
        return f'./reverse_block_cat {self.block_size} {infile} {outfile}'

    def check(self, infile, outfile, outfile2):
        def _check(inf, outf, outf2):
            return shell_return(f'./test_programs/reference/reverse {inf} {outf2}') == 0
        return check_reference(_check, infile, outfile, outfile2)

@dataclass
class TestRandomBlockCat(TestSpec):
    def bin_path(self):
        return './random_block_cat'

    def run_cmd(self, infile, outfile, outfile2):
        return f'./random_block_cat {infile} {outfile}'

@dataclass
class TestStrideCat(TestSpec):
    block_size: int
    stride: int

    def bin_path(self):
        return './stride_cat'

    def run_cmd(self, infile, outfile, outfile2):
        return f'./stride_cat {self.block_size} {self.stride} {infile} {outfile}'

    def check(self, infile, outfile, outfile2):
        def _check(inf, outf, outf2):
            return shell_return(f'./test_programs/reference/stride {self.block_size} {self.stride} {inf} {outf2}') == 0

        return check_reference(_check, infile, outfile, outfile2)

@dataclass
class FuzzTest(TestSpec):
    functions: str
    rand_seeds: list[int]
    file_size: int = 4096
    max_file_size: int = 8192
    num_ops: int = 8192

    def bin_path(self):
        return './io300_test'

    def run(self, infile, outfile, outfile2):
        ok = True
        for seed in self.rand_seeds:
            rv = shell_return(f'./io300_test {self.functions} --seed {seed} -n {self.num_ops} --file-size {self.file_size} --max-size {self.max_file_size}')
            ok = ok and (rv == 0)
            if not ok:
                break

        return ok

    def check(self, infile, outfile, outfile2):
        # Not needed
        return True

@dataclass
class TestRot13(TestSpec):
    def bin_path(self):
        return './rot13'

    def run(self, infile, outfile, outfile2):
        assert shell_return(f'cp {infile} {outfile}') == 0
        rotate1 = shell_return(f'./rot13 {outfile}') == 0
        if not rotate1:
            return False
        return rotate1

    def check(self, infile, outfile, outfile2):
        shell_return(f'cp {infile} {outfile2}')

        ref_ok = shell_return(f'./test_programs/reference/rot13 {outfile2}') == 0
        if not ref_ok:
            print_test_result(1, "Failed to compute expected file.  "
                              "This should not happen, please contact the course staff")
            return False

        return files_same(outfile2, outfile)

@dataclass
class UnitTest(TestSpec):
    path: str

    def bin_path(self):
        return "./{}".format(str(self.path))

    def run(self, infile, outfile, outfile2):
        return shell_return("./{}".format(str(self.path))) == 0

    def check(self, infile, outfile, outfile2):
        # Unused
        return True

def create_unit_tests():
    run_path = pathlib.Path(".")
    test_paths = []
    def _add(glob):
        test_paths.extend(sorted([str(p) for p in run_path.glob(glob) if str(p) not in test_paths]))

    _add("rtest[0-9][0-9][0-9]*")
    _add("extra[0-9][0-9][0-9]*")

    test_dict = {}
    for p in test_paths:
        test_dict[p] = UnitTest(p)

    return test_dict

######################################################################
#########              End test definitions                  #########
######################################################################



def log(msg):
    global GRADER_MODE
    if not GRADER_MODE:
        print(msg)
        sys.stdout.flush()


def pass_fail_str(rv):
    if rv == 0:
        return OKGREEN + "PASSED" + ENDC
    else:
        return FAIL    + "FAILED" + ENDC


def shell_return(shell_cmd, suppress=False, output_on_fail=True):
    if not suppress:
        log('-> ' + shell_cmd)
    proc = subprocess.run(
        shell_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True
    )
    if output_on_fail:
        if proc.returncode != 0:
            output = proc.stdout.decode("utf-8",errors="backslashreplace").strip()
            print_test_result(proc.returncode, output)

    return proc.returncode


def print_test_result(rv, output, header=True):
    global last_log

    if len(output) != 0:
        output_lines = output.split("\n")
        if len(output_lines) > MAX_LINES:
            output_lines = output_lines[:MAX_LINES]
            output_lines.append("[output clipped]")
        output_fmt = "\t" + FAIL + ("Test failed:\n\t" if header else "") \
                + "\n\t".join(output_lines) + ENDC

        log(output_fmt)
        last_log = output_fmt


def files_same_size(expected, actual, output_on_fail=True):
    size_expected = os.path.getsize(expected)
    size_actual = os.path.getsize(actual)

    if size_expected != size_actual:
        if output_on_fail:
            output = f"File sizes differ:  expected {size_expected} ({expected}), got {size_actual} ({actual})\n"
            print_test_result(1, output)
        return False
    else:
        return True


def files_same(expected, actual, output_on_fail=True):
    same_size = files_same_size(expected, actual, output_on_fail=output_on_fail)
    if not same_size:
        return False

    same_contents = shell_return(f'diff {expected} {actual}',
                                 suppress=True, output_on_fail=output_on_fail) == 0

    return same_size and same_contents

def check_reference(reference_proc, infile, outfile, outfile2):
    # Reference_proc must be a lambda that runs the reference_program
    # when given three arguments:  infile, outfile, outfile2

    output_modified = not files_same(infile, outfile, output_on_fail=False)
    if not output_modified:
        print_test_result(1, "Output file was unchanged")
        return False

    ref_ok = reference_proc(infile, outfile, outfile2)
    if not ref_ok:
        print_test_result(1, "Failed to compute expected file.  "
                          "This should not happen, please contact the course staff")
        return False

    return files_same(outfile2, outfile) # expected, actual


def runtests(tests, suite_name, results: util.TestResults,
             write_json=False):
    global GRADER_MODE
    global TEST_FILE_PREFIX
    global IMPLS_SEEN
    global last_log

    os.environ["IO300_TEST_RUN"] = str(1);

    infile = f'{TEST_FILE_PREFIX}/infile'
    outfile = f'{TEST_FILE_PREFIX}/outfile'
    outfile2 = f'{TEST_FILE_PREFIX}/expected'
    integrity = f'{TEST_FILE_PREFIX}/integrity'
    assert shell_return(f'touch {infile}', suppress=True) == 0
    assert shell_return(f'dd if=/dev/urandom of={infile} bs=4096 count=20', suppress=True) == 0
    assert shell_return(f'touch {integrity}', suppress=True) == 0
    assert shell_return(f'cp {infile} {integrity}', suppress=True) == 0

    for (i, test) in enumerate(tests):
        # Truncate output files

        def _truncate_file(f):
            assert shell_return(f"rm -f {f}", suppress=True) == 0
            assert shell_return(f"touch {f}", suppress=True) == 0

        _truncate_file(outfile)
        _truncate_file(outfile2)

        log(f'{OKBLUE}{i + 1}. {test}{ENDC}')

        testclass = tests[test]

        bin_path = testclass.bin_path()
        this_impl = find_impl.try_find_impl(str(bin_path))
        if this_impl is not None:
            IMPLS_SEEN.add(this_impl)

        if test == "ascii_independence":
            assert shell_return(f'touch man_nonascii.txt', suppress=True) == 0
            f = open("man_nonascii.txt", 'w')
            f.write("Make\x00sure\x00your\x00cache\x00can\x00handle\x00null\x00bytes! 가정하는 것은 안전하지 않습니다 प्रत्येकं पात्रं इति 'n ASCII-karakter.")
            f.close()
            assert shell_return(f'touch man_integrity', suppress=True) == 0
            assert shell_return(f'cp man_nonascii.txt man_integrity', suppress=True) == 0

            passed = testclass.run_and_check("man_nonascii.txt", outfile, outfile2)

            if not files_same("man_nonascii.txt", "man_integrity"):
                if not GRADER_MODE:
                    print(WARNING + 'oops, your program modified the input file' + ENDC)
                tests[test] = False
            else:
                tests[test] = True

            tests[test] = passed
            assert shell_return(f'rm -- man_nonascii.txt man_integrity', suppress=True) == 0
        else:
            passed = testclass.run_and_check(infile, outfile, outfile2)
            if suite_name == "REGRESSION":
                tests[test] = passed
            else:
                if not files_same(infile, integrity):
                    print(WARNING + 'oops, your program modified the input file' + ENDC)
                    tests[test] = False
                else:
                    tests[test] = passed

        if tests[test]:
            log("\t" + OKGREEN + "PASSED!" + ENDC)

        if results:
            group = "{}".format(suite_name).lower()
            output = last_log if last_log is not None else ""
            results.add_test(test, group, tests[test], output)

        last_log = None

    log('\nYour results follow, indicating if each test passed or failed.')
    log(f'======= TEST SUMMARY:  {suite_name} TESTS =======')
    log(util.make_impl_check_msg(IMPLS_SEEN))

    ok = True

    if not write_json:
        for (test, passed) in tests.items():
            if passed:
              print("{}: {}PASSED{}".format(test, OKGREEN, ENDC))
            else:
              print("{}: {}FAILED{}".format(test, FAIL, ENDC))
              ok = False
    else:
        print("{},".format(json.dumps(tests, indent=4)))

    del os.environ["IO300_TEST_RUN"]
    assert shell_return(f'rm -f -- {infile} {outfile} {outfile2} {integrity}', suppress=True) == 0
    return ok

def _msg_fuzz_fail():
    log('\nFor failing fuzz tets, you should debug with a small sample file to see how your output is different!')
    log('For example, try running the ./io300_test command for that test, and use the -i option to specify a test file.')
    log('Also, if there is sanitizer output, that\'s a good place to start.')


def _msg_e2e_fail():
    log('\nFor failing end-to-end tests, you should debug with a small sample file to see how your output is different!')
    log('For example, try running the command for the test using a small file as the input file.')
    log('To see what each test does, look at the code for the test in the `test_programs` directory')
    log('Also, if there is sanitizer output, that\'s a good place to start.')

TESTS_ORDER = ["regression", "end-to-end", "fuzz"]

def run(test_group="all", seed=-1,
        grader_mode=False, results=None,
        try_tmpfs=False,
        fuzz_test_repeats=defaults.FUZZ_TEST_REPEATS):

    global GRADER_MODE
    global TEST_FILE_PREFIX

    if grader_mode:
        GRADER_MODE = True

    # Random seed
    if seed != -1:
        # User provided a random seed
        rand_seeds = [seed]
    else:
        # Otherwise, generate random seeds to use for all unit tests
        rand_seeds = [random.randint(0, 2 ** 32)
                     for _ in range(fuzz_test_repeats)]

    using_tmpfs = False
    if try_tmpfs:
        using_tmpfs = util.tmpfs_try_setup(util.TMPFS_PREFIX)
        if using_tmpfs:
            TEST_FILE_PREFIX = util.TMPFS_PREFIX

    if results:
        results.add_extra("seed", rand_seeds)
        results.add_extra("tmpfs", using_tmpfs)

    all_fuzz = {
        'basic_readc': FuzzTest("readc", rand_seeds),
        'basic_writec': FuzzTest("writec", rand_seeds),
        'complex_readc_writec': FuzzTest("readc writec", rand_seeds),
        'complex_readc_writec_seek': FuzzTest("readc writec seek", rand_seeds),
        'basic_read': FuzzTest("read=17", rand_seeds),
        'basic_read_random_amounts': FuzzTest("read", rand_seeds, file_size=4129),
        'basic_write': FuzzTest("write=17", rand_seeds),
        'basic_write_random_amounts': FuzzTest("write", rand_seeds, file_size=4129),
        'complex_read_write': FuzzTest("read write", rand_seeds),
        'complex_read_write_seek': FuzzTest("read write seek", rand_seeds),
        'complex_seek_beyond_eof': FuzzTest("readc writec seek", rand_seeds, file_size=0, max_file_size=4096, num_ops=1000),
        'complex_all_read_write': FuzzTest("readc writec read write", rand_seeds),
        'complex_all_operations': FuzzTest("readc writec read write seek", rand_seeds),
    }

    all_e2e = {
        'byte_cat': TestByteCat(),
        #'diabolical_byte_cat': TestDiabolicalByteCat(),
        'reverse_byte_cat': TestReverseByteCat(),
        'block_cat_1': TestBlockCat(1),
        'block_cat_32': TestBlockCat(32),
        'block_cat_17': TestBlockCat(17),
        'block_cat_334': TestBlockCat(334),
        'block_cat_huge': TestBlockCat(8192),
        'block_cat_gargantuan': TestBlockCat(32768),
        'reverse_block_cat_1': TestReverseBlockCat(1),
        'reverse_block_cat_32': TestReverseBlockCat(32),
        'reverse_block_cat_13': TestReverseBlockCat(13),
        'reverse_block_cat_987': TestReverseBlockCat(987),
        'reverse_block_cat_huge': TestReverseBlockCat(8192),
        'random_block_cat': TestRandomBlockCat(),
        'stride_cat': TestStrideCat(1, 1024),
        'rot13': TestRot13(),
    }

    all_unit = create_unit_tests()
    # unit_extra = {
    #     'extra_ascii_independence': TestBlockCat(17),
    # }
    # all_unit.update(unit_extra)

    run_all_unit = False
    run_all_e2e = False
    run_all_fuzz = False

    if test_group == "all":
        run_all_unit = True
        run_all_e2e = True
        run_all_fuzz = True
    elif test_group == "fuzz":
        run_all_fuzz = True
    elif test_group == "e2e":
        run_all_e2e = True
    elif test_group == "unit" or test_group == "regression":
        run_all_unit = True
    else:
        print(f"Unrecognized test group:  {test_group}")
        return 1

    if run_all_unit:
        log('======= (1) REGRESSION TESTS =======')
        unit_ok = runtests(all_unit, "REGRESSION",
                           results=results,
                           write_json=GRADER_MODE)


    if run_all_fuzz:
        log('======= (2) FUZZ TESTS =======')
        seed_title_str = "SEEDS" if len(rand_seeds) > 1 else "SEED"
        seed_str = str(rand_seeds) if len(rand_seeds) > 1 else str(rand_seeds[0])
        log(WARNING + f'RANDOM {seed_title_str} FOR THIS RUN: ' + seed_str + ENDC)
        fuzz_ok = runtests(all_fuzz, "FUZZ",
                           results=results,
                           write_json=GRADER_MODE)

        if not fuzz_ok:
            _msg_fuzz_fail()
            seed_arg = str(rand_seeds) if len(rand_seeds) > 1 else str(rand_seeds[0])
            log(f'Random {"seeds" if len(rand_seeds) > 1 else "seed"} for this test run was: {seed_arg}')

    if run_all_e2e:
        log('\n======= (3) END-TO-END TESTS =======')
        end_to_end_ok = runtests(all_e2e, "END-TO-END",
                                 results=results,
                                 write_json=GRADER_MODE)

        if not end_to_end_ok:
            _msg_e2e_fail()


def main(input_args):
    global GRADER_MODE
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", help="random seed",
                        type=int, default=-1)
    parser.add_argument("--grader", action="store_true")
    parser.add_argument("--fuzz-repeat", type=int, default=defaults.FUZZ_TEST_REPEATS)
    parser.add_argument("--create-tmpfs", dest="create_tmpfs", action="store_const", const=True)
    parser.add_argument("--no-create-tmpfs", dest="create_tmpfs", action="store_const", const=False)

    parser.add_argument("test_group", type=str, default="all")

    args = parser.parse_args(input_args)

    create_tmpfs = defaults.CORRECTNESS_USE_TMPFS
    if args.create_tmpfs is not None:
        create_tmpfs = args.create_tmpfs

    return run(test_group=args.test_group,
               seed=args.seed,
               try_tmpfs=create_tmpfs,
               grader_mode=args.grader,
               fuzz_test_repeats=args.fuzz_repeat)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
