"use client";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

type Point = { t: number; v: number };

type Props = {
  title: string;
  data: Point[];
  color?: string;
  valueSuffix?: string;
};

export function TrendChart({ title, data, color = "#f06", valueSuffix = "" }: Props) {
  const normalized = data.map((item) => ({
    time: new Date(item.t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    value: Number(item.v.toFixed(2)),
  }));

  return (
    <article className="panel reveal">
      <div className="panel-head">
        <h3>{title}</h3>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={normalized}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke="rgba(255,255,255,0.6)" tick={{ fontSize: 12 }} />
            <YAxis stroke="rgba(255,255,255,0.6)" tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                background: "#111219",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: 12,
              }}
              formatter={(value: number) => `${value}${valueSuffix}`}
            />
            <Line type="monotone" dataKey="value" stroke={color} dot={false} strokeWidth={3} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}
