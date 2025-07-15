# AI Coding Guidelines (single source of truth)

* Use Python 3.12+ with `mypy --strict`.
* Run `ruff check . && ruff format .` before every commit.
* After code changes run `pytest -q`; fix red tests immediately.
* Never commit secrets or binaries >2 MB.
* Ask before adding new runtime dependencies.

