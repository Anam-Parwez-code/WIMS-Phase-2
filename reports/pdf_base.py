# from reportlab.lib import colors
# from reportlab.lib.pagesizes import A4
# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.units import inch
# from io import BytesIO
# from datetime import datetime

# class BaseReportPDF:
#     def __init__(self, title, branch_name, date_range, logo_path=None):
#         self.buffer = BytesIO()
#         self.doc = SimpleDocTemplate(self.buffer, pagesize=A4)
#         self.elements = []
#         self.title = title
#         self.branch_name = branch_name
#         self.date_range = date_range
#         self.logo_path = logo_path
#         self.styles = getSampleStyleSheet()

#     def _create_header(self):
#         # Header data: [[Logo, Branch, DateRange]]
#         logo = Image(self.logo_path, 1*inch, 1*inch) if self.logo_path else "LOGO"
        
#         header_data = [[
#             logo,
#             Paragraph(f"<b>{self.branch_name}</b>", self.styles['Normal']),
#             Paragraph(f"Date: {self.date_range}", self.styles['Normal'])
#         ]]
        
#         header_table = Table(header_data, colWidths=[1.5*inch, 3*inch, 2*inch])
#         header_table.setStyle(TableStyle([
#             ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
#             ('ALIGN', (1,0), (1,0), 'CENTER'),
#             ('ALIGN', (2,0), (2,0), 'RIGHT'),
#         ]))
#         self.elements.append(header_table)
#         self.elements.append(Spacer(1, 0.2*inch))
        
#         # Centered Title
#         title_style = ParagraphStyle('TitleStyle', parent=self.styles['Heading1'], alignment=1, fontSize=18)
#         self.elements.append(Paragraph(self.title, title_style))
#         self.elements.append(Spacer(1, 0.3*inch))

#     def build_table(self, data, col_widths=None):
#         t = Table(data, colWidths=col_widths, repeatRows=1)
#         t.setStyle(TableStyle([
#             ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
#             ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#             ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
#             ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]) # Zebra stripes
#         ]))
#         self.elements.append(t)

#     def get_pdf(self):
#         self._create_header()
#         self.doc.build(self.elements)
#         pdf = self.buffer.getvalue()
#         self.buffer.close()
#         return pdf

import time
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from datetime import datetime
from django.conf import settings
import os

class BaseReportPDF:
    """
    Base class for generating PDF reports with consistent header, footer, and styling.
    """
    
    def __init__(self, title, branch_name, date_range, logo_path=None, orientation='portrait'):
        self.buffer = BytesIO()
        
        # Set page size based on orientation
        pagesize = landscape(A4) if orientation == 'landscape' else A4
        
        self.doc = SimpleDocTemplate(
            self.buffer, 
            pagesize=pagesize,
            topMargin=2.2*inch,
            bottomMargin=0.75*inch,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch
        )
        
        self.elements = []
        self.title = title
        self.branch_name = branch_name
        self.date_range = date_range
        self.logo_path = logo_path
        self.styles = getSampleStyleSheet()
        self.orientation = orientation
        
        # Custom styles
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Create custom paragraph styles for the report"""
        
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=20,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            fontSize=12,
            textColor=colors.grey,
            spaceAfter=6
        )
        
        # Section header style
        self.section_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#283593'),
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )

    # def _draw_page_header(self, canvas, doc, organization=None):
    #     canvas.saveState()

    #     width, height = doc.pagesize
    #     top_y = height - 40

    #     # Branch / Organization
    #     canvas.setFont("Helvetica-Bold", 11)
    #     canvas.drawString(40, top_y, self.branch_name)

    #     # Report title
    #     canvas.setFont("Helvetica", 10)
    #     canvas.drawString(40, top_y - 14, self.title)

    #     # Right-aligned metadata
    #     canvas.setFont("Helvetica", 9)
    #     canvas.drawRightString(
    #         width - 40,
    #         top_y,
    #         f"Period: {self.date_range}"
    #     )
    #     canvas.drawRightString(
    #         width - 40,
    #         top_y - 14,
    #         datetime.now().strftime("Generated: %d/%m/%Y %I:%M %p")
    #     )

    #     # Separator line
    #     canvas.line(40, top_y - 22, width - 40, top_y - 22)

    #     canvas.restoreState()

    # def _draw_page_header(self, canvas, doc, organization=None):
    #     from reportlab.platypus import Table, TableStyle
    #     from reportlab.lib.units import inch

    #     canvas.saveState()

    #     width, height = doc.pagesize
    #     top_y = top_y = height - doc.topMargin + 0.4 * inch

    #     # -------------------------
    #     # Logo handling (same logic)
    #     # -------------------------
    #     logo = None
    #     if self.logo_path and os.path.exists(self.logo_path):
    #         try:
    #             logo = Image(self.logo_path, 1*inch, 1*inch)
    #         except:
    #             logo = None
    #     elif organization and hasattr(organization, 'logo') and organization.logo:
    #         try:
    #             logo_path = os.path.join(settings.MEDIA_ROOT, str(organization.logo))
    #             if os.path.exists(logo_path):
    #                 logo = Image(logo_path, 1*inch, 1*inch)
    #         except:
    #             logo = None

    #     # -------------------------
    #     # Organization details
    #     # -------------------------
    #     org_details = f"<b>{self.branch_name}</b>"
    #     if organization:
    #         address = getattr(organization, 'address', None)
    #         phone = getattr(organization, 'phone', None)
    #         email = getattr(organization, 'email', None)

    #         if address:
    #             org_details += f"<br/>{address}"
    #         if phone:
    #             org_details += f"<br/>Phone: {phone}"
    #         if email:
    #             org_details += f"<br/>Email: {email}"

    #     org_para = Paragraph(org_details, self.styles['Normal'])

    #     # -------------------------
    #     # Date & period block
    #     # -------------------------
    #     date_info = (
    #         f"<b>Generated:</b> {datetime.now().strftime('%d/%m/%Y %I:%M %p')}<br/>"
    #         f"<b>Period:</b> {self.date_range}"
    #     )
    #     date_para = Paragraph(date_info, self.styles['Normal'])

    #     # -------------------------
    #     # Header table (SAME STYLE)
    #     # -------------------------
    #     if logo:
    #         header_data = [[logo, org_para, date_para]]
    #         col_widths = [1.5*inch, 4*inch, 2*inch]
    #     else:
    #         header_data = [[org_para, date_para]]
    #         col_widths = [5*inch, 2.5*inch]

    #     header_table = Table(header_data, colWidths=col_widths)
    #     header_table.setStyle(TableStyle([
    #         ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    #         ('ALIGN', (0,0), (0,0), 'LEFT'),
    #         ('ALIGN', (-1,0), (-1,0), 'RIGHT'),
    #     ]))

    #     # -------------------------
    #     # Draw header table
    #     # -------------------------
    #     w, h = header_table.wrap(doc.width, doc.topMargin)
    #     header_table.drawOn(canvas, doc.leftMargin, top_y - h)

    #     # -------------------------
    #     # Horizontal line
    #     # -------------------------
    #     canvas.setStrokeColor(colors.HexColor('#1a237e'))
    #     canvas.setLineWidth(2)
    #     line_y = top_y - h - 10
    #     canvas.line(
    #         doc.leftMargin,
    #         line_y,
    #         doc.leftMargin + doc.width,
    #         line_y
    #     )

    #     # -------------------------
    #     # Report title
    #     # -------------------------
    #     title_y = top_y - h - 16
    #     canvas.setFont("Helvetica-Bold", 16)
    #     canvas.setFillColor(colors.HexColor('#1a237e'))
    #     canvas.drawCentredString(width / 2, title_y, self.title)

    #     canvas.restoreState()

    def _draw_page_header(self, canvas, doc, organization=None):
        canvas.saveState()

        width, height = doc.pagesize

        # Header starts inside reserved topMargin
        top_y = height - doc.topMargin + 1 * inch

        # Logo
        logo = None
        if self.logo_path and os.path.exists(self.logo_path):
            logo = Image(self.logo_path, 1*inch, 1*inch)
        elif organization and hasattr(organization, 'logo') and organization.logo:
            logo_path = os.path.join(settings.MEDIA_ROOT, str(organization.logo))
            if os.path.exists(logo_path):
                logo = Image(logo_path, 1*inch, 1*inch)

        # Org details
        org_details = f"<b>{self.branch_name}</b>"
        if organization:
            for label in ['address', 'phone', 'email']:
                value = getattr(organization, label, None)
                if value:
                    org_details += f"<br/>{value}"

        org_para = Paragraph(org_details, self.styles['Normal'])

        date_info = (
            f"<b>Generated:</b> {datetime.now().strftime('%d/%m/%Y %I:%M %p')}<br/>"
            f"<b>Period:</b> {self.date_range}"
        )
        date_para = Paragraph(date_info, self.styles['Normal'])

        if logo:
            data = [[logo, org_para, date_para]]
            widths = [1.5*inch, 4*inch, 2*inch]
        else:
            data = [[org_para, date_para]]
            widths = [5*inch, 2.5*inch]

        table = Table(data, colWidths=widths)
        table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (-1,0), (-1,0), 'RIGHT'),
        ]))

        w, h = table.wrap(doc.width, doc.topMargin)
        table.drawOn(canvas, doc.leftMargin, top_y)

        line_y = top_y - h - 10
        canvas.setStrokeColor(colors.HexColor('#1a237e'))
        canvas.setLineWidth(2)
        canvas.line(doc.leftMargin, line_y, doc.leftMargin + doc.width, line_y)

        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawCentredString(
            doc.leftMargin + doc.width / 2,
            line_y - 20,
            self.title
        )

        canvas.restoreState()


    def _create_header(self, organization=None):
        """
        Create header with logo, organization details, and report metadata
        
        Args:
            organization: Organization model instance (optional)
        """
        header_elements = []
        
        # Try to get logo
        logo = None
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                logo = Image(self.logo_path, 1*inch, 1*inch)
            except:
                logo = None
        elif organization and hasattr(organization, 'logo') and organization.logo:
            try:
                logo_path = os.path.join(settings.MEDIA_ROOT, str(organization.logo))
                if os.path.exists(logo_path):
                    logo = Image(logo_path, 1*inch, 1*inch)
            except:
                logo = None
        
        # Organization details
        org_details = f"<b>{self.branch_name}</b>"
        if organization:
            if organization.address:
                org_details += f"<br/>{organization.address}"
            if organization.phone:
                org_details += f"<br/>Phone: {organization.phone}"
            if organization.email:
                org_details += f"<br/>Email: {organization.email}"
        
        org_para = Paragraph(org_details, self.styles['Normal'])
        
        # Date and time
        date_info = f"<b>Generated:</b> {datetime.now().strftime('%d/%m/%Y %I:%M %p')}<br/>"
        date_info += f"<b>Period:</b> {self.date_range}"
        date_para = Paragraph(date_info, self.styles['Normal'])
        
        # Create header table
        if logo:
            header_data = [[logo, org_para, date_para]]
            col_widths = [1.5*inch, 4*inch, 2*inch]
        else:
            header_data = [[org_para, date_para]]
            col_widths = [5*inch, 2.5*inch]
        
        header_table = Table(header_data, colWidths=col_widths)
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (-1,0), (-1,0), 'RIGHT'),
        ]))
        
        self.elements.append(header_table)
        self.elements.append(Spacer(1, 0.2*inch))
        
        # Add horizontal line
        line_table = Table([['']], colWidths=[7.5*inch])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0,0), (-1,0), 2, colors.HexColor('#1a237e')),
        ]))
        self.elements.append(line_table)
        self.elements.append(Spacer(1, 0.2*inch))
        
        # Report title
        self.elements.append(Paragraph(self.title, self.title_style))
        self.elements.append(Spacer(1, 0.3*inch))

    def add_section_header(self, text):
        """Add a section header to the report"""
        self.elements.append(Paragraph(text, self.section_style))

    def add_paragraph(self, text, style='Normal'):
        """Add a paragraph to the report"""
        self.elements.append(Paragraph(text, self.styles[style]))
        self.elements.append(Spacer(1, 0.1*inch))

    def add_summary_box(self, summary_data):
        """
        Add a summary box with key metrics
        
        Args:
            summary_data: List of tuples [(label, value), ...]
        """
        summary_table_data = []
        for label, value in summary_data:
            summary_table_data.append([
                Paragraph(f"<b>{label}:</b>", self.styles['Normal']),
                Paragraph(str(value), self.styles['Normal'])
            ])
        
        summary_table = Table(summary_table_data, colWidths=[3*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#e8eaf6')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        
        self.elements.append(summary_table)
        self.elements.append(Spacer(1, 0.3*inch))

    def build_table(self, data, col_widths=None, zebra_stripes=True, header_color=None):
        """
        Build a formatted table
        
        Args:
            data: 2D list with headers in first row
            col_widths: List of column widths (optional)
            zebra_stripes: Boolean to enable alternating row colors
            header_color: Color for header row (default: dark blue)
        """
        if not data or len(data) == 0:
            self.add_paragraph("No data available for this report.", 'Normal')
            return
        
        # Default header color
        if header_color is None:
            header_color = colors.HexColor('#1a237e')
        
        # Create table
        t = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Base style
        style_commands = [
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), header_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            
            # Cell padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        # Add zebra stripes
        if zebra_stripes and len(data) > 1:
            style_commands.append(
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), 
                 [colors.white, colors.HexColor('#f5f5f5')])
            )
        
        t.setStyle(TableStyle(style_commands))
        self.elements.append(t)

    def add_footer_note(self, note):
        """Add a footer note at the bottom of the report"""
        self.elements.append(Spacer(1, 0.3*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        self.elements.append(Paragraph(note, footer_style))

    def get_pdf(self, organization=None):
        """
        Generate and return the PDF content
        
        Args:
            organization: Organization model instance (optional)
        """
        # self._create_header(organization)
        # self.doc.build(self.elements)
        # pdf = self.buffer.getvalue()
        # self.buffer.close()
        # return pdf
        self.doc.build(
            self.elements,
            onFirstPage=lambda c, d: self._draw_page_header(c, d, organization),
            # onLaterPages=lambda c, d: self._draw_page_header(c, d, organization),
        )

        pdf = self.buffer.getvalue()
        self.buffer.close()
        return pdf
