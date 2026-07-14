"use client";

interface ProbabilityGaugeProps {
  probability: number;
  threshold?: number;
  size?: number;
}

export function ProbabilityGauge({ probability, threshold = 0.5, size = 180 }: ProbabilityGaugeProps) {
  const pct = Math.min(Math.max(probability, 0), 1);
  const isFraud = pct >= threshold;

  const cx = size / 2;
  const cy = size / 2 + 10;
  const r  = size * 0.38;
  const strokeW = size * 0.1;

  function polarToXY(angleDeg: number) {
    const rad = ((angleDeg - 180) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function arcPath(startDeg: number, endDeg: number) {
    const s = polarToXY(startDeg);
    const e = polarToXY(endDeg);
    const large = endDeg - startDeg > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
  }

  const fillEnd = 180 * pct;
  const thresholdAngle = 180 * threshold;
  const needleTip = polarToXY(fillEnd);

  const color = isFraud
    ? pct >= 0.95 ? "#DC2626" : pct >= 0.80 ? "#FFB4AB" : "#FCD34D"
    : pct >= 0.35 ? "#FCD34D" : "#86EFAC";

  return (
    <svg width={size} height={size * 0.7} viewBox={`0 0 ${size} ${size * 0.7}`}>
      {/* Track */}
      <path
        d={arcPath(0, 180)}
        fill="none"
        stroke="#1E293B"
        strokeWidth={strokeW}
        strokeLinecap="round"
      />

      {/* Threshold marker */}
      {(() => {
        const t = polarToXY(thresholdAngle);
        const inner = { x: cx + (r - strokeW / 2) * Math.cos(((thresholdAngle - 180) * Math.PI) / 180),
                        y: cy + (r - strokeW / 2) * Math.sin(((thresholdAngle - 180) * Math.PI) / 180) };
        const outer = { x: cx + (r + strokeW / 2) * Math.cos(((thresholdAngle - 180) * Math.PI) / 180),
                        y: cy + (r + strokeW / 2) * Math.sin(((thresholdAngle - 180) * Math.PI) / 180) };
        return <line x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y} stroke="#6E7F98" strokeWidth={2} />;
      })()}

      {/* Fill arc */}
      {pct > 0.01 && (
        <path
          d={arcPath(0, fillEnd)}
          fill="none"
          stroke={color}
          strokeWidth={strokeW}
          strokeLinecap="round"
        />
      )}

      {/* Needle dot */}
      <circle cx={needleTip.x} cy={needleTip.y} r={strokeW * 0.45} fill={color} />

      {/* Center circle */}
      <circle cx={cx} cy={cy} r={strokeW * 0.35} fill="#051424" stroke={color} strokeWidth={2} />

      {/* Percentage label */}
      <text x={cx} y={cy - 4} textAnchor="middle" dominantBaseline="auto"
        fontSize={size * 0.14} fontWeight="700" fill={color}>
        {Math.round(pct * 100)}%
      </text>

      {/* Sub-label */}
      <text x={cx} y={cy + size * 0.1} textAnchor="middle" dominantBaseline="hanging"
        fontSize={size * 0.07} fill="#8B9BB4">
        {isFraud ? "FRAUD" : "LEGITIMATE"}
      </text>

      {/* Scale labels */}
      <text x={cx - r - strokeW * 0.6} y={cy + 4} textAnchor="middle" fontSize={size * 0.06} fill="#6E7F98">0%</text>
      <text x={cx + r + strokeW * 0.6} y={cy + 4} textAnchor="middle" fontSize={size * 0.06} fill="#6E7F98">100%</text>
    </svg>
  );
}
