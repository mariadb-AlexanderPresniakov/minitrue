from __future__ import annotations

from dataclasses import dataclass
from typing import TextIO

from .config import Config, parse_line
from .rules import Rule
from .types import ParsedLine


@dataclass
class Processor:
    config: Config
    compiled_rules: list[Rule]

    def process_stream(self, src: TextIO, dst: TextIO) -> None:
        for line_number, raw_line in enumerate(src, start=1):
            replaced_line = self._apply_global_replacements(raw_line)
            parsed = parse_line(replaced_line, self.config.input)
            # Inject original line number into fields for templates
            parsed.fields = dict(parsed.fields)
            parsed.fields["line_no"] = str(line_number)
            handled = False
            for rule in self.compiled_rules:
                m = rule.matches(parsed)
                if m:
                    should_print, new_parsed = rule.apply(parsed)
                    if should_print:
                        self._emit(new_parsed, dst)
                    handled = True
                    break
            if not handled:
                if self.config.unmatched == "pass":
                    self._emit(parsed, dst)

    def _emit(self, parsed: ParsedLine, dst: TextIO) -> None:
        if parsed.line_override is not None:
            dst.write(parsed.line_override + "\n")
            return
        fmt = self.config.output.format
        if fmt:
            mapping = parsed.as_mapping()
            try:
                dst.write(fmt.format(**mapping) + "\n")
            except Exception:
                dst.write(parsed.msg + "\n")
        else:
            # No output.format: write original line or reconstructed message-only rewrite
            if parsed.msg_span is not None and parsed.msg != parsed.original_line[parsed.msg_span[0]:parsed.msg_span[1]]:
                start, end = parsed.msg_span
                dst.write(parsed.original_line[:start] + parsed.msg + parsed.original_line[end:] + "\n")
            else:
                dst.write(parsed.original_line + "\n")

    def _apply_global_replacements(self, raw_line: str) -> str:
        line_no_nl = raw_line.rstrip("\n")
        for what, with_what in self.config.global_replace.items():
            if what:
                line_no_nl = line_no_nl.replace(what, with_what)
        return line_no_nl + ("\n" if raw_line.endswith("\n") else "")
