"""
Docker-secrets style ``<NAME>_FILE`` support.

When ``<NAME>_FILE`` is set, the value of ``<NAME>`` is read from the file it
points to instead of from the environment. ``<NAME>_FILE`` wins when both are
set. One trailing newline is stripped. An unreadable or empty file is an error
that names the variable and the path, never the value.
"""

import os

FILE_SUFFIX = "_FILE"


def read_secret_file(file_var: str, path: str) -> str:
    """Read a secret from ``path``, which was given in the ``file_var`` variable."""
    try:
        with open(path, encoding="utf-8") as f:
            value = f.read()
    except (OSError, UnicodeDecodeError) as e:
        reason = (
            e.strerror if isinstance(e, OSError) and e.strerror else type(e).__name__
        )
        raise ValueError(
            f"{file_var}: cannot read secret file {path!r}: {reason}"
        ) from None

    if value.endswith("\r\n"):
        value = value[:-2]
    elif value.endswith("\n"):
        value = value[:-1]

    if not value:
        raise ValueError(f"{file_var}: secret file {path!r} is empty")
    return value


def getenv_or_file(name: str) -> str | None:
    """
    Return the value of ``name``, honouring ``<name>_FILE``.

    ``<name>_FILE`` wins over ``<name>``. An empty ``<name>_FILE`` is treated as
    unset. Returns ``None`` when neither is set.
    """
    file_var = f"{name}{FILE_SUFFIX}"
    path = os.environ.get(file_var)
    if path:
        return read_secret_file(file_var, path)
    return os.environ.get(name)
