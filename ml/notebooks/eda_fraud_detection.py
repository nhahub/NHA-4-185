"""
EDA — Credit Card Fraud Detection
Run: python ml/notebooks/eda_fraud_detection.py
Output: ml/reports/eda_*.png
"""
import os, json, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE
warnings.filterwarnings("ignore")

ROOT    = Path(__file__).parents[2]
DATA    = ROOT / "ml" / "data" / "creditcard.csv"
REPORTS = ROOT / "ml" / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)
RANDOM_STATE = 42

C = {"legit":"#378ADD","fraud":"#E24B4A","bg":"#FAFAFA","grid":"#EEEEEE"}
plt.rcParams.update({"font.family":"DejaVu Sans","axes.spines.top":False,
    "axes.spines.right":False,"axes.grid":True,"grid.color":C["grid"],
    "grid.linewidth":0.6,"axes.facecolor":C["bg"],"figure.facecolor":"white"})

def load():
    if not DATA.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA}\n"
            "Download from https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud\n"
            "and place at ml/data/creditcard.csv")
    df = pd.read_csv(DATA)
    print(f"Loaded {df.shape[0]:,} rows  |  fraud rate {df['Class'].mean():.4%}")
    return df

def save(name):
    out = REPORTS / name
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  -> {name}")

# 1. Class distribution
def plot_class_dist(df):
    counts = df["Class"].value_counts().sort_index()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11,4))
    fig.suptitle("1. Class Distribution", fontweight="bold")
    bars = ax1.bar(["Legitimate","Fraud"], counts.values, color=[C["legit"],C["fraud"]], width=0.45)
    for b, v in zip(bars, counts.values):
        ax1.text(b.get_x()+b.get_width()/2, b.get_height()+500,
                 f"{v:,}\n({v/len(df):.3%})", ha="center", fontsize=10)
    ax1.set_ylim(0, counts.max()*1.2); ax1.set_title("Counts")
    ax2.pie(counts.values, labels=["Legitimate","Fraud"], colors=[C["legit"],C["fraud"]],
            autopct="%1.3f%%", startangle=90,
            wedgeprops={"edgecolor":"white","linewidth":2})
    ax2.set_title("Proportion")
    plt.tight_layout(); save("eda_01_class_distribution.png")

# 2. Amount & Time
def plot_amount_time(df):
    lg, fr = df[df["Class"]==0], df[df["Class"]==1]
    fig, axes = plt.subplots(2,2,figsize=(13,9))
    fig.suptitle("2. Amount & Time Analysis", fontweight="bold")
    # amount hist
    ax=axes[0,0]
    ax.hist(lg["Amount"],bins=80,color=C["legit"],alpha=0.6,density=True,label="Legitimate")
    ax.hist(fr["Amount"],bins=80,color=C["fraud"],alpha=0.75,density=True,label="Fraud")
    ax.set_xlim(0,500); ax.set_xlabel("Amount ($)"); ax.set_title("Amount density"); ax.legend()
    # boxplot
    ax=axes[0,1]
    bp=ax.boxplot([lg["Amount"].clip(0,500),fr["Amount"].clip(0,500)],
                  labels=["Legitimate","Fraud"],patch_artist=True,
                  medianprops={"color":"white","linewidth":2})
    bp["boxes"][0].set_facecolor(C["legit"]); bp["boxes"][1].set_facecolor(C["fraud"])
    ax.set_ylabel("Amount ($, clipped 500)"); ax.set_title("Amount boxplot")
    # CDF
    ax=axes[1,0]
    for cls,col,lbl in [(0,C["legit"],"Legitimate"),(1,C["fraud"],"Fraud")]:
        v=df[df["Class"]==cls]["Amount"].sort_values()
        ax.plot(v.values,np.linspace(0,1,len(v)),color=col,lw=2,label=lbl)
    ax.set_xlim(0,1000); ax.set_xlabel("Amount ($)"); ax.set_ylabel("CDF"); ax.legend()
    ax.set_title("Amount CDF")
    # time hist
    ax=axes[1,1]
    ax.hist(lg["Time"]/3600,bins=48,color=C["legit"],alpha=0.6,density=True,label="Legitimate")
    ax.hist(fr["Time"]/3600,bins=48,color=C["fraud"],alpha=0.75,density=True,label="Fraud")
    ax.set_xlabel("Hours since first tx"); ax.set_title("Time distribution"); ax.legend()
    plt.tight_layout(); save("eda_02_amount_time.png")

# 3. Top discriminating V features
def plot_top_features(df):
    lg,fr=df[df["Class"]==0],df[df["Class"]==1]
    vcols=[f"V{i}" for i in range(1,29)]
    top8=sorted(vcols,key=lambda c:abs(lg[c].mean()-fr[c].mean()),reverse=True)[:8]
    fig,axes=plt.subplots(2,4,figsize=(15,7))
    fig.suptitle("3. Top 8 Discriminating PCA Features",fontweight="bold")
    for ax,feat in zip(axes.flatten(),top8):
        ax.hist(lg[feat],bins=60,color=C["legit"],alpha=0.6,density=True,label="Legit")
        ax.hist(fr[feat],bins=60,color=C["fraud"],alpha=0.7,density=True,label="Fraud")
        ax.set_title(feat,fontweight="500"); ax.legend(fontsize=8)
    plt.tight_layout(); save("eda_03_top_features.png")

# 4. Correlation heatmap
def plot_correlation(df):
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
    ax.set_title("4. Correlation Heatmap  (gold = |corr w/ Class| > 0.1)",
                 fontsize=12,fontweight="bold")
    plt.tight_layout(); save("eda_04_correlation_heatmap.png")

# 5. SMOTE before/after
def plot_smote(df):
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
    plt.tight_layout(); save("eda_05_smote_comparison.png")

# 6. Time-series fraud rate
def plot_timeseries(df):
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
    plt.tight_layout(); save("eda_06_timeseries.png")

# 7. Summary JSON
def export_summary(df):
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
    out=REPORTS/"eda_summary.json"
    with open(out,"w") as f: json.dump(s,f,indent=2)
    print(f"  -> eda_summary.json")

if __name__=="__main__":
    print("\n=== EDA: Credit Card Fraud Detection ===\n")
    df=load()
    print("[1/7] Class distribution...")     ; plot_class_dist(df)
    print("[2/7] Amount & Time...")           ; plot_amount_time(df)
    print("[3/7] Top features...")            ; plot_top_features(df)
    print("[4/7] Correlation heatmap...")     ; plot_correlation(df)
    print("[5/7] SMOTE comparison...")        ; plot_smote(df)
    print("[6/7] Time-series fraud rate...")  ; plot_timeseries(df)
    print("[7/7] Summary JSON...")            ; export_summary(df)
    print(f"\n✓ Done — charts in {REPORTS}\n")
