from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, Pattern
from jinja2 import Template

from .types import ParsedLine
from .jinja import compile_template

logger = logging.getLogger(__name__)

class Rule:
    """Abstract base for processing a parsed line.

    Implementations decide whether they match a line and how to act on it.
    The return from apply is (should_emit, new_parsed_line).
    """
    def matches(self, parsed_line: ParsedLine) -> Optional[re.Match]:
        raise NotImplementedError

    def apply(self, parsed_line: ParsedLine) -> tuple[bool, ParsedLine]:
        raise NotImplementedError


@dataclass
class BaseRegexRule(Rule):
    """Rule that evaluates a regular expression against the message text."""
    pattern: Pattern[str]

    def matches(self, parsed_line: ParsedLine) -> Optional[re.Match]:
        return self.pattern.search(parsed_line.msg)


@dataclass
class SkipRule(BaseRegexRule):
    """Skip any line that matches the regex."""
    def apply(self, parsed_line: ParsedLine) -> tuple[bool, ParsedLine]:
        return False, parsed_line


@dataclass
class PassRule(BaseRegexRule):
    """Pass through any line that matches the regex unchanged."""
    def apply(self, parsed_line: ParsedLine) -> tuple[bool, ParsedLine]:
        return True, parsed_line


@dataclass
class RewriteRule(BaseRegexRule):
    """Rewrite the message to the provided template if the regex matches.

    The template is rendered with:
    - fields captured by the input parser (named groups) plus {msg}
    - named groups captured by this rule's own regex applied to msg
    The rule's regex controls applicability and provides additional fields.
    """
    template: str
    scope: str = "message"  # "message" or "line"
    _compiled_template: Template = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled_template = compile_template(self.template)

    def _render_template(self, parsed_line: ParsedLine) -> str:
        """Render using input fields, msg, and this rule's match groups via Jinja2."""
        values: dict[str, str] = parsed_line.as_mapping()
        match = self.pattern.search(parsed_line.msg)
        if match is not None:
            values.update({k: (v or "") for k, v in match.groupdict().items()})
        return self._compiled_template.render(**values)

    def apply(self, parsed_line: ParsedLine) -> tuple[bool, ParsedLine]:
        """Apply rewrite based on scope.

        - message: only rewrite the msg field, keep other parts as-is
        - line: rewrite the entire line, bypassing output formatting
        """
        rendered = self._render_template(parsed_line)
        if self.scope == "line":
            return True, ParsedLine(
                fields=dict(parsed_line.fields),
                msg=parsed_line.msg,
                original_line=parsed_line.original_line,
                msg_span=parsed_line.msg_span,
                line_override=rendered,
            )
        # default: message scope — update msg and reconstruct line later during emit
        return True, ParsedLine(
            fields=dict(parsed_line.fields),
            msg=rendered,
            original_line=parsed_line.original_line,
            msg_span=parsed_line.msg_span,
        )

