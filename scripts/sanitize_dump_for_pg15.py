"""
Prepare a local pg_dump (PostgreSQL 17) for import into staging's Cloud SQL
PostgreSQL 15 instance.

Two independent fixes:

1. Version portability. A PG17 dump carries statements PG15's psql rejects,
   and the whole import aborts on the first one:
     \\restrict / \\unrestrict  -- psql meta-commands added after PG15
     SET transaction_timeout   -- GUC introduced in PG17

2. Cross-environment FK links. Local `food_items.doctor_id` /
   `ingredients.added_by_doctor_id` point at local dev doctors that do not
   exist on staging, so the import dies on food_items_doctor_id_fkey. Staging
   deliberately has no doctor/patient data, and we are NOT copying local dev
   accounts into it. Same convention the curated restore dump already uses --
   db-backups/RESTORE.md describes it as "FK-clean (doctor links nulled)".
   Affected rows are doctor-private dishes, which are unverified and therefore
   outside the served pool anyway.

Everything else in a --data-only --column-inserts dump (the SETs, the INSERTs,
the sequence setvals) is portable as-is.

Usage:
    python -m scripts.sanitize_dump_for_pg15 <in.sql> <out.sql>
"""
import io
import re
import sys

DROP_PREFIXES = ("\\restrict", "\\unrestrict", "SET transaction_timeout")

# table -> columns whose values must become NULL (FKs to envs staging lacks)
NULL_COLUMNS = {
    "public.food_items": {"doctor_id"},
    "public.ingredients": {"added_by_doctor_id"},
}

INSERT_RE = re.compile(r"^INSERT INTO (\S+) \(([^)]*)\) VALUES \((.*)\);\s*$")


def split_values(s: str) -> list[str]:
    """Split a VALUES tuple on top-level commas.

    Can't use str.split(',') -- text fields contain commas, and PostgreSQL
    escapes a literal quote by doubling it ('it''s'), which must not be read
    as the end of the string.
    """
    out, buf, in_str, depth, i = [], [], False, 0, 0
    while i < len(s):
        ch = s[i]
        if in_str:
            if ch == "'":
                if i + 1 < len(s) and s[i + 1] == "'":   # escaped quote
                    buf.append("''")
                    i += 2
                    continue
                in_str = False
            buf.append(ch)
        elif ch == "'":
            in_str = True
            buf.append(ch)
        elif ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf).strip())
    return out


def null_fk_columns(line: str, stats: dict) -> str:
    m = INSERT_RE.match(line)
    if not m:
        return line
    table, collist, values = m.group(1), m.group(2), m.group(3)
    targets = NULL_COLUMNS.get(table)
    if not targets:
        return line

    cols = [c.strip() for c in collist.split(",")]
    vals = split_values(values)
    if len(cols) != len(vals):
        raise SystemExit(
            f"parse mismatch on {table}: {len(cols)} columns vs {len(vals)} values\n{line[:200]}"
        )

    changed = False
    for idx, col in enumerate(cols):
        if col in targets and vals[idx] != "NULL":
            vals[idx] = "NULL"
            stats[f"{table}.{col}"] = stats.get(f"{table}.{col}", 0) + 1
            changed = True
    if not changed:
        return line
    return f"INSERT INTO {table} ({collist}) VALUES ({', '.join(vals)});\n"


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]

    dropped, kept, stats = [], 0, {}
    with io.open(src, encoding="utf-8") as f, \
            io.open(dst, "w", encoding="utf-8", newline="\n") as out:
        for line in f:
            if line.lstrip().startswith(DROP_PREFIXES):
                dropped.append(line.strip()[:60])
                continue
            out.write(null_fk_columns(line, stats))
            kept += 1

    print(f"kept {kept} lines, dropped {len(dropped)} PG17-only statements:")
    for d in dropped:
        print(f"  - {d}")
    print("nulled cross-environment FK links:")
    for k, v in sorted(stats.items()) or [("(none)", 0)]:
        print(f"  - {k}: {v} row(s)")
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
