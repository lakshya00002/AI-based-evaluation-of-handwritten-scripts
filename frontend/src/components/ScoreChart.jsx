import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

export default function ScoreChart({ semantic, keyword, maxScore = 100 }) {
  const semPct = Math.round(Number(semantic) * 100);
  const kwPct = Math.round(Number(keyword) * 100);
  const data = [
    { metric: "Semantic", value: semPct },
    { metric: "Keywords", value: kwPct },
    { metric: "Scale", value: Math.min(100, (semPct + kwPct) / 2) },
  ];

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <RadarChart data={data}>
          <PolarGrid stroke="#e2e8f0" />
          <PolarAngleAxis dataKey="metric" tick={{ fill: "#64748b", fontSize: 12 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#94a3b8" }} />
          <Radar name="Alignment" dataKey="value" stroke="#2563eb" fill="#3b82f6" fillOpacity={0.35} />
        </RadarChart>
      </ResponsiveContainer>
      <p className="text-center text-xs text-slate-500 mt-2">Max assignment score: {maxScore}</p>
    </div>
  );
}
