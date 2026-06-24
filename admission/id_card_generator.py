# admission/utils/idcard_generator.py

import io
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from django.http import FileResponse


def generate_student_id_card(admission):
    """
    Generates a styled student ID card PDF.
    Returns FileResponse.
    """

    buffer = io.BytesIO()

    # ID Card Size
    width, height = 60 * mm, 90 * mm
    p = canvas.Canvas(buffer, pagesize=(width, height))

    # 🔷 Outer Border
    p.setStrokeColor(colors.HexColor("#2c3e50"))
    p.setLineWidth(2)
    p.rect(2 * mm, 2 * mm, width - (4 * mm), height - (4 * mm))

    # 🔷 Header Background
    p.setFillColor(colors.HexColor("#2c3e50"))
    p.rect(2 * mm, height - (20 * mm), width - (4 * mm), 18 * mm, fill=1)

    # 🔷 Header Text
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 10)

    institute_name = (
        admission.organization.name
        if admission.organization
        else "STUDENT ID CARD"
    )

    p.drawCentredString(width / 2, height - (10 * mm), institute_name)
    p.setFont("Helvetica", 7)
    p.drawCentredString(width / 2, height - (15 * mm), "IDENTITY CARD")

    # 🔷 Photo Section
    photo_y_start = height - 45 * mm

    if admission.image:
        try:
            p.drawImage(
                admission.image.path,
                (width / 2) - (12.5 * mm),
                photo_y_start,
                width=25 * mm,
                height=25 * mm
            )
        except Exception:
            _draw_blank_photo(p, width, photo_y_start)
    else:
        _draw_blank_photo(p, width, photo_y_start)

    # 🔷 Student Info
    p.setFillColor(colors.black)
    info_y = photo_y_start - 10 * mm

    def draw_info(label, value, y_pos):
        p.setFont("Helvetica-Bold", 7)
        p.drawString(6 * mm, y_pos, f"{label}:")
        p.setFont("Helvetica", 7)
        p.drawString(22 * mm, y_pos, str(value)[:25])

    draw_info("Name", admission.candidate_name.upper(), info_y)
    draw_info("ID No", admission.admission_code, info_y - 5 * mm)
    draw_info("Mobile", admission.mobile_no, info_y - 10 * mm)

    course_name = (
        admission.courses.first().course_name
        if admission.courses.exists()
        else "N/A"
    )

    draw_info("Course", course_name, info_y - 15 * mm)
    draw_info(
        "Valid From",
        admission.admission_date.strftime('%Y'),
        info_y - 20 * mm
    )

    # 🔷 Footer
    p.setFont("Helvetica-Oblique", 5)
    p.setFillColor(colors.red)
    p.drawCentredString(
        width / 2,
        6 * mm,
        "If found, please return to the institute office."
    )

    p.showPage()
    p.save()

    buffer.seek(0)

    filename = f"ID_Card_{admission.admission_code}.pdf"

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=filename,
        content_type="application/pdf"
    )


def _draw_blank_photo(p, width, photo_y_start):
    """
    Draws white blank placeholder photo box.
    """
    p.setStrokeColor(colors.lightgrey)
    p.rect(
        (width / 2) - (12.5 * mm),
        photo_y_start,
        25 * mm,
        25 * mm
    )
    p.setFillColor(colors.grey)
    p.setFont("Helvetica", 6)
    p.drawCentredString(
        width / 2,
        photo_y_start + 12 * mm,
        "PHOTO"
    )
