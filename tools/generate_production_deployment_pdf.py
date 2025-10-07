#!/usr/bin/env python3
"""
Generate BrainSwarmOps Production Deployment Guide PDF.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import inch
import os

pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

def make_pdf(output="docs/BrainSwarmOps_Production_Deployment_Guide.pdf"):
    os.makedirs("docs", exist_ok=True)

    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        title="BrainSwarmOps Production Deployment Guide",
        leftMargin=60,
        rightMargin=60,
        topMargin=80,
        bottomMargin=60,
    )

    teal = colors.HexColor("#00C6D1")
    graphite = colors.HexColor("#121214")
    styles = getSampleStyleSheet()

    title = ParagraphStyle("title", parent=styles["Heading1"], fontName="HeiseiKakuGo-W5",
        fontSize=22, textColor=teal, alignment=1, spaceAfter=14)
    section = ParagraphStyle("section", parent=styles["Heading2"], fontName="HeiseiKakuGo-W5",
        fontSize=14, textColor=colors.white, spaceBefore=8, spaceAfter=6)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="HeiseiKakuGo-W5",
        fontSize=10, leading=14, textColor=colors.white)

    def header_footer(canvas, doc):
        width, height = letter
        canvas.saveState()
        # Graphite background
        canvas.setFillColor(graphite)
        canvas.rect(0, 0, width, height, fill=True, stroke=False)

        # Gradient-like teal header bar
        canvas.setFillColor(teal)
        canvas.rect(0, height - 60, width, 60, fill=True, stroke=False)

        # Header title
        canvas.setFillColor(colors.white)
        canvas.setFont("HeiseiKakuGo-W5", 14)
        canvas.drawString(60, height - 40, "🧠 BrainSwarmOps Production Deployment Guide")

        # Footer text
        canvas.setFont("HeiseiKakuGo-W5", 9)
        canvas.setFillColor(colors.gray)
        canvas.drawString(60, 40, "© 2025 BrainSwarmOps · jfbinTECHA · All rights reserved")

        # Section divider line
        canvas.setStrokeColor(teal)
        canvas.setLineWidth(0.6)
        canvas.line(60, 55, width - 60, 55)

        canvas.restoreState()

    story = []
    story.append(Paragraph("BrainSwarmOps Production Deployment Guide", title))
    story.append(Paragraph("Unified Operations, SSL Automation, and Monitoring Stack", body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("1️⃣ Overview", section))
    story.append(Paragraph(
        "This document describes how to deploy the BrainSwarmOps system in production using Docker Compose, NGINX, and Certbot for fully automated HTTPS and live monitoring.",
        body))

    story.append(Paragraph("2️⃣ Stack Components", section))
    components = [
        "FastAPI backend (port 8001) – API + health endpoints",
        "Next.js frontend dashboard (port 3000)",
        "Redis and Postgres (core data + cache)",
        "NGINX reverse proxy (ports 80/443) – routing + SSL termination",
        "Certbot container – automatic certificate renewal",
    ]
    story.append(ListFlowable([ListItem(Paragraph(c, body)) for c in components], bulletType="bullet"))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("3️⃣ Deployment Steps", section))
    steps = [
        "Clone repository: `git clone https://github.com/jfbinTECHA/brain-swarm.git`",
        "Build and launch: `docker compose up -d --build`",
        "Check status: `docker ps` → services should show `(healthy)`",
        "Access dashboard: http://localhost (or https://yourdomain.com after SSL)",
    ]
    story.append(ListFlowable([ListItem(Paragraph(s, body)) for s in steps], bulletType="1"))

    story.append(Paragraph("4️⃣ SSL & HTTPS Setup", section))
    story.append(Paragraph(
        "The stack uses an integrated NGINX + Certbot configuration. Certificates are stored in `nginx/certs/` and automatically renewed every 12 hours. "
        "NGINX is reloaded in place when new certificates are detected, ensuring zero downtime.",
        body))

    story.append(Paragraph("5️⃣ Verification Commands", section))
    cmds = [
        "`curl -s localhost:8001/healthz | jq` → backend OK",
        "`docker logs brainswarm-certbot` → certbot renewal activity",
        "`docker exec brainswarm-nginx nginx -t` → config validation",
        "`curl -I https://yourdomain.com` → HTTP 200 with valid TLS",
    ]
    story.append(ListFlowable([ListItem(Paragraph(c, body)) for c in cmds], bulletType="bullet"))

    story.append(Paragraph("6️⃣ Automatic Recovery", section))
    story.append(Paragraph(
        "Docker healthchecks automatically restart unhealthy containers. The Watchdog agent complements this by monitoring deeper application-level metrics and restarting services via API triggers.",
        body))

    story.append(Paragraph("7️⃣ Maintenance & Scaling", section))
    story.append(Paragraph(
        "• To stop stack: `docker compose down --remove-orphans`\n"
        "• To rebuild: `docker compose up -d --build`\n"
        "• To monitor logs: `docker logs -f brainswarm-nginx`\n"
        "• To extend horizontally, deploy NGINX + API replicas under Kubernetes or Swarm mode.",
        body))

    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph("End of Guide", body))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✅ PDF generated at {output}")

if __name__ == "__main__":
    make_pdf()