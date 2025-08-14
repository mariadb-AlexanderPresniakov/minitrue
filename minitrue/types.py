from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParsedLine:
    """Container for a parsed input line.

    - fields: arbitrary key/value pairs extracted by the input regex (named groups)
    - msg: the primary message string, either captured or the whole line
    """
    fields: dict[str, str]
    msg: str
    # Original raw line as read (without trailing newline)
    original_line: str
    # Span of the 'msg' capture within original_line, if available
    msg_span: tuple[int, int] | None = None
    # When set, emission should bypass formatting and print this exact line
    line_override: str | None = None

    def as_mapping(self) -> dict[str, str]:
        """Return a mapping suitable for string formatting templates."""
        mapping: dict[str, str] = dict(self.fields)
        mapping["msg"] = self.msg
        return mapping

