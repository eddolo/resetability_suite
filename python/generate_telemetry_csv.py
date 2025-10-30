# ==========================================================
# generate_telemetry_csv.py
# ----------------------------------------------------------
# Generates a simple but realistic SO(3) telemetry CSV file
# for the Resetability Control Suite demo.
# ==========================================================

import numpy as np
import pandas as pd
from pathlib import Path

# --- Parameters ---
N = 1000           # number of samples
FPS = 20.0         # frames per second
DT = 1.0 / FPS
T = np.arange(N) * DT

# --- Angular velocity pattern (rad/s) ---
wx = 0.2 * np.sin(0.5 * T) + 0.03 * np.random.randn(N)
wy = 0.15 * np.cos(0.4 * T) + 0.03 * np.random.randn(N)
wz = 0.25 * np.sin(0.2 * T + 0.5) + 0.03 * np.random.randn(N)

# --- Integrate to quaternions ---
def quat_mul(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    ])

def integrate_quats(wx, wy, wz, dt):
    q = np.zeros((len(wx), 4))
    q[0] = [1, 0, 0, 0]  # identity
    for i in range(1, len(wx)):
        omega = np.array([wx[i], wy[i], wz[i]])
        theta = np.linalg.norm(omega) * dt
        if theta > 0:
            axis = omega / theta
            dq = np.hstack([np.cos(theta/2), np.sin(theta/2)*axis])
        else:
            dq = np.array([1, 0, 0, 0])
        q[i] = quat_mul(dq, q[i-1])
        q[i] /= np.linalg.norm(q[i])
    return q

q = integrate_quats(wx, wy, wz, DT)

# --- Build DataFrame ---
df = pd.DataFrame({
    "timestamp": T,
    "qw": q[:,0],
    "qx": q[:,1],
    "qy": q[:,2],
    "qz": q[:,3],
    "wx": wx,
    "wy": wy,
    "wz": wz
})

# --- Save file ---
out_path = Path("data/telemetry.csv")
out_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out_path, index=False)

print(f"\n✅ Telemetry data generated successfully!")
print(f"Saved to: {out_path.resolve()}")
print(f"Rows: {len(df)} | Columns: {list(df.columns)}")
