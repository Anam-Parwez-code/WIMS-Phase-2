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