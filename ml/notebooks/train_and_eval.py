import os, json, time, warnings
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, f1_score,
    precision_score, recall_score, average_precision_score, matthews_corrcoef,
    precision_recall_curve, roc_curve, auc,
)
from imblearn.over_sampling import SMOTE
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "creditcard.csv"
MODELS_DIR = ROOT / "models"
REPORTS = ROOT / "reports"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)
RS = 42

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

C = {"legit":"#378ADD","fraud":"#E24B4A","bg":"#FAFAFA","grid":"#EEEEEE","green":"#22C55E","neutral":"#888780"}
plt.rcParams.update({"font.family":"DejaVu Sans","axes.spines.top":False,
    "axes.spines.right":False,"axes.grid":True,"grid.color":C["grid"],
    "grid.linewidth":0.6,"axes.facecolor":C["bg"],"figure.facecolor":"white"})

def save_report(name):
    plt.savefig(REPORTS / name, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  -> {name}")

def engineer_features(df):
    df = df.copy()
    df["log_amount"]      = np.log1p(df["Amount"])
    df["is_small_amount"] = (df["Amount"] < 10).astype(int)
    df["is_round_amount"] = (df["Amount"] % 10 == 0).astype(int)
    df["is_large_amount"] = (df["Amount"] > 1000).astype(int)
    df["hour"]     = (df["Time"] % 86400 // 3600).astype(int)
    df["is_night"] = df["hour"].isin([0,1,2,3,4,5]).astype(int)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["day_period"] = df["hour"].apply(lambda h: 0 if h<6 else 1 if h<12 else 2 if h<18 else 3)
    v_cols = [f"V{i}" for i in range(1,29)]
    eng_cols = ["log_amount","is_small_amount","is_round_amount","is_large_amount",
                "hour","is_night","hour_sin","hour_cos","day_period"]
    feature_cols = ["Time","Amount"] + v_cols + eng_cols
    return df, feature_cols

def optimize_threshold(model, X_val, y_val):
    probas = model.predict_proba(X_val)[:,1]
    best_t, best_f1 = 0.5, 0.0
    for t in np.arange(0.05, 0.95, 0.005):
        preds = (probas >= t).astype(int)
        f = f1_score(y_val, preds, zero_division=0)
        if f > best_f1:
            best_f1 = f; best_t = float(t)
    return best_t, best_f1

def evaluate_model(model, X_test, y_test, threshold, label):
    probas = model.predict_proba(X_test)[:,1]
    preds  = (probas >= threshold).astype(int)
    cm     = confusion_matrix(y_test, preds)
    tn, fp, fn, tp = cm.ravel()
    return {
        "algorithm": label, "threshold": round(threshold, 3),
        "precision": round(float(precision_score(y_test, preds, zero_division=0)), 4),
        "recall":    round(float(recall_score(y_test, preds, zero_division=0)), 4),
        "f1":        round(float(f1_score(y_test, preds, zero_division=0)), 4),
        "auc_roc":   round(float(roc_auc_score(y_test, probas)), 4),
        "pr_auc":    round(float(average_precision_score(y_test, probas)), 4),
        "mcc":       round(float(matthews_corrcoef(y_test, preds)), 4),
        "confusion_matrix": {"tn":int(tn),"fp":int(fp),"fn":int(fn),"tp":int(tp)},
    }


if __name__ == "__main__":
    t0 = time.time()
    print("=" * 60)
    print("  TRAINING + EVALUATION (fast mode)")
    print("=" * 60)

    df = pd.read_csv(DATA)
    df = df.dropna(subset=["Class"]).reset_index(drop=True)
    df["Class"] = df["Class"].astype(int)
    print(f"Loaded {len(df):,} rows | fraud {df['Class'].sum():,} ({df['Class'].mean():.4%})")

    df_eng, feature_cols = engineer_features(df)
    n = len(df_eng)
    train_end = int(n * 0.70); val_end = int(n * 0.80)
    df_train, df_val, df_test = df_eng.iloc[:train_end], df_eng.iloc[train_end:val_end], df_eng.iloc[val_end:]
    X_train, y_train = df_train[feature_cols].values, df_train["Class"].values
    X_val, y_val     = df_val[feature_cols].values,   df_val["Class"].values
    X_test, y_test   = df_test[feature_cols].values,   df_test["Class"].values

    scale_indices = [feature_cols.index(f) for f in ["Time","Amount","log_amount","hour","hour_sin","hour_cos","day_period"]]
    scaler = RobustScaler()
    X_train_s = X_train.copy(); X_val_s = X_val.copy(); X_test_s = X_test.copy()
    X_train_s[:,scale_indices] = scaler.fit_transform(X_train[:,scale_indices])
    X_val_s[:,scale_indices]   = scaler.transform(X_val[:,scale_indices])
    X_test_s[:,scale_indices]  = scaler.transform(X_test[:,scale_indices])

    print(f"\nSplit: train={len(X_train):,} val={len(X_val):,} test={len(X_test):,}")

    smote = SMOTE(k_neighbors=5, random_state=RS)
    X_res, y_res = smote.fit_resample(X_train_s, y_train)
    print(f"SMOTE: {len(X_train_s):,} -> {len(X_res):,}")

    results = {}

    # Logistic Regression
    print("\n--- Logistic Regression ---")
    lr = LogisticRegression(solver="lbfgs", class_weight="balanced", max_iter=500, random_state=RS)
    lr.fit(X_res, y_res)
    t_lr, f1_lr = optimize_threshold(lr, X_val_s, y_val)
    m_lr = evaluate_model(lr, X_test_s, y_test, t_lr, "logistic_regression")
    print(f"  F1={m_lr['f1']:.4f} AUC={m_lr['auc_roc']:.4f} PR-AUC={m_lr['pr_auc']:.4f} t={t_lr:.3f}")
    print(classification_report(y_test, (lr.predict_proba(X_test_s)[:,1] >= t_lr).astype(int), target_names=["Legit","Fraud"]))
    results["logistic_regression"] = m_lr
    joblib.dump(lr, MODELS_DIR / "logistic_regression.pkl")

    # XGBoost
    if HAS_XGB:
        print("--- XGBoost ---")
        orig_ratio = round((284315 - 492) / 492)
        xgb_m = xgb.XGBClassifier(
            n_estimators=400, max_depth=6, learning_rate=0.05, subsample=0.8,
            colsample_bytree=0.8, min_child_weight=5, gamma=0,
            scale_pos_weight=orig_ratio, eval_metric="aucpr",
            random_state=RS, n_jobs=-1, verbosity=0)
        xgb_m.fit(X_res, y_res, eval_set=[(X_val_s, y_val)], verbose=False)
        t_xgb, f1_xgb = optimize_threshold(xgb_m, X_val_s, y_val)
        m_xgb = evaluate_model(xgb_m, X_test_s, y_test, t_xgb, "xgboost")
        print(f"  F1={m_xgb['f1']:.4f} AUC={m_xgb['auc_roc']:.4f} PR-AUC={m_xgb['pr_auc']:.4f} t={t_xgb:.3f}")
        print(classification_report(y_test, (xgb_m.predict_proba(X_test_s)[:,1] >= t_xgb).astype(int), target_names=["Legit","Fraud"]))
        results["xgboost"] = m_xgb
        joblib.dump(xgb_m, MODELS_DIR / "xgboost.pkl")

    # Isolation Forest
    print("--- Isolation Forest ---")
    iso = IsolationForest(n_estimators=200, contamination=492/284807, random_state=RS, n_jobs=-1)
    iso.fit(X_train_s)
    scores = -iso.score_samples(X_test_s)
    iso_preds = np.where(iso.predict(X_test_s) == -1, 1, 0)
    cm = confusion_matrix(y_test, iso_preds); tn, fp, fn, tp = cm.ravel()
    m_iso = {
        "algorithm": "isolation_forest",
        "auc_roc": round(float(roc_auc_score(y_test, scores)), 4),
        "pr_auc":  round(float(average_precision_score(y_test, scores)), 4),
        "precision": round(float(precision_score(y_test, iso_preds, zero_division=0)), 4),
        "recall":    round(float(recall_score(y_test, iso_preds, zero_division=0)), 4),
        "f1":        round(float(f1_score(y_test, iso_preds, zero_division=0)), 4),
        "confusion_matrix": {"tn":int(tn),"fp":int(fp),"fn":int(fn),"tp":int(tp)},
    }
    print(f"  F1={m_iso['f1']:.4f} AUC={m_iso['auc_roc']:.4f} PR-AUC={m_iso['pr_auc']:.4f}")
    results["isolation_forest"] = m_iso
    joblib.dump(iso, MODELS_DIR / "isolation_forest.pkl")

    # Save artifacts
    joblib.dump(scaler, MODELS_DIR / "scaler.pkl")
    with open(MODELS_DIR / "feature_names.json", "w") as f:
        json.dump(feature_cols, f, indent=2)
    with open(MODELS_DIR / "scale_indices.json", "w") as f:
        json.dump(scale_indices, f)
    with open(MODELS_DIR / "training_summary.json", "w") as f:
        json.dump({"results": results, "timestamp": pd.Timestamp.now().isoformat()}, f, indent=2, default=str)

    # Evaluation charts (best model)
    best_model = xgb_m if HAS_XGB else lr
    best_label = "xgboost" if HAS_XGB else "logistic_regression"
    probas = best_model.predict_proba(X_test_s)[:,1]

    # ROC
    fpr, tpr, _ = roc_curve(y_test, probas); roc_auc_val = auc(fpr, tpr)
    fig, ax = plt.subplots(figsize=(7,6))
    ax.plot(fpr, tpr, color=C["fraud"], lw=2.5, label=f"{best_label} (AUC={roc_auc_val:.4f})")
    ax.plot([0,1],[0,1], color=C["neutral"], lw=1.2, linestyle="--", label="Random")
    ax.fill_between(fpr, tpr, alpha=0.08, color=C["fraud"])
    ax.set_xlabel("FPR"); ax.set_ylabel("TPR"); ax.set_title(f"ROC Curve AUC={roc_auc_val:.4f}", fontweight="bold")
    ax.legend(loc="lower right"); ax.set_xlim(0,1); ax.set_ylim(0,1.02)
    plt.tight_layout(); save_report("eval_01_roc_curve.png")

    # PR
    prec, rec, _ = precision_recall_curve(y_test, probas); ap = average_precision_score(y_test, probas)
    bl = y_test.sum()/len(y_test)
    fig, ax = plt.subplots(figsize=(7,6))
    ax.plot(rec, prec, color=C["fraud"], lw=2.5, label=f"AP={ap:.4f}")
    ax.axhline(bl, color=C["neutral"], lw=1.2, linestyle="--", label=f"Baseline ({bl:.4%})")
    ax.fill_between(rec, prec, bl, alpha=0.08, color=C["fraud"])
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision"); ax.set_title(f"PR Curve AP={ap:.4f}", fontweight="bold")
    ax.legend(); ax.set_xlim(0,1); ax.set_ylim(0,1.05)
    plt.tight_layout(); save_report("eval_02_pr_curve.png")

    # Confusion matrix
    preds50 = (probas >= 0.5).astype(int)
    cm = confusion_matrix(y_test, preds50); tn, fp, fn, tp = cm.ravel(); total = tn+fp+fn+tp
    cells = [(tn,"True\nNegative","Correct\nlegitimate","#DCFCE7","#166534"),(fp,"False\nPositive","Legit->Fraud","#FEE2E2","#991B1B"),
             (fn,"False\nNegative","Fraud missed","#FEF3C7","#92400E"),(tp,"True\nPositive","Correct\nfraud","#DBEAFE","#1E3A5F")]
    fig, axes = plt.subplots(2,2,figsize=(9,8))
    fig.suptitle("Confusion Matrix (threshold=0.50)", fontweight="bold")
    for ax,(val,title,sub,bg,tc) in zip(axes.flatten(),cells):
        ax.set_facecolor(bg)
        ax.text(0.5,0.60,f"{val:,}",ha="center",va="center",fontsize=36,fontweight="bold",color=tc,transform=ax.transAxes)
        ax.text(0.5,0.30,title,ha="center",va="center",fontsize=13,fontweight="600",color=tc,transform=ax.transAxes)
        ax.text(0.5,0.12,sub,ha="center",va="center",fontsize=9,color=tc,alpha=0.8,transform=ax.transAxes)
        ax.text(0.5,-0.02,f"{val/total:.2%}",ha="center",va="center",fontsize=9,color=tc,alpha=0.7,transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
    plt.tight_layout(); save_report("eval_03_confusion_matrix.png")

    # Threshold sweep
    ts = np.arange(0.01,0.99,0.005)
    f1s,precs,recs = [],[],[]
    for t in ts:
        p = (probas >= t).astype(int)
        f1s.append(f1_score(y_test,p,zero_division=0))
        precs.append(precision_score(y_test,p,zero_division=0))
        recs.append(recall_score(y_test,p,zero_division=0))
    bi = int(np.argmax(f1s)); bt = float(ts[bi])
    fig, ax = plt.subplots(figsize=(11,5))
    ax.plot(ts,f1s,color=C["fraud"],lw=2.2,label="F1")
    ax.plot(ts,precs,color=C["legit"],lw=2.0,label="Precision",linestyle="--")
    ax.plot(ts,recs,color=C["green"],lw=2.0,label="Recall",linestyle="-.")
    ax.axvline(bt,color="#854F0B",linestyle=":",lw=1.5,label=f"Best t={bt:.3f} (F1={f1s[bi]:.4f})")
    ax.set_xlabel("Threshold"); ax.set_ylabel("Score"); ax.set_title("Threshold Sweep",fontweight="bold")
    ax.legend(); ax.set_xlim(0,1); ax.set_ylim(0,1.05)
    plt.tight_layout(); save_report("eval_04_threshold_sweep.png")

    # Feature importance (LR)
    feature_names = ["Time","Amount"] + [f"V{i}" for i in range(1,29)] + [
        "log_amount","is_small_amount","is_round_amount","is_large_amount","hour","is_night","hour_sin","hour_cos","day_period"]
    coefs = lr.coef_[0]; idx = np.argsort(np.abs(coefs))[::-1][:20]
    fig, ax = plt.subplots(figsize=(10,7))
    colors_bar = [C["fraud"] if coefs[i]>0 else C["legit"] for i in idx]
    ax.barh([feature_names[i] for i in idx[::-1]], coefs[idx[::-1]], color=colors_bar[::-1], edgecolor="white", linewidth=0.5)
    ax.axvline(0,color="#888780",lw=1); ax.set_xlabel("Coefficient"); ax.set_title("Feature Importance (LR, top 20)",fontweight="bold")
    plt.tight_layout(); save_report("eval_05_feature_importance.png")

    # Prob distribution
    fig, axes = plt.subplots(1,2,figsize=(13,5))
    fig.suptitle("Predicted Probability Distributions",fontweight="bold")
    axes[0].hist(probas[y_test==0],bins=80,color=C["legit"],alpha=0.65,density=True,label="Legit")
    axes[0].hist(probas[y_test==1],bins=80,color=C["fraud"],alpha=0.75,density=True,label="Fraud")
    axes[0].set_xlabel("P(fraud)"); axes[0].set_ylabel("Density"); axes[0].set_title("Linear"); axes[0].legend()
    axes[1].hist(probas[y_test==0]+1e-9,bins=80,color=C["legit"],alpha=0.65,density=True,label="Legit",log=True)
    axes[1].hist(probas[y_test==1]+1e-9,bins=80,color=C["fraud"],alpha=0.75,density=True,label="Fraud",log=True)
    axes[1].set_xlabel("P(fraud)"); axes[1].set_ylabel("Density (log)"); axes[1].set_title("Log"); axes[1].legend()
    plt.tight_layout(); save_report("eval_06_prob_distribution.png")

    elapsed = time.time() - t0
    print("\n" + "=" * 60)
    print("  ALL DONE")
    print("=" * 60)
    print(f"  Time: {elapsed:.0f}s")
    print(f"  Models saved to: {MODELS_DIR}")
    print(f"  Reports saved to: {REPORTS}")
    print()
    for name, m in results.items():
        print(f"  {name:25s}  PR-AUC: {m.get('pr_auc','-')}  F1: {m.get('f1','-')}")
    print()
    print("  Saved files:")
    for f in sorted(MODELS_DIR.glob("*")):
        size = f.stat().st_size if f.is_file() else 0
        print(f"    {f.name:40s}  {size:>10,} bytes")
