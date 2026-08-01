# Contributing to AppSweep

Contributions are welcome through GitHub issues and pull requests.

## Development setup

Install the required Ubuntu packages:

~~~bash
sudo apt install \
  git \
  python3 \
  python3-venv \
  python3-apt \
  python3-gi \
  python3-gi-cairo \
  gir1.2-gtk-4.0 \
  gir1.2-adw-1
~~~

Create the development environment:

~~~bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install pytest ruff mypy
~~~

## Code quality

Before submitting a pull request, run:

~~~bash
ruff format src tests
ruff check src tests
pytest
~~~

## Pull requests

- Keep changes focused on one issue.
- Add tests for new behavior.
- Do not weaken package or filesystem safety checks.
- Do not add arbitrary command execution to the privileged helper.
- Update documentation when behavior changes.
- Use clear commit messages.

## Reporting bugs

Include:

- Ubuntu version
- AppSweep version
- Installation backend involved
- Exact steps to reproduce the issue
- Relevant terminal output
- Whether any package or user data was modified
