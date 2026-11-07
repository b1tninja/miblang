"""Command line entry point for miblang.

The CLI is how most people meet a protocol library, so it is part of the public surface and
gets the same typing and testing discipline as the rest of the package.
"""

from __future__ import annotations

import argparse
import sys

USAGE = """\
Examples:
  miblang resolve IF-MIB::ifPhysAddress --prove"""


def build_parser():
    return argparse.ArgumentParser(
        prog="miblang",
        description="Parses SMIv2 MIB modules into an OID-addressed object tree: the macro forms, the RFC 2579 textual conventions, RFC 2580 conformance statements, and the ITU-T formal-description catalogue as a digest-pinned module source",
        epilog=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


def main(argv=None):
    """Parse arguments, then refuse to pretend the protocol works.

    Exiting non-zero is the correct behaviour for a shell. A CLI that printed a friendly
    banner and exited 0 would be indistinguishable from one that actually did something.
    """
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_usage(sys.stderr)
    print("miblang: no protocol behaviour is implemented yet; see ROADMAP.md", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
