---
name: python-development
description: Python development standards for code review and generation. Covers Python 3.14+ patterns including template strings (t-strings), deferred annotations, free-threading, type hints, async/await, testing with pytest, package management with uv, AWS Lambda/boto3 patterns, and Pydantic validation. Use when working with .py files, pyproject.toml, requirements.txt, Lambda functions, or when asking about Python best practices, code review, or generation.
---

# Python Development

## Guiding Principle

Apply features only when they add clarity, correctness, performance, or security. Prefer simple, intentional solutions (DRY, KISS, YAGNI, Fail Fast).

## The Zen of Python (`import this`)

The canonical aphorisms by Tim Peters (PEP 20). When in doubt about which Python idiom to choose, re-read these. Quote verbatim; do not paraphrase in code reviews.

```text
The Zen of Python, by Tim Peters

Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.
Flat is better than nested.
Sparse is better than dense.
Readability counts.
Special cases aren't special enough to break the rules.
Although practicality beats purity.
Errors should never pass silently.
Unless explicitly silenced.
In the face of ambiguity, refuse the temptation to guess.
There should be one-- and preferably only one --obvious way to do it.
Although that way may not be obvious at first unless you're Dutch.
Now is better than never.
Although never is often better than *right* now.
If the implementation is hard to explain, it's a bad idea.
If the implementation is easy to explain, it may be a good idea.
Namespaces are one honking great idea -- let's do more of those!
```

> Run `python -c "import this"` in any Python REPL to see it.

For per-line operative readings (how to apply each in review), see the Zen section in `rules/200-python.mdc`.

## AI Assistant Guidelines

- **Avoid Over-Engineering**: Don't recommend boto3 client caching, async/await, or concurrency patterns unless explicitly requested or bottlenecks are evident
- **Keep It Simple**: Prefer stdlib over complex architectures
- **Respect Context**: Don't transform a 20-line script into a 200-line framework

## Standards Quick Reference

| Aspect | Standard |
|--------|----------|
| **Python Version** | ≥ 3.14 |
| **Shebang** | `#!/usr/bin/env -S uv run` |
| **Formatting** | 4-space indents, 120 char line length |
| **Linting** | `black`, `ruff`, `pylint` (≥9.0) |
| **Type Hints** | Strict typing required |
| **Docstrings** | Google-style |
| **Package Manager** | `uv` (preferred) |

## Type Hints

Use built-in types instead of `typing` module:

```python
# Modern Python 3.14+
def process(items: list[str], config: dict[str, int] | None = None) -> tuple[str, int]:
    ...

# Avoid (old style)
from typing import List, Dict, Optional, Tuple
def process(items: List[str], config: Optional[Dict[str, int]] = None) -> Tuple[str, int]:
    ...
```

## Python 3.14 Features (Released Oct 2025)

### Template String Literals (PEP 750)

Safe custom string processing with t-strings:

```python
# SQL query with safe parameterization
query = t"SELECT * FROM users WHERE id = {user_id}"

# HTML generation with auto-escaping
html = t"<div>{user_input}</div>"

# Custom formatting
config = t"server={host}:{port}"
```

### Deferred Annotation Evaluation (PEP 649)

Annotations are no longer evaluated eagerly, improving startup performance:

```python
# Annotations stored in __annotate__ function
# Evaluated only when inspect.get_annotations() is called
def process(data: ComplexType) -> Result:
    """Annotations evaluated lazily, not at import time."""
    ...
```

### Free-Threading Support (PEP 779)

True parallelism without the GIL (experimental):

```python
# Enable with: python3.14t (free-threaded build)
# Performance penalty reduced to 5-10% for single-threaded code
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor() as executor:
    results = executor.map(cpu_intensive_task, items)
```

### datetime Improvements

Direct parsing of date and time strings:

```python
from datetime import date, time

# Python 3.14+
d = date.fromisoformat("2025-10-07")
t = time.fromisoformat("14:30:00")
```

### UUID7 and UUID8 Support

Modern UUID versions with better properties:

```python
import uuid

# UUID7: Time-ordered, sortable (recommended for databases)
id = uuid.uuid7()

# UUID8: Custom format
id = uuid.uuid8(bytes16)
```

## Code Structure

```python
#!/usr/bin/env -S uv run
"""
Module purpose and overview.

Workflow:
1. Load configuration
2. Validate inputs
3. Process data
"""

# Standard library
import logging

# Third-party
import requests

# Local
from utils import helper


def helper_function() -> None:
    """Helper functions first."""
    pass


def main() -> int:
    """Main function last."""
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Key Patterns

### Defensive Programming

```python
# Validate inputs early (fail-fast)
def process_user(user_id: str | None) -> User:
    if user_id is None:
        raise ValueError("user_id is required")
    # Continue processing...
```

### No Mutable Defaults

```python
# BAD
def foo(items: list[str] = []):
    ...

# GOOD
def foo(items: list[str] | None = None):
    items = items or []
    ...
```

### Error Handling

```python
# Re-raise with context at boundaries
try:
    data = load_database()
except Exception as e:
    raise RuntimeError(f"Failed to load database: {e}") from e
```

### Logging Setup

```python
import logging
import time

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    class UTCFormatter(logging.Formatter):
        converter = time.gmtime
    
    handler = logging.StreamHandler()
    handler.setFormatter(UTCFormatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger

logger = setup_logger(__name__)
```

## Package Management (uv)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Project setup
uv init my-project
uv add boto3 pydantic
uv add --dev pytest black ruff
uv sync

# Run script
uv run python main.py
```

## Pydantic Validation

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    name: str
    age: int
    
    @field_validator("age")
    @classmethod
    def valid_age(cls, v: int) -> int:
        if v < 0 or v > 150:
            raise ValueError("Invalid age")
        return v
```

## Quick Checklist

- [ ] Shebang line with `uv`
- [ ] Type hints on all functions
- [ ] Google-style docstrings
- [ ] Imports grouped and sorted
- [ ] `if __name__ == "__main__":` guard
- [ ] Logging configured
- [ ] Input validation
- [ ] Specific exception handling
- [ ] `black` and `ruff` pass
- [ ] `pylint` score ≥ 9.0

## Detailed References

- **Code Quality Tools**: See [references/code-quality-tools.md](references/code-quality-tools.md) for black, ruff, isort, mypy, pylint configuration
- **Package Management**: See [references/package-management.md](references/package-management.md) for uv, isort, dependency management
- **Standard Library**: See [references/standard-library.md](references/standard-library.md) for pathlib, textwrap, contextlib, dataclasses, enum, typing, secrets, heapq, graphlib
- **Logging & Observability**: See [references/logging-observability.md](references/logging-observability.md) for logger setup, structured logging, log levels
- **Security & Validation**: See [references/security-validation.md](references/security-validation.md) for bandit, input validation, Pydantic, regex patterns
- **Error Handling**: See [references/error-handling.md](references/error-handling.md) for exception handling, retry patterns, custom exceptions
- **Performance Optimization**: See [references/performance-optimization.md](references/performance-optimization.md) for profiling, optimization examples, concurrency guide
- **Troubleshooting & Debugging**: See [references/troubleshooting-debugging.md](references/troubleshooting-debugging.md) for pdb, profiling, common issues
- **Design Patterns**: See [references/design-patterns.md](references/design-patterns.md) for decorator, factory, singleton, strategy patterns
- **CLI & User Experience**: See [references/cli-user-experience.md](references/cli-user-experience.md) for argparse, typer, rich, UX best practices
- **Modern Python Features**: See [references/modern-python.md](references/modern-python.md) for match-case, walrus operator, dataclasses, functional patterns
- **Async & Concurrency**: See [references/async-concurrency.md](references/async-concurrency.md) for asyncio, threading, multiprocessing
- **Testing Patterns**: See [references/testing-patterns.md](references/testing-patterns.md) for pytest, mocking, fixtures
- **AWS Lambda**: See [references/aws-lambda.md](references/aws-lambda.md) for boto3 patterns, Lambda best practices
- **AWS & Boto3**: See [references/aws-boto3.md](references/aws-boto3.md) for client configuration, error handling, pagination, Lambda patterns
