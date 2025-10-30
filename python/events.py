# python/events.py
import csv
import time
from pathlib import Path


class EventLogger:
    def __init__(self, path="results/reset_events.csv"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with open(self.path, "w", newline="") as f:
                csv.writer(f).writerow(
                    [
                        "wall_time",
                        "timestamp",
                        "domain",
                        "R",
                        "theta_net_deg",
                        "predicted_benefit_deg",
                    ]
                )

    def log(self, ts, domain, R, theta_deg, benefit_deg):
        with open(self.path, "a", newline="") as f:
            csv.writer(f).writerow(
                [
                    int(time.time()),
                    float(ts),
                    domain,
                    float(R),
                    float(theta_deg),
                    float(benefit_deg),
                ]
            )
        return self.path
