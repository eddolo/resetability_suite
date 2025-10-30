# python/report_utils.py
import numpy as np
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def make_summary(df):
    if df.empty:
        return {
            "mean_R": np.nan,
            "mean_theta": np.nan,
            "mean_benefit": np.nan,
            "resets": 0,
        }
    return {
        "mean_R": np.nanmean(df["R"]),
        "mean_theta": np.nanmean(df["theta_net_deg"]),
        "mean_benefit": np.nanmean(df["predicted_benefit_deg"]),
        "resets": len(df[(df["R"] < 0.05) & (df["predicted_benefit_deg"] > 0)]),
    }


def export_pdf(summary, outfile="results/telemetry_report.pdf"):
    c = canvas.Canvas(outfile, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(50, 740, "SO(3) Resetability Analysis Report")
    c.line(50, 735, 560, 735)
    y = 710
    for k, v in summary.items():
        c.drawString(
            60,
            y,
            (
                f"{k.replace('_',' ').title()}: {v:.4f}"
                if isinstance(v, float)
                else f"{k}: {v}"
            ),
        )
        y -= 20
    c.save()
    return outfile
