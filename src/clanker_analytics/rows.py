"""Loading Python rows into DuckDB tables."""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
import tempfile
from typing import Iterable, Sequence

import duckdb


def insert_rows(db: duckdb.DuckDBPyConnection, table: str, rows: Iterable[Sequence]) -> None:
    """Append rows, in the table's column order, through a JSON Lines file.

    DuckDB's executemany and bound lists convert each value through Python and try to
    import pandas for each one, which costs seconds per hundred thousand values when
    pandas is not installed; reading a file costs a fraction of a second.
    """
    columns = db.execute(f"DESCRIBE {table}").fetchall()
    names = [column[0] for column in columns]
    spec = ", ".join("'" + name.replace("'", "''") + "': '" + kind + "'" for name, kind, *_ in columns)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "rows.jsonl"
        with path.open("w") as stream:
            for row in rows:
                stream.write(json.dumps(dict(zip(names, row)), default=_json_value) + "\n")
        db.execute(f"INSERT INTO {table} SELECT * FROM read_json(?, format = 'newline_delimited', "
                   f"columns = {{{spec}}})", [path.as_posix()])


def _json_value(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    raise TypeError(f"cannot store {type(value).__name__} in a row")
