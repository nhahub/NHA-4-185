"use client";
import {
  ComposedChart, Bar, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

interface DataPoint {
  label: string;
  transactions: number;
  fraud: number;
  fraud_rate?: number;
}

interface FraudTrendChartProps {
  data: DataPoint[];
  title?: string;
  height?: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface-container-high border border-outline-variant rounded-lg p-3 text-xs">
      <p className="font-semibold text-on-surface mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2 mb-1">
          <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: p.color }} />
          <span className="text-on-surface-variant">{p.name}:</span>
          <span className="font-semibold text-on-surface">{p.value?.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
};

export function FraudTrendChart({ data, title = "Transaction Trend", height = 280 }: FraudTrendChartProps) {
  return (
    <div>
      {title && <p className="text-label-lg text-on-surface mb-4">{title}</p>}
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="txGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#0266FF" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#0266FF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#8B9BB4" }} axisLine={false} tickLine={false} />
          <YAxis yAxisId="left"  tick={{ fontSize: 11, fill: "#8B9BB4" }} axisLine={false} tickLine={false} />
          <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: "#FFB4AB" }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "12px" }} />
          <Bar   yAxisId="left"  dataKey="transactions" name="Transactions" fill="#1E3A5F" radius={[3, 3, 0, 0]} />
          <Line  yAxisId="right" dataKey="fraud"        name="Fraud count"  stroke="#FFB4AB" strokeWidth={2} dot={{ r: 3, fill: "#FFB4AB" }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
