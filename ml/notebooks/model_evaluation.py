"""
Model Evaluation Report — Credit Card Fraud Detection
=======================================================
Run: python ml/notebooks/model_evaluation.py
Needs: ml/artifacts/*.pkl  (run train.py first)
Output: ml/reports/eval_*.png
"""
import json, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import joblib
from pathlib import Path
from sklearn.metrics import (
    roc_curve, auc, precision_recall_curve, average_precision_score,
    confusion_matrix, classification_report, f1_score, precision_score, recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings("ignore")

ROOT      = Path(__file__).parents[2]
DATA      = ROOT / "ml" / "data" / "creditcard.csv"
ARTIFACTS = ROOT / "backend" / "app" / "ml" / "artifacts"
REPORTS   = ROOT / "ml" / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)
RANDOM_STATE = 42

C = {"legit":"#378ADD","fraud":"#E24B4A","neutral":"#888780",
     "bg":"#FAFAFA","grid":"#EEEEEE","green":"#22C55E"}

plt.rcParams.update({"font.family":"DejaVu Sans","axes.spines.top":False,
    "axes.spines.right":False,"axes.grid":True,"grid.color":C["grid"],
    "grid.linewidth":0.6,"axes.facecolor":C["bg"],"figure.facecolor":"white"})

def save(name):
    out = REPORTS / name
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  -> {name}")


# ── Load model + test data ────────────────────────────────────────────────────
def load_artifacts():
    lr_path  = ARTIFACTS / "logistic_regression.pkl"
    sc_path  = ARTIFACTS / "scaler.pkl"
    if not lr_path.exists():
        raise FileNotFoundError("Model not found. Run: python -m app.ml.pipeline.train first.")
    model  = joblib.load(lr_path)
    scaler = joblib.load(sc_path)
    print("Model loaded:", lr_path.name)
    return model, scaler

def prepare_test_data(scaler):
    df = pd.read_csv(DATA)
    X  = df.drop("Class", axis=1).values
    y  = df["Class"].values
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)
    X_test[:, :2] = scaler.transform(X_test[:, :2])
    return X_test, y_test


# 1. ROC curve
def plot_roc(model, X_test, y_test):
    probas = model.predict_proba(X_test)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, probas)
    roc_auc = auc(fpr, tpr)

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(fpr, tpr, color=C["fraud"], lw=2.5, label=f"LR + SMOTE  (AUC = {roc_auc:.4f})")
    ax.plot([0, 1], [0, 1], color=C["neutral"], lw=1.2, linestyle="--", label="Random classifier")
    ax.fill_between(fpr, tpr, alpha=0.08, color=C["fraud"])
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate (Recall)")
    ax.set_title(f"1. ROC Curve  —  AUC = {roc_auc:.4f}", fontweight="bold")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)

    # Zoom inset — top-left corner
    axins = ax.inset_axes([0.08, 0.55, 0.38, 0.38])
    axins.plot(fpr, tpr, color=C["fraud"], lw=1.5)
    axins.set_xlim(0, 0.10); axins.set_ylim(0.85, 1.0)
    axins.set_title("Low FPR zoom", fontsize=8)
    ax.indicate_inset_zoom(axins, edgecolor="gray")

    save("eval_01_roc_curve.png")
    return roc_auc

# 2. Precision-Recall curve
def plot_pr(model, X_test, y_test):
    probas = model.predict_proba(X_test)[:, 1]
    prec, rec, thresholds = precision_recall_curve(y_test, probas)
    ap = average_precision_score(y_test, probas)
    baseline = y_test.sum() / len(y_test)

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(rec, prec, color=C["fraud"], lw=2.5, label=f"LR + SMOTE  (AP = {ap:.4f})")
    ax.axhline(baseline, color=C["neutral"], lw=1.2, linestyle="--",
               label=f"Baseline (fraud rate {baseline:.4%})")
    ax.fill_between(rec, prec, baseline, alpha=0.08, color=C["fraud"])
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(f"2. Precision-Recall Curve  —  AP = {ap:.4f}", fontweight="bold")
    ax.legend()
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.05)
    save("eval_02_pr_curve.png")
    return ap

# 3. Confusion matrix (visual)
def plot_confusion_matrix(model, X_test, y_test, threshold=0.5):
    probas = model.predict_proba(X_test)[:, 1]
    preds  = (probas >= threshold).astype(int)
    cm     = confusion_matrix(y_test, preds)
    tn, fp, fn, tp = cm.ravel()
    total  = tn + fp + fn + tp

    cells = [
        (tn, "True\nNegative",  "Correctly identified\nlegitimate", "#DCFCE7", "#166534"),
        (fp, "False\nPositive", "Legitimate flagged\nas fraud",     "#FEE2E2", "#991B1B"),
        (fn, "False\nNegative", "Fraud missed\nby model",           "#FEF3C7", "#92400E"),
        (tp, "True\nPositive",  "Correctly identified\nfraud",      "#DBEAFE", "#1E3A5F"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(9, 8))
    fig.suptitle(f"3. Confusion Matrix  (threshold = {threshold:.2f})",
                 fontweight="bold", fontsize=13)
    axes = axes.flatten()

    for ax, (val, title, sub, bg, tc) in zip(axes, cells):
        ax.set_facecolor(bg)
        ax.text(0.5, 0.60, f"{val:,}", ha="center", va="center",
                fontsize=36, fontweight="bold", color=tc,
                transform=ax.transAxes)
        ax.text(0.5, 0.30, title, ha="center", va="center",
                fontsize=13, fontweight="600", color=tc,
                transform=ax.transAxes)
        ax.text(0.5, 0.12, sub, ha="center", va="center",
                fontsize=9, color=tc, alpha=0.8,
                transform=ax.transAxes)
        ax.text(0.5, -0.02, f"{val/total:.2%} of total",
                ha="center", va="center", fontsize=9, color=tc,
                alpha=0.7, transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor("#CBD5E1"); spine.set_linewidth(1)

    plt.tight_layout()
    save("eval_03_confusion_matrix.png")

    # Print classification report
    print("\nClassification Report:")
    print(classification_report(y_test, preds, target_names=["Legitimate","Fraud"]))
    return {"tn":int(tn),"fp":int(fp),"fn":int(fn),"tp":int(tp)}

# 4. Threshold sweep: F1 / Precision / Recall
def plot_threshold_sweep(model, X_test, y_test):
    probas = model.predict_proba(X_test)[:, 1]
    thresholds = np.arange(0.01, 0.99, 0.005)
    f1s, precs, recs, fprs = [], [], [], []

    for t in thresholds:
        p = (probas >= t).astype(int)
        f1s.append(f1_score(y_test, p, zero_division=0))
        precs.append(precision_score(y_test, p, zero_division=0))
        recs.append(recall_score(y_test, p, zero_division=0))
        tn, fp, fn, tp = confusion_matrix(y_test, p).ravel()
        fprs.append(fp / (fp + tn) if (fp + tn) > 0 else 0)

    best_idx = int(np.argmax(f1s))
    best_t   = float(thresholds[best_idx])

    fig, axes = plt.subplots(2, 1, figsize=(11, 9))
    fig.suptitle("4. Threshold Sweep Analysis", fontweight="bold", fontsize=13)

    ax = axes[0]
    ax.plot(thresholds, f1s,   color=C["fraud"],   lw=2.2, label="F1 Score")
    ax.plot(thresholds, precs, color=C["legit"],   lw=2.0, label="Precision", linestyle="--")
    ax.plot(thresholds, recs,  color=C["green"],   lw=2.0, label="Recall",    linestyle="-.")
    ax.axvline(best_t, color="#854F0B", linestyle=":", lw=1.5,
               label=f"Best threshold = {best_t:.3f}  (F1 = {f1s[best_idx]:.4f})")
    ax.set_xlabel("Decision threshold")
    ax.set_ylabel("Score")
    ax.set_title("F1 / Precision / Recall vs threshold")
    ax.legend()
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.05)

    ax = axes[1]
    ax.plot(thresholds, fprs, color=C["fraud"], lw=2.2, label="False Positive Rate")
    ax.axvline(best_t, color="#854F0B", linestyle=":", lw=1.5,
               label=f"Best threshold = {best_t:.3f}")
    ax.set_xlabel("Decision threshold")
    ax.set_ylabel("False Positive Rate")
    ax.set_title("FPR vs threshold  (lower = fewer legitimate flagged as fraud)")
    ax.legend()
    ax.set_xlim(0, 1)

    plt.tight_layout()
    save("eval_04_threshold_sweep.png")
    return best_t

# 5. Feature importance (LR coefficients)
def plot_feature_importance(model):
    feature_names = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
    coefs = model.coef_[0]
    idx   = np.argsort(np.abs(coefs))[::-1][:20]   # top 20

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = [C["fraud"] if coefs[i] > 0 else C["legit"] for i in idx]
    bars = ax.barh(
        [feature_names[i] for i in idx[::-1]],
        coefs[idx[::-1]],
        color=colors[::-1],
        edgecolor="white", linewidth=0.5,
    )
    ax.axvline(0, color="#888780", lw=1)
    ax.set_xlabel("Logistic Regression coefficient")
    ax.set_title("5. Feature Importance (LR coefficients, top 20)\n"
                 "Red = positive → higher value increases fraud probability",
                 fontweight="bold")
    plt.tight_layout()
    save("eval_05_feature_importance.png")

# 6. Probability distribution of predictions
def plot_prob_distribution(model, X_test, y_test):
    probas = model.predict_proba(X_test)[:, 1]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("6. Predicted Probability Distributions", fontweight="bold")

    ax = axes[0]
    ax.hist(probas[y_test==0], bins=80, color=C["legit"], alpha=0.65,
            density=True, label="Legitimate")
    ax.hist(probas[y_test==1], bins=80, color=C["fraud"], alpha=0.75,
            density=True, label="Fraud")
    ax.set_xlabel("Predicted fraud probability")
    ax.set_ylabel("Density")
    ax.set_title("Distribution (linear scale)")
    ax.legend()

    ax = axes[1]
    ax.hist(probas[y_test==0]+1e-9, bins=80, color=C["legit"], alpha=0.65,
            density=True, label="Legitimate", log=True)
    ax.hist(probas[y_test==1]+1e-9, bins=80, color=C["fraud"], alpha=0.75,
            density=True, label="Fraud", log=True)
    ax.set_xlabel("Predicted fraud probability")
    ax.set_ylabel("Density (log)")
    ax.set_title("Distribution (log scale — shows tails)")
    ax.legend()

    plt.tight_layout()
    save("eval_06_prob_distribution.png")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== Model Evaluation: Credit Card Fraud Detection ===\n")
    model, scaler = load_artifacts()
    X_test, y_test = prepare_test_data(scaler)
    print(f"Test set: {len(y_test):,} samples  |  fraud: {y_test.sum():,}\n")

    print("[1/6] ROC curve...")
    roc_auc = plot_roc(model, X_test, y_test)

    print("[2/6] Precision-Recall curve...")
    ap = plot_pr(model, X_test, y_test)

    print("[3/6] Confusion matrix...")
    cm_data = plot_confusion_matrix(model, X_test, y_test)

    print("[4/6] Threshold sweep...")
    best_t = plot_threshold_sweep(model, X_test, y_test)

    print("[5/6] Feature importance...")
    plot_feature_importance(model)

    print("[6/6] Probability distribution...")
    plot_prob_distribution(model, X_test, y_test)

    # Save evaluation summary
    summary = {
        "auc_roc": round(roc_auc, 4),
        "avg_precision": round(ap, 4),
        "best_threshold": round(best_t, 4),
        "confusion_matrix": cm_data,
    }
    out = REPORTS / "eval_summary.json"
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  -> eval_summary.json")
    print(f"\n✓ Evaluation complete — reports saved to {REPORTS}\n")
    print(f"  AUC-ROC:        {roc_auc:.4f}")
    print(f"  Avg Precision:  {ap:.4f}")
    print(f"  Best threshold: {best_t:.3f}")
