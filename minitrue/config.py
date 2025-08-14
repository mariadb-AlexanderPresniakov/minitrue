from __future__ import annotations

import re
from pathlib import Path
from typing import Literal
from typing import Annotated

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from .rules import PassRule, RewriteRule, Rule, SkipRule
from .types import ParsedLine


class InputFormatConfig(BaseModel):
    """Configure how to parse incoming lines and the default format for output.

    - regex: Optional named-group regex. Must include 'msg' if provided.
    - flags: Regex flags as letters: i (IGNORECASE), m (MULTILINE), s (DOTALL).
    """
    regex: str | None = Field(default=None, description="Regex with named groups (must include msg, others are free-form)")
    flags: str | None = Field(default=None, description="Regex flags as letters: i,m,s")


class OutputFormatConfig(BaseModel):
    """Configure how emitted lines are rendered when they pass."""
    format: str | None = Field(default=None, description="Output format for emitted lines")


class RuleWhen(BaseModel):
    """Condition under which a rule is applied, expressed as a regex."""
    regex: str
    flags: str | None = None


class BaseRuleConfig(BaseModel):
    when: RuleWhen
    description: str | None = Field(default=None, description="Optional human-readable description of the rule")


class SkipRuleConfig(BaseRuleConfig):
    """Skip any line that matches 'when.regex'."""
    type: Literal["skip"]


class PassRuleConfig(BaseRuleConfig):
    """Emit any line that matches 'when.regex' unchanged."""
    type: Literal["pass"]


class RewriteRuleConfig(BaseRuleConfig):
    """Rewrite message to the 'replace' template when 'when.regex' matches."""
    type: Literal["rewrite"]
    replace: str
    scope: Literal["message", "line"] | None = Field(
        default="message",
        description="Apply replacement to just the msg field ('message') or the whole line ('line')",
    )


RuleConfig = Annotated[
    SkipRuleConfig | PassRuleConfig | RewriteRuleConfig,
    Field(discriminator="type"),
]


class Config(BaseModel):
    """Top-level configuration for a minitrue run loaded from YAML."""
    description: str | None = Field(default=None, description="Optional description of this rules file")
    input: InputFormatConfig = Field(default_factory=InputFormatConfig)
    output: OutputFormatConfig = Field(default_factory=OutputFormatConfig)
    global_replace: dict[str, str] = Field(default_factory=dict, description="Map of literal replacements applied before parsing and rules")
    rules: list[RuleConfig] = Field(default_factory=list)
    unmatched: str = Field(default="pass")

    @field_validator("unmatched")
    @classmethod
    def _validate_unmatched(cls, v: str) -> str:
        if v not in {"pass", "skip"}:
            raise ValueError("'unmatched' must be either 'pass' or 'skip'")
        return v

    def compile_rules(self) -> list[Rule]:
        compiled: list[Rule] = []
        for rc in self.rules:
            flags = _parse_flags(rc.when.flags)
            pattern = re.compile(rc.when.regex, flags)
            if isinstance(rc, SkipRuleConfig):
                compiled.append(SkipRule(pattern=pattern))
            elif isinstance(rc, PassRuleConfig):
                compiled.append(PassRule(pattern=pattern))
            elif isinstance(rc, RewriteRuleConfig):
                # When matched, the message becomes the provided template rendered with input fields
                compiled.append(RewriteRule(pattern=pattern, template=rc.replace, scope=rc.scope or "message"))
        return compiled


def _parse_flags(flag_letters: str | None) -> int:
    """Translate simple flag letters into Python regex flags."""
    if not flag_letters:
        return re.MULTILINE
    flag_value = re.MULTILINE
    for ch in flag_letters:
        if ch.lower() == "i":
            flag_value |= re.IGNORECASE
        elif ch.lower() == "m":
            flag_value |= re.MULTILINE
        elif ch.lower() == "s":
            flag_value |= re.DOTALL
    return flag_value


def load_config(path: str | Path) -> Config:
    """Load YAML config from 'path' and validate into a Config model."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    try:
        return Config.model_validate(data)
    except ValidationError as e:
        # Re-raise with a cleaner message for CLI users
        raise ValueError(str(e))


def parse_line(raw_line: str, input_cfg: InputFormatConfig) -> ParsedLine:
    """Parse a raw input line using the configured input regex.

    If no regex or no match, the entire line becomes {msg} and no extra fields
    are added. Otherwise, named groups become fields and 'msg' is special.
    """
    line = raw_line.rstrip("\n")
    if not input_cfg.regex:
        return ParsedLine(fields={}, msg=line, original_line=line)

    flags = _parse_flags(input_cfg.flags)
    pattern = re.compile(input_cfg.regex, flags)
    m = pattern.search(line)
    if not m:
        return ParsedLine(fields={}, msg=line, original_line=line)

    groups = m.groupdict()
    msg_from_groups = groups.get("msg")
    msg_value: str = line if msg_from_groups is None else msg_from_groups
    msg_span = m.span("msg") if "msg" in m.re.groupindex else None
    other_fields = {k: (v or "") for k, v in groups.items() if k != "msg"}
    return ParsedLine(fields=other_fields, msg=msg_value, original_line=line, msg_span=msg_span)

