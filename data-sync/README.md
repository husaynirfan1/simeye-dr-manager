# Data Sync Guide

This directory contains data files for syncing deficiency records to the database using the Django management command `sync_dr_full_interactive`.

## Management Command

### Command Syntax

```bash
python manage.py sync_dr_full_interactive \
    --numbers <path> \
    --cleared <path> \
    --due <path> \
    --statuses <path> \
    [--raised <path>]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--numbers` | Yes | Path to DR numbers file |
| `--cleared` | Yes | Path to cleared dates file |
| `--due` | Yes | Path to due dates file |
| `--statuses` | Yes | Path to statuses file |
| `--raised` | No | Path to raised dates file (optional) |
| `--update-all` | No | Update ALL records with same DR number |

---

## File Format Guidelines

All files must have the **same number of lines** (one line per record).

### Supported Date Formats

| Format | Example | Description |
|--------|---------|-------------|
| YYYY-MM-DD | `2025-01-15` | ISO format |
| DD-Mon-YYYY | `15-Jan-2025` | Day, abbreviated month, year |
| DD Month YYYY | `15 January 2025` | Day, full month name, year |
| Month DD YYYY HH:MM AM/PM | `June 15 2026 04:00 PM` | Full format with time |

### Empty Values

Use any of these to represent empty/null values:
- `(empty)`
- `none`
- Empty line

---

## File Templates

### 1. DR Numbers File (`number.txt`)

```
<start>
12345
23456
34567
<end>
```

### 2. Statuses File (`status.txt`)

```
<start>
Open
Closed
In Progress
<end>
```

### 3. Due Dates File (`due_dates_example.txt`)

```
<start>
2025-06-30
2025-07-15
June 15 2026 04:00 PM
<end>
```

### 4. Cleared Dates File (`cleared.txt`)

```
<start>
2025-05-01
(empty)
2025-06-10
<end>
```

### 5. Raised Dates File (`raised_date.txt`) - Optional

```
<start>
2025-04-01
March 20 2026 10:30 AM
(empty)
<end>
```

---

## File Structure Rules

1. **Start/End Markers**: Wrap data in `<start>` and `<end>` tags
2. **Comments**: Lines starting with `#` are ignored
3. **Line Order**: Line N in all files corresponds to the same record
4. **Empty Values**: Use `(empty)`, `none`, or blank line

---

## Example Usage

### Basic sync (without raised dates)

```bash
python manage.py sync_dr_full_interactive \
    --numbers data-sync/number.txt \
    --cleared data-sync/cleared.txt \
    --due data-sync/due_dates_example.txt \
    --statuses data-sync/status.txt
```

### With raised dates

```bash
python manage.py sync_dr_full_interactive \
    --numbers data-sync/number.txt \
    --cleared data-sync/cleared.txt \
    --due data-sync/due_dates_example.txt \
    --statuses data-sync/status.txt \
    --raised data-sync/raised_date.txt
```

### Update all records with same DR number

```bash
python manage.py sync_dr_full_interactive \
    --numbers data-sync/number.txt \
    --cleared data-sync/cleared.txt \
    --due data-sync/due_dates_example.txt \
    --statuses data-sync/status.txt \
    --raised data-sync/raised_date.txt \
    --update-all
```

---

## Processing Modes

The command offers two processing modes:

1. **Auto + Interactive**: Processes records with changes first automatically, then reviews remaining records interactively
2. **Interactive Only**: Reviews all records one by one in original order

---

## Common Issues

| Issue | Solution |
|-------|----------|
| File length mismatch | Ensure all files have the same number of data lines |
| Invalid date format | Use one of the supported date formats listed above |
| DR not found in database | The DR number doesn't exist - check your input |
| Multiple resources found | Use `--update-all` to update all matching records |

---

## Logging

The command creates a `log.txt` file in the project root with detailed operation logs.
