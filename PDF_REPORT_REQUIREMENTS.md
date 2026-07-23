# PDF Report Requirements

## PDF Generation Library

The PDF report feature now uses **ReportLab** (pure Python, no external system dependencies required).

### Installation

```bash
pip install reportlab==4.2.0
```

### Why ReportLab over WeasyPrint?

- **No system dependencies** - Works on Windows, Linux, macOS without GTK/Cairo
- **Pure Python** - No need to install complex C libraries
- **Reliable** - Proven library for PDF generation in Python

### Add to requirements.txt

Add the following line to your `requirements.txt`:

```
reportlab==4.2.0
```

## Migration from WeasyPrint

If you previously had WeasyPrint installed:

```bash
# Uninstall WeasyPrint (optional, not needed anymore)
pip uninstall weasyprint

# Install ReportLab
pip install reportlab==4.2.0
```

## Features

The PDF report includes:
- Landscape A4 page layout
- Per-resource grouping
- Aging indicators (green/orange/red)
- Last action taken sub-rows
- Print-friendly formatting
- Page numbers (handled by ReportLab)
