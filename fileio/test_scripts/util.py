import re
import os
import sys
import json
import argparse
import tempfile
import subprocess

from dataclasses import dataclass, field

HEADER = "\033[95m"
OKBLUE = "\033[94m"
OKCYAN = "\033[96m"
OKGREEN = "\033[92m"
WARNING = "\033[93m"
FAIL = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
OKGREENBOLD = "\033[32;1m"
FAILBOLD = "\033[31;1m"

TMPFS_PREFIX = "/tmp/io300"

def make_impl_check_msg(impls_seen):
    msg = ""
    if len(impls_seen) == 0:
        # Couldn't gather any info, just return
        pass
    elif len(impls_seen) == 1:
        impl = list(impls_seen)[0]
        msg = f"{FAIL if impl != 'student' else ENDC}Implementation tested:  {impl}{ENDC}"
    else:
        msg = FAIL + f"WARNING WARNING WARNING:  Test used programs that from multiple implementations ({impls_seen})" + \
            ", run 'make clean' and try again" + ENDC

    return msg


def dir_is_tmpfs(dir: str):
    chk = subprocess.check_output("mount | grep {} || true".format(dir), shell=True, text=True)
    if "tmpfs" in chk:
        return True
    else:
        return False


def tmpfs_warning_str():
    return WARNING + "WARNING:  Unable to set up tmpfs directory for performance tests." + \
        "Performance results may be inaccurate, please verify on grading server." + ENDC


def tmpfs_do_setup(prefix: str):
    def _run(cmd):
        subprocess.check_output(cmd, shell=True)

    _run("mkdir -p {}".format(prefix))
    _run("sudo mount -t tmpfs none {}".format(prefix))


def tmpfs_try_setup(prefix: str):
    ok = False
    try:
        ok = dir_is_tmpfs(prefix);

        if not ok:
            tmpfs_do_setup(prefix)
            ok = dir_is_tmpfs(prefix)
    except Exception:
        print(tmpfs_warning_str())
        ok = False

    return ok


@dataclass
class Test:
    name: str
    group: str
    status: str
    output: str = ""

    STATUS_PASS = "passed"
    STATUS_FAIL = "failed"

    def is_passing(self):
        return self.status == self.STATUS_PASS

    def to_json(self):
        d = {
            "name": self.name,
            "status": self.status,
            "output": self.output,
            "extra": {
                "group": self.group,
            }
        }
        return d

@dataclass
class TestResults:
    tests: list[Test] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def add_test(self, name: str, group: str, is_pass: bool,
                 output=""):
        status = Test.STATUS_PASS if is_pass else Test.STATUS_FAIL
        test_name = "{}_{}".format(group, name)
        self.tests.append(Test(test_name, group, status, output))

    def add_extra(self, key, value):
        self.extra[key] = value


    def show_summary(self, group_print_order=None, impls_seen=None):
        groups_present = list(set([x.group for x in self.tests]))

        if group_print_order is None:
            _print_order = groups_present
        else:
            _print_order = [x for x in group_print_order if x in groups_present]


        print("\n====================== OVERALL TEST SUMMARY =======================")
        if impls_seen is not None:
            print(make_impl_check_msg(impls_seen))

        if "fuzz" in _print_order and "seed" in self.extra:
            seed_list = self.extra["seed"]
            seed_arg = seed_list if len(seed_list) > 1 else seed_list[0]
            print("{}random {} for fuzz tests: {}{}".format(WARNING,
                                                            "seeds" if len(seed_list) > 1 else "seed",
                                                            seed_arg, ENDC))

        rows = []
        def _make_row(group_name):
            tests_in_group = [t for t in self.tests if t.group == group_name]
            passing = len([t for t in tests_in_group if
                           t.is_passing()])
            total = len(tests_in_group)
            failing = total - passing
            count_str = BOLD + "passed {} of {} tests".format(passing, total) + ENDC
            result_str = "{}{}{}".format(OKGREENBOLD if failing == 0 else FAILBOLD,
                                           "PASSED" if failing == 0
                                           else "FAILED", ENDC)
            row = (BOLD + group_name.lower() + " tests" + ENDC, count_str, result_str)
            return row

        for group in _print_order:
            rows.append(_make_row(group))

        def _hr():
            return "|" + "-"*22 + "|" + "-"*32 + "|" + ("-"*9) + "|"

        headers = ["Test group", "Results", "Status"]
        print("\n| {:28s} | {:38s} | {:15s} |".format(*[BOLD + x + ENDC for x in headers]))
        print(_hr())
        for row in rows:
            print("| {:28s} | {:38s} | {:18s} |".format(*row))
            if len(rows) > 1:
                print(_hr())

    def to_json(self):
        d = {
            "tests": [t.to_json() for t in self.tests],
            "extra": self.extra,
        }
        return d

    def write_json(self, out_file):
        with open(str(out_file), "w") as fd:
            json.dump(self.to_json(), fd,
                      indent=2)


