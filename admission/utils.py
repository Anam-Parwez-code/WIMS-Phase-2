import os

from django.conf import settings

from weasyprint import HTML

def replace_placeholders(
        body_text,
        student_name,
        course_name,
        completion_date,
        batch_name
):

    return (
        body_text
        .replace("{{student_name}}", student_name)
        .replace("{{course_name}}", course_name)
        .replace("{{completion_date}}", str(completion_date))
        .replace("{{batch_name}}", batch_name)
    )

def build_certificate_html(
        template,
        student_name,
        course_name,
        completion_date,
        batch_name
):

    body_text = replace_placeholders(
        template.body_text,
        student_name,
        course_name,
        completion_date,
        batch_name
    )

    logo_url = ""

    if template.institute_logo:
        logo_url = (
            "file://"
            + template.institute_logo.path
        )

    signature_url = ""

    if template.signature_image:
        signature_url = (
            "file://"
            + template.signature_image.path
        )

    stamp_url = ""

    if template.stamp_image:
        stamp_url = (
            "file://"
            + template.stamp_image.path
        )

    html = f"""
    <html>
    <body>

        <div style="text-align:center;">

            <img src="{logo_url}" width="120">

            <h1>{template.institute_name}</h1>

            <h2>{template.certificate_title}</h2>

            <p>{body_text}</p>

            <br><br>

            <img src="{signature_url}" width="120">

            <p>{template.signature_label}</p>

            <br>

            <img src="{stamp_url}" width="120">

        </div>

    </body>
    </html>
    """

    return html


import os

from django.conf import settings

#from weasyprint import HTML
from xhtml2pdf import pisa

def generate_certificate_pdf(
        certificate_issue,
        html_content
):

    pdf_dir = os.path.join(
        settings.MEDIA_ROOT,
        "certificates",
        "pdf"
    )

    os.makedirs(
        pdf_dir,
        exist_ok=True
    )

    filename = (
        f"certificate_{certificate_issue.id}.pdf"
    )

    pdf_path = os.path.join(
        pdf_dir,
        filename
    )

    HTML(
        string=html_content,
        base_url=settings.BASE_DIR
    ).write_pdf(pdf_path)

    return (
        f"certificates/pdf/{filename}"
    )



