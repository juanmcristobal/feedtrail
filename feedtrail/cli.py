"""Command line interface for feedtrail."""

import argparse
import json
import sys

from feedtrail.feed_parser import FeedParser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="feedtrail",
        description="Parse RSS/Atom feed XML from stdin and print JSON.",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Base URL used to resolve relative links.",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    xml_content = sys.stdin.read()
    parsed = FeedParser().parse(xml_content, base_url=args.base_url)
    json.dump(parsed, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
