import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

df = pd.read_csv("data/processed/alerts_user_day_demo.csv")

# ── Basic counts ──────────────────────────────────────────────────────────────
total = len(df)
high = (df["risk_band"] == "High").sum()
medium = (df["risk_band"] == "Medium").sum()
low = (df["risk_band"] == "Low").sum()

print("Total:", total)
print("High:", high)
print("Medium:", medium)
print("Low:", low)
print("\nPercentages:")
print("High %:", round(high / total * 100, 2))
print("Medium %:", round(medium / total * 100, 2))
print("Low %:", round(low / total * 100, 2))

# ── Top anomalies ─────────────────────────────────────────────────────────────
top = df.sort_values("anomaly_score", ascending=False).head(10)
print("\nTop anomalies:")
print(top[["user", "day", "anomaly_score", "top_reason"]])

print("\nUsers with most high-risk alerts:")
print(df[df["risk_band"] == "High"]["user"].value_counts().head(10))

# ── Ground truth evaluation ───────────────────────────────────────────────────
# CERT ground truth: labels the INSIDER users (malicious scenarios)
# File is usually called "insiders.csv" in the CERT dataset
try:
    insiders = pd.read_csv("data/raw/insiders.csv")  # adjust path if needed

    # insiders.csv has a "user" column — mark those users as malicious
    malicious_users = set(insiders["user"].unique())

    # Create ground truth column: 1 = malicious, 0 = benign
    df["y_true"] = df["user"].apply(lambda u: 1 if u in malicious_users else 0)

    # Model prediction: treat High as positive (threat detected)
    df["y_pred"] = (df["risk_band"] == "High").astype(int)

    print("\n── Classification Report ────────────────────────────────")
    print(classification_report(
        df["y_true"], df["y_pred"],
        target_names=["Benign", "Malicious"],
        digits=4
    ))

    cm = confusion_matrix(df["y_true"], df["y_pred"])
    tn, fp, fn, tp = cm.ravel()
    fpr = round(fp / (fp + tn) * 100, 2)

    print("── Confusion Matrix ─────────────────────────────────────")
    print(f"  True Positives  (correctly flagged threats): {tp}")
    print(f"  True Negatives  (correctly cleared benign):  {tn}")
    print(f"  False Positives (benign flagged as threat):  {fp}")
    print(f"  False Negatives (missed threats):            {fn}")
    print(f"\n  False Positive Rate: {fpr}%")

except FileNotFoundError:
    print("\n[!] insiders.csv not found — skipping ground truth evaluation.")
    print("    Check your CERT dataset folder and update the path above.")