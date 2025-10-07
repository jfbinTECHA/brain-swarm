#!/usr/bin/env python3
"""
Generate a styled PDF version of the BrainSwarmOps Admin Console documentation.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
import os

pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

def make_pdf(output_path="docs/BrainSwarmOps_Admin_Console_Guide.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        title="BrainSwarmOps Admin Console Guide",
        leftMargin=60,
        rightMargin=60,
        topMargin=80,
        bottomMargin=60,
    )

    styles = getSampleStyleSheet()

    # Define colors
    teal = colors.HexColor("#00C6D1")
    graphite = colors.HexColor("#121214")

    # Header and footer drawing
    def draw_header_footer(canvas, doc):
        canvas.saveState()
        width, height = letter

        # Background
        canvas.setFillColor(graphite)
        canvas.rect(0, 0, width, height, fill=True, stroke=False)

        # Header logo area
        canvas.setFillColor(teal)
        canvas.setFont("HeiseiKakuGo-W5", 14)
        canvas.drawString(60, height - 50, "🧠 BrainSwarmOps Admin Console 1.0")

        # Footer branding
        canvas.setFont("HeiseiKakuGo-W5", 9)
        canvas.setFillColor(colors.gray)
        canvas.drawString(60, 40, "© 2025 BrainSwarmOps · jfbinTECHA · All rights reserved")

        canvas.restoreState()

    # Custom styles
    header = ParagraphStyle(
        "header",
        parent=styles["Heading1"],
        fontName="HeiseiKakuGo-W5",
        textColor=teal,
        fontSize=20,
        spaceAfter=12,
    )

    subheader = ParagraphStyle(
        "subheader",
        parent=styles["Heading2"],
        fontName="HeiseiKakuGo-W5",
        textColor=colors.white,
        fontSize=14,
        spaceBefore=6,
        spaceAfter=6,
    )

    body = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        fontName="HeiseiKakuGo-W5",
        textColor=colors.white,
        fontSize=10,
        leading=14,
    )

    from reportlab.lib.units import inch

    story = []

    def add_section(title, content):
        story.append(Paragraph(title, header))
        story.append(Paragraph(content, body))
        story.append(Spacer(1, 0.2 * inch))

    # Compose PDF
    add_section("🧠 BrainSwarmOps Admin Console 1.0", "Unified System Health • Control • Telemetry")
    add_section(
        "📘 Overview",
        "Unified dashboard for real-time system monitoring and control built with FastAPI, Next.js, Redis, and Docker Compose."
    )
    add_section(
        "🧩 Core Features",
        "• Real-time Health Monitor\n• Restart and Shutdown controls\n• Redis audit logging and SSE live events\n• Toast notifications and Live Ops indicator\n• Self-healing watchdog\n• Teal-on-graphite design"
    )
    add_section(
        "⚙️ Setup",
        "git clone https://github.com/jfbinTECHA/brain-swarm.git\ncd brain-swarm\ndocker compose up -d --build\n\nOpen http://localhost:3000/admin"
    )
    add_section(
        "🧪 Verification Commands",
        "curl -s localhost:8001/healthz | jq\ncurl -X POST localhost:8001/admin/restart\ndocker exec -it brainswarm-redis redis-cli XRANGE admin_events - +"
    )
    add_section(
        "👤 Author",
        "Joseph Buzzell (jfbinTECHA) · BrainSwarmOps © 2025"
    )

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    print(f"✅ Branded PDF generated: {output_path}")


if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    make_pdf()