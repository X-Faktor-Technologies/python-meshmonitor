# Contributing

## Development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/python -m pip install build
.venv/bin/python -m build
```

Keep deterministic tests free of real tokens, node identities, coordinates, and
message content. Live tests are opt-in through environment variables and must
never write to a mesh unless a test explicitly documents and gates that action.

Public methods require type annotations and concise docstrings describing API
semantics or safety constraints. Comments should explain non-obvious protocol
behavior, not restate the code.

Before opening a pull request, run all checks above. The final two commands
install the standard build frontend into the isolated development environment
and build the wheel and source distribution.
