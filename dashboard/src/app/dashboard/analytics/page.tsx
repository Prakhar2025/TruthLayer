"use client";

import { motion } from "framer-motion";
import {
    BarChart3,
    TrendingUp,
    Clock,
    Shield,
    CheckCircle2,
    AlertTriangle,
    XCircle,
} from "lucide-react";
import { useState, useEffect } from "react";
import {
    getAnalyticsSummary,
    getAnalyticsTrends,
    getRecentVerifications,
    type AnalyticsSummary,
    type TrendData,
} from "@/lib/api";

export default function AnalyticsPage() {
    const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
    const [trends, setTrends] = useState<TrendData[]>([]);
    const [recent, setRecent] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [days, setDays] = useState(7);

    useEffect(() => {
        loadData();
    }, [days]);

    const loadData = async () => {
        setLoading(true);
        try {
            const [s, t, r] = await Promise.all([
                getAnalyticsSummary(),
                getAnalyticsTrends(days),
                getRecentVerifications(10),
            ]);
            setSummary(s);
            setTrends(t.trends);
            setRecent(r.verifications);
        } catch {
            // Demo data
            setSummary({
                total_verifications: 248,
                total_claims: 1492,
                avg_latency_ms: 43.7,
                accuracy_breakdown: { verified: 1089, uncertain: 267, unsupported: 136 },
                verification_rate: 73.0,
            });
            setTrends([
                { date: "2026-02-16", verifications: 28, verified: 85, uncertain: 18, unsupported: 12, avg_latency_ms: 45.2 },
                { date: "2026-02-17", verifications: 35, verified: 108, uncertain: 24, unsupported: 8, avg_latency_ms: 42.1 },
                { date: "2026-02-18", verifications: 42, verified: 132, uncertain: 30, unsupported: 15, avg_latency_ms: 44.8 },
                { date: "2026-02-19", verifications: 31, verified: 94, uncertain: 22, unsupported: 10, avg_latency_ms: 41.3 },
                { date: "2026-02-20", verifications: 38, verified: 118, uncertain: 28, unsupported: 14, avg_latency_ms: 46.1 },
                { date: "2026-02-21", verifications: 45, verified: 141, uncertain: 32, unsupported: 11, avg_latency_ms: 39.8 },
                { date: "2026-02-22", verifications: 29, verified: 89, uncertain: 19, unsupported: 9, avg_latency_ms: 43.5 },
            ]);
            setRecent([
                { verification_id: "v1", total_claims: 5, summary: { verified: 4, uncertain: 1, unsupported: 0 }, latency_ms: 38.2, created_at: Date.now() / 1000 - 600 },
                { verification_id: "v2", total_claims: 3, summary: { verified: 2, uncertain: 0, unsupported: 1 }, latency_ms: 52.1, created_at: Date.now() / 1000 - 3600 },
                { verification_id: "v3", total_claims: 8, summary: { verified: 6, uncertain: 2, unsupported: 0 }, latency_ms: 67.3, created_at: Date.now() / 1000 - 7200 },
            ]);
        }
        setLoading(false);
    };

    if (loading) {
        return (
            <div>
                <h1 style={{ fontSize: "1.6rem", fontWeight: 700, marginBottom: 28 }}>Analytics</h1>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
                    {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="skeleton" style={{ height: 100, borderRadius: 16 }} />
                    ))}
                </div>
                <div className="skeleton" style={{ height: 300, borderRadius: 16 }} />
            </div>
        );
    }

    const maxVerifications = Math.max(...trends.map((t) => t.verifications), 1);

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
                <div>
                    <h1 style={{ fontSize: "1.6rem", fontWeight: 700, marginBottom: 4 }}>Analytics</h1>
                    <p style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                        Verification performance and trends
                    </p>
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                    {[7, 14, 30].map((d) => (
                        <button
                            key={d}
                            onClick={() => setDays(d)}
                            className={days === d ? "btn-primary" : "btn-secondary"}
                            style={{ fontSize: "0.75rem", padding: "6px 14px" }}
                        >
                            {d}d
                        </button>
                    ))}
                </div>
            </div>

            {/* Summary Cards */}
            {summary && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 }}>
                    {[
                        { icon: Shield, label: "Verifications", value: summary.total_verifications, color: "#6366F1" },
                        { icon: BarChart3, label: "Total Claims", value: summary.total_claims, color: "#22C55E" },
                        { icon: Clock, label: "Avg Latency", value: `${summary.avg_latency_ms}ms`, color: "#EAB308" },
                        { icon: TrendingUp, label: "Trust Rate", value: `${summary.verification_rate}%`, color: "#818CF8" },
                    ].map((card, i) => (
                        <motion.div
                            key={card.label}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.08 }}
                            className="glass-card"
                            style={{ padding: "18px 22px" }}
                        >
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                                <span style={{ fontSize: "0.78rem", color: "var(--color-text-secondary)", fontWeight: 500 }}>{card.label}</span>
                                <card.icon size={16} color={card.color} />
                            </div>
                            <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{card.value}</div>
                        </motion.div>
                    ))}
                </div>
            )}

            {/* Trends Chart */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="glass-card"
                style={{ padding: 28, marginBottom: 24 }}
            >
                <h2 style={{ fontSize: "1.05rem", fontWeight: 600, marginBottom: 24 }}>
                    Daily Verifications
                </h2>
                <div style={{ display: "flex", gap: 6, height: 180, alignItems: "flex-end", padding: "0 4px" }}>
                    {trends.map((day) => {
                        const pct = (day.verifications / maxVerifications) * 100;
                        return (
                            <div
                                key={day.date}
                                style={{
                                    flex: 1,
                                    display: "flex",
                                    flexDirection: "column",
                                    alignItems: "center",
                                    gap: 6,
                                }}
                            >
                                <span style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--color-text-secondary)" }}>
                                    {day.verifications}
                                </span>
                                <motion.div
                                    initial={{ height: 0 }}
                                    animate={{ height: `${Math.max(pct * 1.5, 6)}px` }}
                                    transition={{ delay: 0.5, duration: 0.4 }}
                                    style={{
                                        width: "70%",
                                        background: "linear-gradient(180deg, #6366F1, #4F46E5)",
                                        borderRadius: 6,
                                        minHeight: 6,
                                    }}
                                />
                                <span style={{ fontSize: "0.65rem", color: "var(--color-text-secondary)" }}>
                                    {day.date.slice(5)}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </motion.div>

            {/* Accuracy Breakdown + Recent */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                {/* Breakdown */}
                {summary && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="glass-card"
                        style={{ padding: 24 }}
                    >
                        <h2 style={{ fontSize: "1.05rem", fontWeight: 600, marginBottom: 20 }}>
                            Accuracy Breakdown
                        </h2>
                        {[
                            { label: "Verified", value: summary.accuracy_breakdown.verified, icon: CheckCircle2, color: "var(--color-verified)" },
                            { label: "Uncertain", value: summary.accuracy_breakdown.uncertain, icon: AlertTriangle, color: "var(--color-uncertain)" },
                            { label: "Unsupported", value: summary.accuracy_breakdown.unsupported, icon: XCircle, color: "var(--color-unsupported)" },
                        ].map((item) => {
                            const pct = summary.total_claims > 0 ? (item.value / summary.total_claims) * 100 : 0;
                            return (
                                <div key={item.label} style={{ marginBottom: 16 }}>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                            <item.icon size={14} color={item.color} />
                                            <span style={{ fontSize: "0.85rem" }}>{item.label}</span>
                                        </div>
                                        <span style={{ fontSize: "0.85rem", fontWeight: 600, color: item.color }}>
                                            {item.value} ({pct.toFixed(1)}%)
                                        </span>
                                    </div>
                                    <div className="confidence-bar">
                                        <div
                                            className="confidence-bar-fill"
                                            style={{ width: `${pct}%`, background: item.color }}
                                        />
                                    </div>
                                </div>
                            );
                        })}
                    </motion.div>
                )}

                {/* Recent Verifications */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    className="glass-card"
                    style={{ padding: 24 }}
                >
                    <h2 style={{ fontSize: "1.05rem", fontWeight: 600, marginBottom: 20 }}>
                        Recent Verifications
                    </h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                        {recent.map((v) => {
                            const ago = Math.round((Date.now() / 1000 - v.created_at) / 60);
                            const agoText = ago < 60 ? `${ago}m ago` : `${Math.round(ago / 60)}h ago`;
                            return (
                                <div
                                    key={v.verification_id}
                                    style={{
                                        padding: "12px 14px",
                                        borderRadius: 10,
                                        background: "var(--color-bg-primary)",
                                        border: "1px solid var(--color-border)",
                                    }}
                                >
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                                        <div style={{ display: "flex", gap: 8, fontSize: "0.78rem" }}>
                                            <span style={{ color: "var(--color-verified)" }}>✅{v.summary.verified}</span>
                                            <span style={{ color: "var(--color-uncertain)" }}>⚠️{v.summary.uncertain}</span>
                                            <span style={{ color: "var(--color-unsupported)" }}>❌{v.summary.unsupported}</span>
                                        </div>
                                        <span style={{ fontSize: "0.72rem", color: "var(--color-text-secondary)" }}>{agoText}</span>
                                    </div>
                                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "var(--color-text-secondary)" }}>
                                        <span>{v.total_claims} claims</span>
                                        <span>{v.latency_ms}ms</span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
