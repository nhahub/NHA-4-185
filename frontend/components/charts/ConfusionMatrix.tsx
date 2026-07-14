"use client";

interface ConfusionMatrixProps {
  /** [[TN, FP], [FN, TP]] */
  matrix: [[number, number], [number, number]];
}

export function ConfusionMatrix({ matrix }: ConfusionMatrixProps) {
  const [[tn, fp], [fn, tp]] = matrix;
  const total = tn + fp + fn + tp;

  const cells = [
    { label: "True Negative",  value: tn, sub: "Correctly identified legitimate", bg: "bg-surface-success",  border: "border-success/30",  text: "text-success" },
    { label: "False Positive", value: fp, sub: "Legitimate flagged as fraud",     bg: "bg-surface-error",    border: "border-error/30",    text: "text-error" },
    { label: "False Negative", value: fn, sub: "Fraud missed by model",           bg: "bg-surface-warning",  border: "border-warning/30",  text: "text-warning" },
    { label: "True Positive",  value: tp, sub: "Correctly identified fraud",      bg: "bg-secondary-container", border: "border-secondary/30", text: "text-secondary" },
  ];

  return (
    <div>
      <div className="grid grid-cols-2 gap-0 border border-outline-variant rounded-xl overflow-hidden">
        {/* Axis labels */}
        <div className="col-span-2 grid grid-cols-3 text-xs text-center font-semibold text-on-surface-dim bg-surface-container border-b border-outline-variant">
          <div className="py-2" />
          <div className="py-2 border-l border-outline-variant">Predicted: Legit</div>
          <div className="py-2 border-l border-outline-variant">Predicted: Fraud</div>
        </div>

        {cells.map((cell, i) => (
          <div
            key={cell.label}
            className={`${cell.bg} ${cell.border} p-5 border relative ${i % 2 === 0 ? "border-r" : ""} ${i < 2 ? "border-b" : ""}`}
          >
            {i === 0 && (
              <div className="absolute -left-0 top-1/2 -translate-y-1/2 text-xs font-semibold text-on-surface-dim transform -rotate-90 translate-x-[-28px]">
                Actual: Legit
              </div>
            )}
            {i === 2 && (
              <div className="absolute -left-0 top-1/2 -translate-y-1/2 text-xs font-semibold text-on-surface-dim transform -rotate-90 translate-x-[-28px]">
                Actual: Fraud
              </div>
            )}
            <p className={`text-3xl font-bold ${cell.text}`}>{value(cell.value)}</p>
            <p className={`text-xs font-semibold ${cell.text} mt-1`}>{cell.label}</p>
            <p className="text-xs text-on-surface-dim mt-0.5">{cell.sub}</p>
            <p className="text-xs text-on-surface-dim mt-1">{((cell.value / total) * 100).toFixed(2)}% of total</p>
          </div>
        ))}
      </div>

      {/* Summary metrics */}
      <div className="grid grid-cols-3 gap-3 mt-4">
        <div className="text-center">
          <p className="text-sm font-bold text-on-surface">
            {tp + tn > 0 ? ((( tp + tn) / total) * 100).toFixed(2) : "—"}%
          </p>
          <p className="text-xs text-on-surface-dim">Accuracy</p>
        </div>
        <div className="text-center">
          <p className="text-sm font-bold text-on-surface">
            {tp + fp > 0 ? ((tp / (tp + fp)) * 100).toFixed(2) : "—"}%
          </p>
          <p className="text-xs text-on-surface-dim">Precision</p>
        </div>
        <div className="text-center">
          <p className="text-sm font-bold text-on-surface">
            {tp + fn > 0 ? ((tp / (tp + fn)) * 100).toFixed(2) : "—"}%
          </p>
          <p className="text-xs text-on-surface-dim">Recall</p>
        </div>
      </div>
    </div>
  );
}

function value(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : n.toLocaleString();
}
