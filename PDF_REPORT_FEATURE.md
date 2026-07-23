# PDF Report Feature - Implementation Summary

## Overview
A PDF report generation feature for DRs by Severity & Type, with filtering, grouping, and aging indicators.

## Files Created

### 1. View Function
**File**: [apps/deficiencies/views_report.py](apps/deficiencies/views_report.py)

Functions:
- `get_aging_bucket(dr)` - Returns aging color based on `raised_date`
  - Green: < 30 days
  - Orange: 30-90 days
  - Red: > 90 days
  - Gray: No raised date

- `get_last_action(dr)` - Returns tuple of (date, note) from last action in `actiontaken`

- `dr_report_pdf_view(request)` - Main PDF generation view
  - Query params: `site`, `severity`, `resource`, `date_from`, `date_to`, `download`
  - Filters Deficiencies by params
  - Groups by Resource (aircraft type)
  - Renders HTML and converts to PDF via WeasyPrint
  - Supports inline view or download

### 2. Template
**File**: [templates/deficiencies/dr_report.html](templates/deficiencies/dr_report.html)

Features:
- Landscape A4 page layout with page numbers
- Company logo area (SimEye)
- Centered title "DRs by Severity & Type"
- Eastern timezone timestamp
- Color legend for aging buckets
- Per-resource tables with columns:
  - DR # (with colored aging indicator)
  - Description
  - Raised By
  - Raised Date
  - Assigned To
  - Status
  - Severity
  - Due Date
  - Resource
- Sub-row for "Last Action Taken"
- Print-friendly beige/tan table headers
- Total records footer

### 3. URL Route
**File**: [apps/deficiencies/urls.py](apps/deficiencies/urls.py)

```python
path('deficiencies/report/pdf/', views_report.dr_report_pdf_view, name='report_pdf'),
```

### 4. UI Integration
**File**: [templates/deficiencies/list.html](templates/deficiencies/list.html)

Added a "Generate Report" button with a modal for:
- Site selection
- Severity selection
- Resource/Aircraft Type selection
- Date range (from/to)

## Usage

### Generate Report from UI
1. Navigate to Deficiencies list page
2. Click "Generate Report" button
3. Select filters in the modal
4. Click "Generate PDF"

### Direct URL Access
```
/deficiencies/report/pdf/?site=Site1&severity=A&resource=Resource1&date_from=2024-01-01&date_to=2024-12-31
```

### Download vs View
- Default: Opens in browser/inline
- Add `?download=1` to prompt download

## Dependencies

### Required Package
```bash
pip install reportlab==4.2.0
```

**ReportLab** is a pure Python library - no system dependencies required!

See [PDF_REPORT_REQUIREMENTS.md](PDF_REPORT_REQUIREMENTS.md) for installation instructions.

## Real Field Names Used

| Purpose | Field Name |
|----------|-----------|
| DR # | `deficiency_number` |
| Site | `site_name` |
| Resource | `resource` |
| Description | `issue_description` |
| Raised By | `raised_by_name` |
| Raised Date | `raised_date` |
| Assigned To | `assignee_name` |
| Status | `status` |
| Severity | `severity` |
| Due Date | `due_date` |
| Deficiency Type | `deficiency_type` |
| Actions | `actiontaken` (parsed via `parsed_actions` property) |

## Aging Calculation

Aging is computed as: `(today - raised_date)` in days

- **Green**: < 30 days
- **Orange**: 30-90 days
- **Red**: > 90 days

## PDF Layout

```
+------------------------------------------+
| Logo            DRs by Severity & Type    |
|                Printed On: ... (Eastern)  |
|                Site: ... | Severity: ...  |
|  [< 30 Days] [30-90 Days] [> 90 Days]  |
+------------------------------------------+
| Resource Group Header                     |
+------------------------------------------+
| DR# | Description | Raised By | ...      |
| [■] | ...          | ...        | ...      |
| Last Action Taken: [date] - note          |
+------------------------------------------+
```

## Notes

- Groups records by **Resource** (aircraft type)
- No new models created - uses existing `Deficiency` model
- `sub_status_name` field exists but excluded from report per requirements
- Uses `parsed_actions` model property to get last action
- Timezone conversion to US/Eastern for display
