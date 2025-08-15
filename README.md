# minitrue
Rules-driven line rewriter
====================================
A flexible CLI tool that processes text files using declarative YAML rules. It can skip, pass, or rewrite log lines — based on patterns you define — just like a miniature Ministry of Truth

Minitrue reads lines from a file or stdin, applies YAML-configured rules to skip, pass, or rewrite lines, and writes to a file or stdout.

Install
-------

Use Poetry:

```bash
poetry install
```

Usage
-----

```bash
minitrue rules.yml input.txt -o output.txt
```

Rules file format
-----------------

```yaml
unmatched: pass   # or "skip". If the line is not matched by any rule, do we pass it through or skip it?

description: "My service logs normalization rules"

global_replace:
  # Optional global string replacements to apply to each line before parsing and rules.
  "192.168.1.2": "host1"

input:
  # Optional parser with named groups. Only "msg" is special; anything else is user-defined. All the groups are available to the rules.
  # If this is not provided, the entire line becomes {msg} and no extra fields are added.
  regex: ^(?P<dt>\d{2}/[A-Za-z]{3}/\d{4} \d{2}:\d{2}:\d{2}) \[(?P<level>[^\]]+)\] \((?P<logger>[^\)]+)\) \{(?P<actor>[^}]+)\} (?P<msg>.*)$
  flags: i  # optional: i,m,s

output:
  # Optional output format for emitted lines
  format: "{dt} [{level}] {msg}"

rules:
  - type: skip
    description: Drop noisy debug lines
    when:
      regex: \[DEBUG\]
      flags: i

  - type: pass
    description: Allow OK lines through
    enabled: false  # Simple way to disable a rule without removing it from the file
    when:
      regex: ^OK

  - type: rewrite
    description: Rewrite the request message
    when:
      regex: 'Got incoming (?P<method>PUT|GET|POST|DELETE|PATCH|OPTIONS|HEAD) request from \"(?P<ip>[\d\.]+)\" to \"(?P<url>.+?)\". uid: (?P<req_uid>[a-f0-9-]+)'
    # 'replace' provides the full new message. Jinja2 is used for templating.
    # Placeholders include:
    # - msg from the input line
    # - named groups from input regex (e.g., dt, level)
    # - named groups captured by this rewrite rule's own regex applied to msg (e.g., ip)
    # - line_no -- the line number in the input file
    replace: "{{ ip }} --> {{ method }} {{ url }}"
    # optional rewrite scope:
    # scope: message (default value) -- rewrites {msg} only
    # scope: line -- replaces the whole line bypassing output.format
    scope: message

header: "# BEGIN"  # Optional Jinja header section that will be written before the first line is processed
footer: "# END"  # Optional Jinja footer section that will be written after the last line is processed
```

- If `input.regex` is omitted, the entire line is passed to the rules as `{msg}`.
- Rewrite templates and `output.format` can reference `{msg}` and any other named groups captured by `input.regex` (e.g. {dt}, {logger}, etc)
- `output.format` controls how final lines are printed for pass and unmatched-pass cases. Also it provides a default format for rewrite rules (aside from {msg}).
- Optional top-level `description` lets you document the ruleset.
- Optional top-level `global_replace` applies literal string replacements to each line before parsing and rules.
- Each rule can be disabled by setting `enabled: false`.
