# Run all checks (lint + typecheck + test)
check: lint typecheck test

# Run tests with coverage
test *args:
    uv run pytest {{args}}

# Run ruff linter and formatter check
lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/

# Auto-fix lint and formatting issues
fix:
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

# Run type checker
typecheck:
    uv run ty check src/

# Install/sync dependencies
sync:
    uv sync
