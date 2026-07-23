# Supported Date Formats

## Quick Reference

The `sync_dr_full_interactive` command supports the following date formats:

### Date-Only Formats

| Format | Pattern | Example |
|--------|---------|---------|
| ISO | YYYY-MM-DD | `2025-06-15` |
| Short | DD-Mon-YYYY | `15-Jun-2025` |
| Short (2-digit year) | DD-Mon-YY | `15-Jun-25` |
| Medium | DD Mon YYYY | `15 Jun 2025` |
| Long | DD Month YYYY | `15 June 2025` |
| Reverse Long | Month DD YYYY | `June 15 2026` |

### Formats With Time

| Format | Pattern | Example |
|--------|---------|---------|
| Full AM/PM | Month DD YYYY HH:MM AM/PM | `June 15 2026 04:00 PM` |
| Full AM/PM (no space) | Month DD YYYY HH:MMAM/PM | `June 15 2026 04:00PM` |
| Abbreviated + Time | Mon DD YYYY HH:MM AM/PM | `Jan 15 2026 04:00 PM` |
| 24-hour format | Month DD YYYY HH:MM | `June 15 2026 16:00` |
| With seconds | Month DD YYYY HH:MM:SS AM/PM | `June 15 2026 04:00:00 PM` |

---

## Empty/Null Values

Use any of these to represent missing dates:

```
(empty)
none
```

Or leave the line blank.

---

## Examples by Field

### Due Date (required)
```
2025-07-15
June 30 2026 04:00 PM
15-Jul-2025
```

### Cleared Date (optional)
```
2025-06-10
(empty)
none
```

### Raised Date (optional)
```
March 20 2026 10:30 AM
2025-04-01
(empty)
```

---

## Tips

1. **Consistency**: Use the same date format throughout a file when possible
2. **Time is ignored**: When using formats with time, only the date portion is stored
3. **Case sensitivity**: Month names are case-insensitive (June, JUNE, june all work)
4. **Leading zeros**: Optional for days and hours (`04:00 PM` = `4:00 PM`)
