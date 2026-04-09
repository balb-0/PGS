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
import { useEffect, useMemo, useState } from "react";

type Point = { t: number; v: number };

type Props = {
  title: string;
  data: Point[];
  color?: string;
  valueSuffix?: string;
};

export function TrendChart({ title, data, color = "#f06", valueSuffix = "" }: Props) {
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  useEffect(() => {
    const applyThemeFromDom = () => {
      const activeTheme = document.documentElement.getAttribute("data-theme");
      if (activeTheme === "light" || activeTheme === "dark") {
        setTheme(activeTheme);
      } else {
        setTheme(window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
      }
    };

    applyThemeFromDom();
    const observer = new MutationObserver(applyThemeFromDom);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  const normalized = useMemo(
    () =>
      data.map((item) => ({
        time: new Date(item.t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        value: Number(item.v.toFixed(2)),
      })),
    [data],
  );

  const axisColor = theme === "light" ? "rgba(22, 36, 41, 0.72)" : "rgba(255,255,255,0.7)";
  const gridColor = theme === "light" ? "rgba(22, 36, 41, 0.16)" : "rgba(255,255,255,0.08)";
  const tooltipStyle =
    theme === "light"
      ? {
          background: "#fbf8f2",
          border: "1px solid rgba(22,36,41,0.24)",
          borderRadius: 12,
          color: "#162429",
        }
      : {
          background: "#111219",
          border: "1px solid rgba(255,255,255,0.2)",
          borderRadius: 12,
          color: "#eaf3f0",
        };

  return (
    <article className="panel reveal">
      <div className="panel-head">
        <h3>{title}</h3>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={normalized}>
            <CartesianGrid stroke={gridColor} strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke={axisColor} tick={{ fontSize: 12 }} />
            <YAxis stroke={axisColor} tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value: number) => `${value}${valueSuffix}`}
            />
            <Line type="monotone" dataKey="value" stroke={color} dot={false} strokeWidth={3} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}
