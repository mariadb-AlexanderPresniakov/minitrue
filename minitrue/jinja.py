from __future__ import annotations

from jinja2 import Environment, StrictUndefined, Template

"""Jinja2 environment and helpers used across minitrue.

The environment is created once at import time and reused to avoid per-line
construction overhead during rewriting.
"""

# Singleton environment reused across the process
JINJA_ENV: Environment = Environment(undefined=StrictUndefined, autoescape=False)


def compile_template(source: str) -> Template:
    """Compile a Jinja2 template from a string.
    """
    return JINJA_ENV.from_string(source)

