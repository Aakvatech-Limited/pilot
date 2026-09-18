from __future__ import annotations

import json
import subprocess
import sys
import typing
from pathlib import Path

from pilot.core.app.validator.base import python_files
from pilot.exceptions import AppValidationError

if typing.TYPE_CHECKING:
    from pilot.core.app import App


class SyntaxCheck:
    """Ast-parses every Python file in the app, rejecting it on any SyntaxError."""

    def run(self, app: "App") -> None:
        broken = [
            f"{path.relative_to(app.path)}: {error}"
            for path in python_files(app)
            for error in self._syntax_errors(path)
        ]
        if broken:
            raise AppValidationError(
                f"'{app.config.name}' has Python syntax errors:\n" + "\n".join(f"  {b}" for b in broken)
            )

    @staticmethod
    def _get_python_bin(app: "App") -> str:
        """Returns the path to the bench's Python binary, falling back to the current Pilot Python executable."""
        bench = getattr(app, "bench", None)
        if bench and hasattr(bench, "env_path") and bench.env_path:
            bench_python = Path(bench.env_path) / "bin" / "python"
            if bench_python.exists():
                return str(bench_python)
        return sys.executable

    @staticmethod
    def _check_syntax_in_env(files: list[str], python_bin: str) -> dict[str, str]:
        """Runs ast.parse across all files in a single subprocess using the target bench Python runner."""
        script = """
import ast
import json
import sys

try:
    files = json.load(sys.stdin)
except Exception as e:
    sys.stderr.write(f"Failed to read input files: {e}")
    sys.exit(1)

errors = {}
for file_path in files:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            ast.parse(f.read(), filename=file_path)
    except SyntaxError as exc:
        errors[file_path] = f"line {exc.lineno}: {exc.msg}"
    except OSError:
        pass

print(json.dumps(errors))
"""
        cmd = [python_bin, "-c", script]
        try:
            ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as exc:
            return [f"line {exc.lineno}: {exc.msg}"]
        except OSError:
            return []
        return []
