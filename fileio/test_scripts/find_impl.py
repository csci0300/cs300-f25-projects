#!/usr/bin/env python3
#
# Try to guess the I/O library implementation for a given program
# Usage:
#    test_scripts/find_impl.py <program name>
#

import sys
import pathlib
import argparse
import subprocess


def try_find_impl(bin_path: str):
    impl_name = None

    # If any error occurs, finding the implementation is more complicated than we can handle,
    # so just return None
    try:
        out = subprocess.check_output(f"objdump -W {bin_path} | grep DW_AT_name | grep 'impl/'",
                                      text=True, shell=True)

        tokens = out.strip().split(" ")
        filename = tokens[-1]
        assert("impl" in filename)
        file_path = pathlib.Path(filename)
        impl_name = file_path.stem
    except Exception as e:
        pass

    return impl_name


def main(input_args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true",
                        help="Print nothing and exit silently on error")
    parser.add_argument("program")

    args = parser.parse_args(input_args)

    impl = try_find_impl(args.program)
    if impl is None:
        print("Unable to detect implementation")
        return 1
    else:
        print(impl)
        return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
