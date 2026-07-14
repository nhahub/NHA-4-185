"""
Run EDA + Train Models + Evaluate + Save to ml/models/
"""
import os, json, warnings, time
import numpy as np
import pandas as pd
import joblib
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, f1_score, precision_score, recall_score,
    average_precision_score, matthews_corrcoef, matthews_corrcoef,
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
RANDOM_STATE = 42

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("[Warning] XGBoost not installed")

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    print("[Warning] SHAP not installed")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

try:
    from sklearn.inspection import permutation_importance
except ImportError:
    pass


C = {"legit":"#378ADD","fraud":"#E24B4A","bg":"#FAFAFA","grid":"#EEEEEE","green":"#22C55E","neutral":"#888780"}
plt.rcParams.update({"font.family":"DejaVu Sans","axes.spines.top":False,
    "axes.spines.right":False,"axes.grid":True,"grid.color":C["grid"],
    "grid.linewidth":0.6,"axes.facecolor":C["bg"],"figure.facecolor":"white"})


def save_report(name):
    out = REPORTS / name
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  -> {name}")


# ══════════════════════════════════════════════════════════════
# EDA
# ══════════════════════════════════════════════════════════════
def run_eda(df):
    print("\n" + "="*60)
    print("  PART 1: EXPLORATORY DATA ANALYSIS")
    print("="*60)

    # 1. Class distribution
    counts = df["Class"].value_counts().sort_index()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    fig.suptitle("1. Class Distribution", fontweight="bold")
    bars = ax1.bar(["Legitimate", "Fraud"], counts.values, color=[C["legit"], C["fraud"]], width=0.45)
    for b, v in zip(bars, counts.values):
        ax1.text(b.get_x()+b.get_width()/2, b.get_height()+500,
                 f"{v:,}\n({v/len(df):.3%})", ha="center", fontsize=10)
    ax1.set_ylim(0, counts.max()*1.2); ax1.set_title("Counts")
    ax2.pie(counts.values, labels=["Legitimate", "Fraud"], colors=[C["legit"], C["fraud"]],
            autopct="%1.3f%%", startangle=90, wedgeprops={"edgecolor":"white","linewidth":2})
    ax2.set_title("Proportion")
    plt.tight_layout(); save_report("eda_01_class_distribution.png")
    print("[1/7] Class distribution done")

    # 2. Amount & Time
    from matplotlib.patches import FancyBboxPatch
    lg, fr = df[df["Class"]==0], df[df["Class"]==1]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle("2. Amount & Time Analysis", fontweight="bold")
    ax=axes[0,0]
    ax.hist(lg["Amount"],bins=80,color=C["legit"],alpha=0.6,density=True,label="Legitimate")
    ax.hist(fr["Amount"],bins=80,color=C["fraud"],alpha=0.75,density=True,label="Fraud")
    ax.set_xlim(0,500); ax.set_xlabel("Amount ($)"); ax.set_title("Amount density"); ax.legend()
    ax=axes[0,1]
    bp=ax.boxplot([lg["Amount"].clip(0,500),fr["Amount"].clip(0,500)],
                  tick_labels=["Legitimate","Fraud"],patch_artist=True,
                  medianprops={"color":"white","linewidth":2})
    bp["boxes"][0].set_facecolor(C["legit"]); bp["boxes"][1].set_facecolor(C["fraud"])
    ax.set_ylabel("Amount ($, clipped 500)"); ax.set_title("Amount boxplot")
    ax=axes[1,0]
    for cls,col,lbl in [(0,C["legit"],"Legitimate"),(1,C["fraud"],"Fraud")]:
        v=df[df["Class"]==cls]["Amount"].sort_values()
        ax.plot(v.values,np.linspace(0,1,len(v)),color=col,lw=2,label=lbl)
    ax.set_xlim(0,1000); ax.set_xlabel("Amount ($)"); ax.set_ylabel("CDF"); ax.legend()
    ax.set_title("Amount CDF")
    ax=axes[1,1]
    ax.hist(lg["Time"]/3600,bins=48,color=C["legit"],alpha=0.6,density=True,label="Legitimate")
    ax.hist(fr["Time"]/3600,bins=48,color=C["fraud"],alpha=0.75,density=True,label="Fraud")
    ax.set_xlabel("Hours since first tx"); ax.set_title("Time distribution"); ax.legend()
    plt.tight_layout(); save_report("eda_02_amount_time.png")
    print("[2/7] Amount & Time done")

    # 3. Top features
    vcols=[f"V{i}" for i in range(1,29)]
    top8=sorted(vcols,key=lambda c:abs(lg[c].mean()-fr[c].mean()),reverse=True)[:8]
    fig,axes=plt.subplots(2,4,figsize=(15,7))
    fig.suptitle("3. Top 8 Discriminating PCA Features",fontweight="bold")
    for ax,feat in zip(axes.flatten(),top8):
        ax.hist(lg[feat],bins=60,color=C["legit"],alpha=0.6,density=True,label="Legit")
        ax.hist(fr[feat],bins=60,color=C["fraud"],alpha=0.7,density=True,label="Fraud")
        ax.set_title(feat,fontweight="500"); ax.legend(fontsize=8)
    plt.tight_layout(); save_report("eda_03_top_features.png")
    print("[3/7] Top features done")

    # 4. Correlation heatmap
    cols=[f"V{i}" for i in range(1,29)]+["Amount","Time","Class"]
    corr=df[cols].corr()
    fig,ax=plt.subplots(figsize=(16,13))
    im=ax.imshow(corr.values,cmap="RdBu_r",vmin=-1,vmax=1,aspect="auto")
    ax.set_xticks(range(len(cols))); ax.set_yticks(range(len(cols)))
    ax.set_xticklabels(cols,rotation=45,ha="right",fontsize=8)
    ax.set_yticklabels(cols,fontsize=8)
    ci=cols.index("Class")
    for i in range(len(cols)):
        if abs(corr.values[i,ci])>0.1:
            ax.add_patch(FancyBboxPatch((ci-.48,i-.48),.96,.96,
                boxstyle="round,pad=0.02",edgecolor="#FFD700",facecolor="none",lw=2))
    plt.colorbar(im,ax=ax,fraction=0.02,pad=0.02)
    ax.set_title("4. Correlation Heatmap  (gold = |corr w/ Class| > 0.1)",fontsize=12,fontweight="bold")
    plt.tight_layout(); save_report("eda_04_correlation_heatmap.png")
    print("[4/7] Correlation heatmap done")

    # 5. SMOTE comparison
    X=df.drop("Class",axis=1).values; y=df["Class"].values
    sc=StandardScaler(); X[:,:2]=sc.fit_transform(X[:,:2])
    Xtr,_,ytr,_=train_test_split(X,y,test_size=0.2,stratify=y,random_state=RANDOM_STATE)
    Xr,yr=SMOTE(k_neighbors=5,random_state=RANDOM_STATE).fit_resample(Xtr,ytr)
    before={0:(ytr==0).sum(),1:(ytr==1).sum()}
    after ={0:(yr ==0).sum(),1:(yr ==1).sum()}
    fig,axes=plt.subplots(1,3,figsize=(14,5))
    fig.suptitle("5. SMOTE: Class Balance Before & After",fontweight="bold")
    labels=["Legitimate","Fraud"]; colors=[C["legit"],C["fraud"]]
    for ax,data,title in [(axes[0],before,"Before SMOTE"),(axes[1],after,"After SMOTE")]:
        bars=ax.bar(labels,[data[0],data[1]],color=colors,width=0.45)
        ax.set_title(title); ax.set_ylabel("Count")
        for b,v in zip(bars,[data[0],data[1]]):
            ax.text(b.get_x()+b.get_width()/2,b.get_height()*1.02,f"{v:,}",ha="center",fontsize=10)
    ax=axes[2]
    rb=[before[0]/sum(before.values()),before[1]/sum(before.values())]
    ra=[after[0] /sum(after.values()), after[1] /sum(after.values())]
    x=np.arange(2); w=0.32
    b1=ax.bar(x-w/2,rb,w,color=colors,alpha=0.55,label="Before")
    b2=ax.bar(x+w/2,ra,w,color=colors,alpha=1.0, label="After")
    ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_ylabel("Proportion")
    ax.set_title("Class ratio comparison"); ax.set_ylim(0,1.15); ax.legend()
    for brs in [b1,b2]:
        for b in brs:
            ax.text(b.get_x()+b.get_width()/2,b.get_height()+0.01,
                    f"{b.get_height():.1%}",ha="center",fontsize=8)
    plt.tight_layout(); save_report("eda_05_smote_comparison.png")
    print("[5/7] SMOTE comparison done")

    # 6. Time-series fraud rate
    d=df.copy(); d["hb"]=(d["Time"]//3600).astype(int)
    g=d.groupby("hb").agg(total=("Class","count"),fraud=("Class","sum")).reset_index()
    g["rate"]=g["fraud"]/g["total"]
    fig,axes=plt.subplots(3,1,figsize=(13,10),sharex=True)
    fig.suptitle("6. Transaction Patterns Over Time",fontweight="bold")
    axes[0].fill_between(g["hb"],g["total"],alpha=0.4,color=C["legit"])
    axes[0].plot(g["hb"],g["total"],color=C["legit"],lw=1.5)
    axes[0].set_ylabel("Volume"); axes[0].set_title("Total transactions / hour")
    axes[1].fill_between(g["hb"],g["fraud"],alpha=0.5,color=C["fraud"])
    axes[1].plot(g["hb"],g["fraud"],color=C["fraud"],lw=1.5)
    axes[1].set_ylabel("Count"); axes[1].set_title("Fraud count / hour")
    axes[2].fill_between(g["hb"],g["rate"],alpha=0.4,color="#E24B4A")
    axes[2].plot(g["hb"],g["rate"],color="#A32D2D",lw=1.5)
    axes[2].axhline(g["rate"].mean(),color="#854F0B",linestyle="--",lw=1.2,
                    label=f"Mean {g['rate'].mean():.4%}")
    axes[2].yaxis.set_major_formatter(plt.FuncFormatter(lambda x,_:f"{x:.2%}"))
    axes[2].set_xlabel("Hours"); axes[2].set_ylabel("Rate"); axes[2].legend()
    axes[2].set_title("Fraud rate / hour")
    plt.tight_layout(); save_report("eda_06_timeseries.png")
    print("[6/7] Time-series done")

    # 7. Summary
    s={
        "total_rows":int(len(df)),"fraud_count":int(df["Class"].sum()),
        "legitimate_count":int((df["Class"]==0).sum()),
        "fraud_rate_pct":round(float(df["Class"].mean()*100),4),
        "missing_values":int(df.isnull().sum().sum()),
        "duplicate_rows":int(df.duplicated().sum()),
        "amount":{"min":round(float(df["Amount"].min()),2),
                  "max":round(float(df["Amount"].max()),2),
                  "mean":round(float(df["Amount"].mean()),2),
                  "median":round(float(df["Amount"].median()),2)},
    }
    with open(REPORTS/"eda_summary.json","w") as f: json.dump(s,f,indent=2)
    print("[7/7] Summary JSON saved")
    print("  EDA complete -> ml/reports/")


# ══════════════════════════════════════════════════════════════
# Feature Engineering
# ══════════════════════════════════════════════════════════════
def engineer_features(df):
    df = df.copy()
    df["log_amount"]      = np.log1p(df["Amount"])
    df["is_small_amount"] = (df["Amount"] < 10).astype(int)
    df["is_round_amount"] = (df["Amount"] % 10 == 0).astype(int)
    df["is_large_amount"] = (df["Amount"] > 1000).astype(int)
    df["hour"]     = (df["Time"] % 86400 // 3600).astype(int)
    df["is_night"] = df["hour"].isin([0, 1, 2, 3, 4, 5]).astype(int)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    def get_period(h):
        if h < 6:   return 0
        if h < 12:  return 1
        if h < 18:  return 2
        return 3
    df["day_period"] = df["hour"].apply(get_period)

    v_cols  = [f"V{i}" for i in range(1, 29)]
    eng_cols = ["log_amount","is_small_amount","is_round_amount","is_large_amount",
                "hour","is_night","hour_sin","hour_cos","day_period"]
    feature_cols = ["Time", "Amount"] + v_cols + eng_cols
    return df, feature_cols


def scale_features(X_train, X_val, X_test, feature_cols):
    scale_indices = [
        feature_cols.index("Time"), feature_cols.index("Amount"),
        feature_cols.index("log_amount"), feature_cols.index("hour"),
        feature_cols.index("hour_sin"), feature_cols.index("hour_cos"),
        feature_cols.index("day_period"),
    ]
    scaler = RobustScaler()
    X_train_s = X_train.copy(); X_val_s = X_val.copy(); X_test_s = X_test.copy()
    X_train_s[:, scale_indices] = scaler.fit_transform(X_train[:, scale_indices])
    X_val_s[:, scale_indices]   = scaler.transform(X_val[:, scale_indices])
    X_test_s[:, scale_indices]  = scaler.transform(X_test[:, scale_indices])
    return X_train_s, X_val_s, X_test_s, scaler, scale_indices


# ══════════════════════════════════════════════════════════════
# TRAIN + EVALUATE
# ══════════════════════════════════════════════════════════════
def optimize_threshold(model, X_val, y_val):
    probas = model.predict_proba(X_val)[:, 1]
    best_t, best_f1 = 0.5, 0.0
    for t in np.arange(0.05, 0.95, 0.005):
        preds = (probas >= t).astype(int)
        f = f1_score(y_val, preds, zero_division=0)
        if f > best_f1:
            best_f1 = f; best_t = float(t)
    return best_t, best_f1


def evaluate_model(model, X_test, y_test, threshold, label):
    probas = model.predict_proba(X_test)[:, 1]
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
        "confusion_matrix": {"tn":int(tn),"fp":int(fp),"fn":int(fn),"tp":tp},
    }


def train_and_evaluate(df, feature_cols):
    print("\n" + "="*60)
    print("  PART 2: MODEL TRAINING & EVALUATION")
    print("="*60)

    df_eng, _ = engineer_features(df)
    n = len(df_eng)
    train_end = int(n * 0.70); val_end = int(n * 0.80)

    df_train = df_eng.iloc[:train_end]
    df_val   = df_eng.iloc[train_end:val_end]
    df_test  = df_eng.iloc[val_end:]

    X_train = df_train[feature_cols].values;  y_train = df_train["Class"].values
    X_val   = df_val[feature_cols].values;    y_val   = df_val["Class"].values
    X_test  = df_test[feature_cols].values;   y_test  = df_test["Class"].values

    X_train_s, X_val_s, X_test_s, scaler, scale_indices = scale_features(
        X_train, X_val, X_test, feature_cols)

    smote = SMOTE(k_neighbors=5, random_state=RANDOM_STATE, n_jobs=-1)
    X_res, y_res = smote.fit_resample(X_train_s, y_train)
    print(f"  SMOTE: {len(X_train_s):,} -> {len(X_res):,} rows")

    results = {}

    # ── Logistic Regression ──────────────────────────────────
    print("\n--- Training Logistic Regression ---")
    lr = LogisticRegression(solver="saga", class_weight="balanced",
                            max_iter=2000, random_state=RANDOM_STATE, n_jobs=-1)
    lr.fit(X_res, y_res)
    t_lr, f1_lr = optimize_threshold(lr, X_val_s, y_val)
    m_lr = evaluate_model(lr, X_test_s, y_test, t_lr, "logistic_regression")
    print(f"  F1: {m_lr['f1']:.4f} | AUC-ROC: {m_lr['auc_roc']:.4f} | PR-AUC: {m_lr['pr_auc']:.4f} | threshold: {t_lr:.3f}")
    results["logistic_regression"] = m_lr

    joblib.dump(lr, MODELS_DIR / "logistic_regression.pkl")

    # ── XGBoost ──────────────────────────────────────────────
    if HAS_XGB:
        print("\n--- Training XGBoost ---")
        if HAS_OPTUNA:
            orig_ratio = round((284315 - 492) / 492)
            def objective(trial):
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 200, 600),
                    "max_depth": trial.suggest_int("max_depth", 3, 8),
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                    "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                    "gamma": trial.suggest_float("gamma", 0, 5),
                }
                m = xgb.XGBClassifier(**params, scale_pos_weight=orig_ratio,
                    eval_metric="aucpr", random_state=RANDOM_STATE, n_jobs=-1, verbosity=0)
                m.fit(X_res, y_res, eval_set=[(X_val_s, y_val)], verbose=False)
                return average_precision_score(y_val, m.predict_proba(X_val_s)[:, 1])

            study = optuna.create_study(direction="maximize",
                sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
            study.optimize(objective, n_trials=30, show_progress_bar=False)
            best_params = study.best_params
            print(f"  Optuna best PR-AUC (val): {study.best_value:.4f}")
        else:
            best_params = {"n_estimators":500,"max_depth":6,"learning_rate":0.05,
                "subsample":0.8,"colsample_bytree":0.8,"min_child_weight":5,"gamma":0}

        xgb_model = xgb.XGBClassifier(**best_params, scale_pos_weight=orig_ratio,
            eval_metric="aucpr", random_state=RANDOM_STATE, n_jobs=-1, verbosity=0)
        xgb_model.fit(X_res, y_res, eval_set=[(X_val_s, y_val)], verbose=False)
        t_xgb, f1_xgb = optimize_threshold(xgb_model, X_val_s, y_val)
        m_xgb = evaluate_model(xgb_model, X_test_s, y_test, t_xgb, "xgboost")
        print(f"  F1: {m_xgb['f1']:.4f} | AUC-ROC: {m_xgb['auc_roc']:.4f} | PR-AUC: {m_xgb['pr_auc']:.4f} | threshold: {t_xgb:.3f}")
        m_xgb["hyperparams"] = best_params
        results["xgboost"] = m_xgb

        joblib.dump(xgb_model, MODELS_DIR / "xgboost.pkl")

        # SHAP
        if HAS_SHAP:
            print("  Building SHAP explainer...")
            try:
                explainer = shap.TreeExplainer(xgb_model)
                sample_size = min(2000, len(X_res))
                rng = np.random.default_rng(RANDOM_STATE)
                idx = rng.choice(len(X_res), size=sample_size, replace=False)
                shap_vals = explainer.shap_values(X_res[idx])
                if isinstance(shap_vals, list):
                    shap_vals = shap_vals[1]
                mean_abs = np.abs(shap_vals).mean(axis=0)
                importance = {feature_cols[i]: round(float(mean_abs[i]), 6)
                              for i in range(len(feature_cols))}
                importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
                joblib.dump(explainer, MODELS_DIR / "xgboost_shap_explainer.pkl")
                with open(MODELS_DIR / "xgboost_shap_importance.json", "w") as f:
                    json.dump(importance, f, indent=2)
                print("  SHAP saved")
            except Exception as e:
                print(f"  SHAP failed: {e}")

    # ── Isolation Forest ─────────────────────────────────────
    print("\n--- Training Isolation Forest ---")
    iso = IsolationForest(n_estimators=200, contamination=492/284807,
                          random_state=RANDOM_STATE, n_jobs=-1)
    iso.fit(X_train_s)
    scores = -iso.score_samples(X_test_s)
    iso_preds = np.where(iso.predict(X_test_s) == -1, 1, 0)
    cm = confusion_matrix(y_test, iso_preds)
    tn, fp, fn, tp = cm.ravel()
    m_iso = {
        "algorithm": "isolation_forest",
        "auc_roc":   round(float(roc_auc_score(y_test, scores)), 4),
        "pr_auc":    round(float(average_precision_score(y_test, scores)), 4),
        "precision": round(float(precision_score(y_test, iso_preds, zero_division=0)), 4),
        "recall":    round(float(recall_score(y_test, iso_preds, zero_division=0)), 4),
        "f1":        round(float(f1_score(y_test, iso_preds, zero_division=0)), 4),
        "confusion_matrix": {"tn":int(tn),"fp":int(fp),"fn":int(fn),"tp":int(tp)},
    }
    print(f"  F1: {m_iso['f1']:.4f} | AUC-ROC: {m_iso['auc_roc']:.4f} | PR-AUC: {m_iso['pr_auc']:.4f}")
    results["isolation_forest"] = m_iso
    joblib.dump(iso, MODELS_DIR / "isolation_forest.pkl")

    # ── Save scaler ──────────────────────────────────────────
    joblib.dump(scaler, MODELS_DIR / "scaler.pkl")
    with open(MODELS_DIR / "feature_names.json", "w") as f:
        json.dump(feature_cols, f, indent=2)
    with open(MODELS_DIR / "scale_indices.json", "w") as f:
        json.dump(scale_indices, f)

    return results, X_test_s, y_test, lr, xgb_model if HAS_XGB else None


# ══════════════════════════════════════════════════════════════
# EVALUATION CHARTS
# ══════════════════════════════════════════════════════════════
def run_evaluation_charts(model, X_test, y_test, label="logistic_regression"):
    print("\n" + "="*60)
    print("  PART 3: EVALUATION CHARTS")
    print("="*60)
    probas = model.predict_proba(X_test)[:, 1]

    # 1. ROC
    fpr, tpr, _ = roc_curve(y_test, probas)
    roc_auc_val = auc(fpr, tpr)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(fpr, tpr, color=C["fraud"], lw=2.5, label=f"{label}  (AUC = {roc_auc_val:.4f})")
    ax.plot([0, 1], [0, 1], color=C["neutral"], lw=1.2, linestyle="--", label="Random")
    ax.fill_between(fpr, tpr, alpha=0.08, color=C["fraud"])
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title(f"1. ROC Curve  —  AUC = {roc_auc_val:.4f}", fontweight="bold")
    ax.legend(loc="lower right"); ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    plt.tight_layout(); save_report("eval_01_roc_curve.png")

    # 2. PR curve
    prec, rec, _ = precision_recall_curve(y_test, probas)
    ap = average_precision_score(y_test, probas)
    baseline = y_test.sum() / len(y_test)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(rec, prec, color=C["fraud"], lw=2.5, label=f"{label}  (AP = {ap:.4f})")
    ax.axhline(baseline, color=C["neutral"], lw=1.2, linestyle="--", label=f"Baseline ({baseline:.4%})")
    ax.fill_between(rec, prec, baseline, alpha=0.08, color=C["fraud"])
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
    ax.set_title(f"2. Precision-Recall  —  AP = {ap:.4f}", fontweight="bold")
    ax.legend(); ax.set_xlim(0, 1); ax.set_ylim(0, 1.05)
    plt.tight_layout(); save_report("eval_02_pr_curve.png")

    # 3. Confusion matrix
    preds = (probas >= 0.5).astype(int)
    cm = confusion_matrix(y_test, preds)
    tn, fp, fn, tp = cm.ravel()
    total = tn + fp + fn + tp
    cells = [
        (tn,"True\nNegative","Correctly identified\nlegitimate","#DCFCE7","#166534"),
        (fp,"False\nPositive","Legitimate flagged\nas fraud","#FEE2E2","#991B1B"),
        (fn,"False\nNegative","Fraud missed\nby model","#FEF3C7","#92400E"),
        (tp,"True\nPositive","Correctly identified\nfraud","#DBEAFE","#1E3A5F"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(9, 8))
    fig.suptitle("3. Confusion Matrix  (threshold = 0.50)", fontweight="bold", fontsize=13)
    for ax, (val, title, sub, bg, tc) in zip(axes.flatten(), cells):
        ax.set_facecolor(bg)
        ax.text(0.5, 0.60, f"{val:,}", ha="center", va="center", fontsize=36, fontweight="bold", color=tc, transform=ax.transAxes)
        ax.text(0.5, 0.30, title, ha="center", va="center", fontsize=13, fontweight="600", color=tc, transform=ax.transAxes)
        ax.text(0.5, 0.12, sub, ha="center", va="center", fontsize=9, color=tc, alpha=0.8, transform=ax.transAxes)
        ax.text(0.5, -0.02, f"{val/total:.2%} of total", ha="center", va="center", fontsize=9, color=tc, alpha=0.7, transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor("#CBD5E1"); spine.set_linewidth(1)
    plt.tight_layout(); save_report("eval_03_confusion_matrix.png")

    # 4. Threshold sweep
    thresholds = np.arange(0.01, 0.99, 0.005)
    f1s, precs, recs = [], [], []
    for t in thresholds:
        p = (probas >= t).astype(int)
        f1s.append(f1_score(y_test, p, zero_division=0))
        precs.append(precision_score(y_test, p, zero_division=0))
        recs.append(recall_score(y_test, p, zero_division=0))
    best_idx = int(np.argmax(f1s)); best_t = float(thresholds[best_idx])
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(thresholds, f1s, color=C["fraud"], lw=2.2, label="F1 Score")
    ax.plot(thresholds, precs, color=C["legit"], lw=2.0, label="Precision", linestyle="--")
    ax.plot(thresholds, recs, color=C["green"], lw=2.0, label="Recall", linestyle="-.")
    ax.axvline(best_t, color="#854F0B", linestyle=":", lw=1.5, label=f"Best t={best_t:.3f} (F1={f1s[best_idx]:.4f})")
    ax.set_xlabel("Decision threshold"); ax.set_ylabel("Score")
    ax.set_title("4. Threshold Sweep", fontweight="bold")
    ax.legend(); ax.set_xlim(0, 1); ax.set_ylim(0, 1.05)
    plt.tight_layout(); save_report("eval_04_threshold_sweep.png")

    # 5. Feature importance
    if hasattr(model, "coef_"):
        feature_names = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)] + [
            "log_amount","is_small_amount","is_round_amount","is_large_amount",
            "hour","is_night","hour_sin","hour_cos","day_period"]
        coefs = model.coef_[0]
        idx = np.argsort(np.abs(coefs))[::-1][:20]
        fig, ax = plt.subplots(figsize=(10, 7))
        colors_bar = [C["fraud"] if coefs[i] > 0 else C["legit"] for i in idx]
        ax.barh([feature_names[i] for i in idx[::-1]], coefs[idx[::-1]], color=colors_bar[::-1], edgecolor="white", linewidth=0.5)
        ax.axvline(0, color="#888780", lw=1)
        ax.set_xlabel("Coefficient")
        ax.set_title("5. Feature Importance (top 20)", fontweight="bold")
        plt.tight_layout(); save_report("eval_05_feature_importance.png")

    # 6. Probability distribution
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("6. Predicted Probability Distributions", fontweight="bold")
    axes[0].hist(probas[y_test==0], bins=80, color=C["legit"], alpha=0.65, density=True, label="Legit")
    axes[0].hist(probas[y_test==1], bins=80, color=C["fraud"], alpha=0.75, density=True, label="Fraud")
    axes[0].set_xlabel("Predicted fraud probability"); axes[0].set_ylabel("Density")
    axes[0].set_title("Linear scale"); axes[0].legend()
    axes[1].hist(probas[y_test==0]+1e-9, bins=80, color=C["legit"], alpha=0.65, density=True, label="Legit", log=True)
    axes[1].hist(probas[y_test==1]+1e-9, bins=80, color=C["fraud"], alpha=0.75, density=True, label="Fraud", log=True)
    axes[1].set_xlabel("Predicted fraud probability"); axes[1].set_ylabel("Density (log)")
    axes[1].set_title("Log scale"); axes[1].legend()
    plt.tight_layout(); save_report("eval_06_prob_distribution.png")

    print("  Evaluation charts complete -> ml/reports/")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    t0 = time.time()
    print("\n" + "█"*60)
    print("  FraudShield: EDA + Training + Evaluation")
    print("█"*60)

    print(f"\nLoading data from {DATA}...")
    df = pd.read_csv(DATA)
    before = len(df)
    df = df.dropna(subset=["Class"]).reset_index(drop=True)
    df["Class"] = df["Class"].astype(int)
    removed = before - len(df)
    if removed:
        print(f"  Dropped {removed} rows with NaN in Class column")
    print(f"Loaded {df.shape[0]:,} rows | fraud rate {df['Class'].mean():.4%}")

    # EDA
    run_eda(df)

    # Train + Evaluate
    _, feature_cols = engineer_features(df)
    results, X_test_s, y_test, lr_model, xgb_model = train_and_evaluate(df, feature_cols)

    # Evaluation charts for best model
    best_model = xgb_model if xgb_model is not None else lr_model
    best_label = "xgboost" if xgb_model is not None else "logistic_regression"
    run_evaluation_charts(best_model, X_test_s, y_test, best_label)

    # Summary
    summary = {
        "models_dir": str(MODELS_DIR),
        "reports_dir": str(REPORTS),
        "results": results,
        "saved_files": [f.name for f in MODELS_DIR.glob("*")],
    }
    with open(MODELS_DIR / "training_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    elapsed = time.time() - t0
    print("\n" + "="*60)
    print("  ALL DONE")
    print("="*60)
    print(f"  Time: {elapsed:.0f}s")
    print(f"  Models saved to: {MODELS_DIR}")
    print(f"  Reports saved to: {REPORTS}")
    print()
    for name, m in results.items():
        print(f"  {name:25s}  PR-AUC: {m.get('pr_auc','—')}  F1: {m.get('f1','—')}")
    print()
    print(f"  Saved files:")
    for f in sorted(MODELS_DIR.glob("*")):
        size = f.stat().st_size if f.is_file() else 0
        print(f"    {f.name:40s}  {size:>10,} bytes")
    print()
