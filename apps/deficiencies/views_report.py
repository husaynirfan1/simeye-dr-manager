"""
PDF Report Views for Deficiency Reporting
Using ReportLab
"""
import re
import pytz
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from .models import Deficiency

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, inch
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
        PageBreak, KeepTogether
    )
    from reportlab.pdfgen import canvas
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def strip_html_tags(text):
    """Remove HTML tags from text"""
    if not text:
        return text
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def get_aging_bucket(dr):
    """
    Calculate aging bucket based on raised_date.
    Returns: 'green' (< 30 days), 'orange' (30-90 days), 'red' (> 90 days)
    """
    if not dr.raised_date:
        return 'gray'

    today = timezone.now().date()
    raised = dr.raised_date

    if isinstance(raised, str):
        try:
            raised = datetime.strptime(raised, '%Y-%m-%d').date()
        except (ValueError, AttributeError):
            return 'gray'

    days_open = (today - raised).days

    if days_open < 30:
        return 'green'
    elif 30 <= days_open <= 90:
        return 'orange'
    else:
        return 'red'


def get_last_action(dr):
    """
    Get the last action taken from the parsed_actions list.
    Returns tuple: (date_string, note) or (None, None)
    """
    actions = getattr(dr, 'parsed_actions', None)
    if actions:
        last = actions[-1]
        return (last.get('timestamp'), last.get('description'))
    return (None, None)


def get_aging_color(aging):
    """Return ReportLab color for aging bucket matching the visual"""
    colors_map = {
        'green': colors.HexColor('#b5e6a1'),  # Light green 
        'orange': colors.HexColor('#ff9900'), # Orange
        'red': colors.HexColor('#ff0000'),    # Solid Red
        'gray': colors.HexColor('#d1d5db'),
    }
    return colors_map.get(aging, colors.gray)


AIRCRAFT_MANUFACTURER_MAP = {
    'AW139': 'Agusta Westland',
    'AW189': 'Agusta Westland',
    'AW169': 'Agusta Westland',
    'H145': 'Airbus',
    'H175': 'Airbus',
    'S92': 'Sikorsky',
}


def get_configuration_label(dr):
    """
    Build the bracketed configuration label, e.g. "[Agusta Westland AW139]".
    """
    resource = (getattr(dr, 'resource', '') or '').strip()
    if not resource:
        return '-'
    manufacturer = getattr(dr, 'manufacturer', None) or AIRCRAFT_MANUFACTURER_MAP.get(resource)
    if manufacturer:
        return f"[{manufacturer}\n{resource}]"
    return f"[{resource}]"


class PDFBuilder:
    """Helper class to build PDF with ReportLab"""

    def __init__(self, buffer, context):
        self.buffer = buffer
        self.context = context
        self.story = []
        self.width, self.height = landscape(A4)

        self.doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=10*mm,
        )

        self.styles = getSampleStyleSheet()
        self.styles['Normal'].fontSize = 8
        self._add_custom_styles()

    def _add_custom_styles(self):
        """Add custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=2,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.black,
        ))
        self.styles.add(ParagraphStyle(
            name='ResourceHeader',
            parent=self.styles['Heading2'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=2,
        ))
        self.styles.add(ParagraphStyle(
            name='ActionRow',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.black,
            leftIndent=0,
        ))
        self.styles.add(ParagraphStyle(
            name='ConfigLink',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=TA_RIGHT,
        ))
        self.styles.add(ParagraphStyle(
            name='CenteredNormal',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            name='LogoFallback',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#001b44'),
            fontName='Helvetica-Bold'
        ))

    def _get_logo(self):
        """Get company logo from PNG file or fallback"""
        try:
            from pathlib import Path
            from reportlab.platypus import Image
            
            logo_path = Path('static/icons/simeye.png')
            if logo_path.exists():
                # Load the PNG and scale it to 30x30 mm
                return Image(str(logo_path), width=30*mm, height=30*mm)
        except Exception:
            pass
            
        return Paragraph("SimEye", self.styles['LogoFallback'])

    def build_header(self):
        """Build document header with logo and subtitles"""
        
        # Header top row: Logo and title
        header_data = [
            [self._get_logo(), Paragraph("<b>DRs by Severity & Type</b>", self.styles['ReportTitle']), '']
        ]
        header_table = Table(header_data, colWidths=[40*mm, 157*mm, 40*mm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        self.story.append(header_table)

        # Subtitles (Printed On, Site, Def type, Severity)
        printed_str = f"<b>Printed On:</b> {self.context['printed_date']} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>{self.context['printed_time']} (Eastern Time)</b>"
        self.story.append(Paragraph(printed_str, self.styles['Subtitle']))
        self.story.append(Paragraph(f"<b>Site: {self.context['site']}</b>", self.styles['Subtitle']))
        self.story.append(Paragraph(self.context['deficiency_type_label'], self.styles['Subtitle']))
        self.story.append(Paragraph(self.context['severity_label'], self.styles['Subtitle']))

        # Wide distinct Legend boxes
        self.story.append(Spacer(3*mm, 3*mm))
        legend_data = [['< 30 Days', '', '30 to 90 Days', '', '> 90 Days']]
        legend_table = Table(legend_data, colWidths=[35*mm, 5*mm, 35*mm, 5*mm, 35*mm], rowHeights=[6*mm])
        legend_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            
            # Apply color to individual blocks
            ('BACKGROUND', (0, 0), (0, 0), get_aging_color('green')),
            ('BACKGROUND', (2, 0), (2, 0), get_aging_color('orange')),
            ('BACKGROUND', (4, 0), (4, 0), get_aging_color('red')),
            
            # Grids specific to blocks to avoid borders on the empty spacers
            ('GRID', (0, 0), (0, 0), 0.5, colors.black),
            ('GRID', (2, 0), (2, 0), 0.5, colors.black),
            ('GRID', (4, 0), (4, 0), 0.5, colors.black),
        ]))
        
        center_table = Table([[legend_table]])
        center_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        self.story.append(center_table)
        self.story.append(Spacer(6*mm, 6*mm))

    def build_resource_group(self, resource_name, dr_list):
        """Build a resource group with standalone individual tables per DR"""
        
        # Flex table to keep AW139 aligned left, Configuration link aligned right
        resource_header_table = Table([
            [Paragraph(f"{resource_name}", self.styles['ResourceHeader']),
             Paragraph('<u>Configuration</u>', self.styles['ConfigLink'])]
        ], colWidths=[133*mm, 134*mm])
        self.story.append(resource_header_table)

        # Standard headers width summing up to 267mm
        col_widths = [15*mm, 60*mm, 35*mm, 20*mm, 35*mm, 18*mm, 20*mm, 15*mm, 22*mm, 27*mm]
        headers = ['DR #', 'Description', 'Raised By', 'Raised Date',
                   'Assigned To', 'Status', 'Sub Status', 'Severity', 'Due Date', 'Configuration']
        
        # Dedicated Headers Table
        header_table = Table([headers], colWidths=col_widths, rowHeights=[6*mm])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fcd5b4')), # Peach header
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        self.story.append(header_table)
        self.story.append(Spacer(2*mm, 2*mm))

        # Build each individual DR as an isolated 2-row table structure
        for item in dr_list:
            dr = item['dr']
            aging = item['aging']
            last_date = item['last_action_date']
            last_note = item['last_action_note']
            
            # Row 1 Main Details
            row1 = [
                str(dr.deficiency_number), 
                Paragraph(self._truncate_text(getattr(dr, 'issue_description', ''), 200), self.styles['Normal']),
                Paragraph(getattr(dr, 'raised_by_name', None) or '-', self.styles['Normal']),
                Paragraph(self._format_date(dr.raised_date), self.styles['CenteredNormal']),
                Paragraph(getattr(dr, 'assignee_name', None) or '-', self.styles['Normal']),
                Paragraph(getattr(dr, 'status', None) or '-', self.styles['CenteredNormal']),
                Paragraph(getattr(dr, 'sub_status', None) or '-', self.styles['CenteredNormal']),
                Paragraph(getattr(dr, 'severity', None) or '-', self.styles['CenteredNormal']),
                Paragraph(self._format_date(dr.due_date), self.styles['CenteredNormal']),
                Paragraph(get_configuration_label(dr), self.styles['CenteredNormal']),
            ]

            # Row 2 Actions 
            action_text = "Last Action Taken: "
            if last_date:
                action_text += f"[{last_date}] - "
            if last_note:
                action_text += strip_html_tags(last_note)
            
            row2 = [Paragraph(action_text, self.styles['ActionRow'])] + [''] * 9

            # Apply separate table wrapper per item list iteration to force gaps
            dr_table = Table([row1, row2], colWidths=col_widths)
            dr_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),

                # Full colored block in the "DR #" slot
                ('BACKGROUND', (0, 0), (0, 0), get_aging_color(aging)),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                ('FONTNAME', (0, 0), (0, 0), 'Helvetica'),

                # Action row merge spanning
                ('SPAN', (0, 1), (-1, 1)),
                ('BACKGROUND', (0, 1), (-1, 1), colors.white),
                ('ALIGN', (0, 1), (-1, 1), 'LEFT'),
            ]))
            
            self.story.append(dr_table)
            self.story.append(Spacer(2*mm, 2*mm))
            
        self.story.append(Spacer(5*mm, 5*mm))

    def _format_date(self, date_val):
        """Format date accurately for display: 17-Apr-13"""
        if date_val:
            if isinstance(date_val, str):
                try:
                    date_val = datetime.strptime(date_val, '%Y-%m-%d')
                except ValueError:
                    return str(date_val)
            return date_val.strftime('%d-%b-%y')
        return '-'

    def _truncate_text(self, text, max_length):
        if text and len(text) > max_length:
            return text[:max_length] + '...'
        return text or '-'

    def build_footer(self):
        """Build document footer"""
        self.story.append(Spacer(5*mm, 5*mm))
        footer_text = f"Total Records: {self.context['total_count']}"
        self.story.append(Paragraph(footer_text, self.styles['Subtitle']))

    def build(self):
        """Build the complete PDF"""
        self.build_header()

        for resource_name, dr_list in self.context['grouped_data']:
            self.build_resource_group(resource_name, dr_list)

        self.build_footer()
        self.doc.build(self.story)


def dr_report_pdf_view(request):
    """
    Generate PDF report for DRs filtered by site, severity, date range, and aircraft type/resource.
    """
    if not REPORTLAB_AVAILABLE:
        return HttpResponse(
            "PDF generation requires 'reportlab' package. "
            "Please install it: pip install reportlab",
            content_type='text/plain',
            status=500
        )

    site = request.GET.get('site', 'All')
    severity = request.GET.get('severity', 'All')
    resource = request.GET.get('resource', '')
    deficiency_type = request.GET.get('deficiency_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    download = request.GET.get('download', '0')

    deficiencies = Deficiency.objects.all()

    if site and site != 'All':
        deficiencies = deficiencies.filter(site_name=site)

    if severity and severity != 'All':
        deficiencies = deficiencies.filter(severity=severity)

    if resource:
        deficiencies = deficiencies.filter(resource=resource)

    if deficiency_type:
        deficiencies = deficiencies.filter(deficiency_type=deficiency_type)

    deficiencies = deficiencies.order_by('resource', 'deficiency_number')
    deficiencies_list = list(deficiencies)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            filtered = []
            for dr in deficiencies_list:
                if dr.raised_date:
                    if isinstance(dr.raised_date, str):
                        try:
                            raised = datetime.strptime(dr.raised_date, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                raised = datetime.strptime(dr.raised_date, '%d-%m-%Y').date()
                            except ValueError:
                                continue
                    else:
                        raised = dr.raised_date

                    if raised >= date_from_obj:
                        filtered.append(dr)
            deficiencies_list = filtered
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            filtered = []
            for dr in deficiencies_list:
                if dr.raised_date:
                    if isinstance(dr.raised_date, str):
                        try:
                            raised = datetime.strptime(dr.raised_date, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                raised = datetime.strptime(dr.raised_date, '%d-%m-%Y').date()
                            except ValueError:
                                continue
                    else:
                        raised = dr.raised_date

                    if raised <= date_to_obj:
                        filtered.append(dr)
            deficiencies_list = filtered
        except ValueError:
            pass

    from collections import defaultdict
    grouped_data = defaultdict(list)

    for dr in deficiencies_list:
        resource_name = getattr(dr, 'resource', 'Unknown') or 'Unknown'
        aging = get_aging_bucket(dr)
        last_action_date, last_action_note = get_last_action(dr)
        grouped_data[resource_name].append({
            'dr': dr,
            'aging': aging,
            'last_action_date': last_action_date,
            'last_action_note': last_action_note,
        })

    grouped_list = [(res, grouped_data[res]) for res in sorted(grouped_data.keys())]

    # Format time output for exact matching
    eastern = pytz.timezone('US/Eastern')
    now_eastern = timezone.now().astimezone(eastern)
    
    printed_date = now_eastern.strftime('%d-%b-%y')
    # Use lstrip to avoid "08:43:45PM", turning it to "8:43:45PM"
    printed_time = now_eastern.strftime('%I:%M:%S%p').lstrip('0')

    severity_label = f"Severity {severity}" if severity != 'All' else "All Severity"
    deficiency_type_label = f"Deficiency Type: {deficiency_type}" if deficiency_type else "All Deficiency Types"

    context = {
        'grouped_data': grouped_list,
        'printed_date': printed_date,
        'printed_time': printed_time,
        'site': site,
        'severity_label': severity_label,
        'deficiency_type_label': deficiency_type_label,
        'deficiency_type': deficiency_type,
        'total_count': len(deficiencies_list),
        'date_from': date_from,
        'date_to': date_to,
    }

    from io import BytesIO
    buffer = BytesIO()

    builder = PDFBuilder(buffer, context)
    builder.build()

    pdf_value = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_value, content_type='application/pdf')

    if download == '1':
        type_part = f"_{deficiency_type}" if deficiency_type else ""
        filename = f"DR_Report_{site}_{severity}{type_part}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    else:
        response['Content-Disposition'] = 'inline; filename="dr_report.pdf"'

    return response