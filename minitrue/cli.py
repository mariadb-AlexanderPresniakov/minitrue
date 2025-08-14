from __future__ import annotations

import argparse
import logging
import sys

from .config import Config, load_config
from .processor import Processor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="minitrue", description="Rewrite lines using YAML rules.")
    parser.add_argument("rules", type=str, help="Path to YAML rules file")
    parser.add_argument("input", type=str, nargs="?", default="-", help="Input file path or '-' for stdin")
    parser.add_argument("-o", "--output", type=str, default="-", help="Output file path or '-' for stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    cfg: Config = load_config(args.rules)
    processor = Processor(config=cfg, compiled_rules=cfg.compile_rules())

    if args.input == "-":
        src = sys.stdin
    else:
        src = open(args.input, "r", encoding="utf-8")

    if args.output == "-":
        dst = sys.stdout
    else:
        dst = open(args.output, "w", encoding="utf-8")

    try:
        processor.process_stream(src, dst)
        return 0
    finally:
        if src is not sys.stdin:
            src.close()
        if dst is not sys.stdout:
            dst.close()


if __name__ == "__main__":
    raise SystemExit(main())

