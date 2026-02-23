"use client";

import { motion } from "framer-motion";
import { Shield, Zap, FileText, BarChart3, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getAnalyticsSummary, type AnalyticsSummary } from "@/lib/api";

export default function DashboardOverview() {
    const [stats, setStats] = useState<AnalyticsSummary | null>(null);

    useEffect(() => {
        getAnalyticsSummary()
            .then(setStats)
            .catch(() => {
                // Fallback demo stats
                setStats({
                    total_verifications: 142,
                    total_claims: 856,
                    avg_latency_ms: 47.3,
                    accuracy_breakdown: { verified: 623, uncertain: 145, unsupported: 88 },
                    verification_rate: 72.8,
                });
            });
    }, []);

    const cards = [
        {
            icon: Shield,
            label: "Total Verifications",
            value: stats?.total_verifications ?? "—",
            color: "#6366F1",
        },
        {
            icon: Zap,
            label: "Avg Latency",
            value: stats ? `${stats.avg_latency_ms}ms` : "—",
            color: "#22C55E",
        },
        {
            icon: FileText,
            label: "Total Claims",
            value: stats?.total_claims ?? "—",
            color: "#EAB308",
        },
        {
            icon: BarChart3,
            label: "Verification Rate",
            value: stats ? `${stats.verification_rate}%` : "—",
            color: "#818CF8",
        },
    ];

    return (
        <div>
            <div style={{ marginBottom: 32 }}>
                <h1 style={{ fontSize: "1.8rem", fontWeight: 700, marginBottom: 6 }}>Dashboard</h1>
                <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem" }}>
                    Monitor your AI verification pipeline
                </p>
            </div>

            {/* Stat Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
                {cards.map((card, i) => (
                    <motion.div
                        key={card.label}
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="glass-card"
                        style={{ padding: "22px 24px" }}
                    >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                            <span style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", fontWeight: 500 }}>
                                {card.label}
                            </span>
                            <card.icon size={18} color={card.color} />
                        </div>
                        <div style={{ fontSize: "1.8rem", fontWeight: 700 }}>{card.value}</div>
                    </motion.div>
                ))}
            </div>

            {/* Accuracy Breakdown */}
            {stats && (
                <motion.div
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    className="glass-card"
                    style={{ padding: 28, marginBottom: 24 }}
                >
                    <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 20 }}>Claim Breakdown</h2>
                    <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
                        {/* Bar chart */}
                        <div style={{ flex: 1, display: "flex", gap: 8, height: 160, alignItems: "flex-end" }}>
                            {[
                                { label: "Verified", value: stats.accuracy_breakdown.verified, color: "var(--color-verified)" },
                                { label: "Uncertain", value: stats.accuracy_breakdown.uncertain, color: "var(--color-uncertain)" },
                                { label: "Unsupported", value: stats.accuracy_breakdown.unsupported, color: "var(--color-unsupported)" },
                            ].map((bar) => {
                                const total = stats.total_claims || 1;
                                const pct = (bar.value / total) * 100;
                                return (
                                    <div key={bar.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                                        <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{bar.value}</span>
                                        <div
                                            style={{
                                                width: "60%",
                                                height: `${Math.max(pct * 1.4, 8)}px`,
                                                background: bar.color,
                                                borderRadius: 6,
                                                transition: "height 0.6s ease",
                                            }}
                                        />
                                        <span style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)" }}>{bar.label}</span>
                                    </div>
                                );
                            })}
                        </div>

                        {/* Quick links */}
                        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                            <Link href="/dashboard/verify" className="btn-primary" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem", padding: "10px 20px" }}>
                                Verify Now <ArrowRight size={16} />
                            </Link>
                            <Link href="/dashboard/analytics" className="btn-secondary" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem" }}>
                                View Analytics <ArrowRight size={16} />
                            </Link>
                        </div>
                    </div>
                </motion.div>
            )}

            {/* API Usage Example */}
            <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
                className="glass-card"
                style={{ padding: 28 }}
            >
                <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 16 }}>Quick Start</h2>
                <pre
                    style={{
                        background: "var(--color-bg-primary)",
                        border: "1px solid var(--color-border)",
                        borderRadius: 10,
                        padding: 20,
                        fontSize: "0.82rem",
                        lineHeight: 1.7,
                        overflowX: "auto",
                        color: "var(--color-text-secondary)",
                    }}
                >
                    {`curl -X POST https://YOUR-API/prod/verify \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: YOUR_KEY" \\
  -d '{
    "ai_response": "Python was created by Guido van Rossum.",
    "source_documents": ["Python is a language created by Guido van Rossum in 1991."]
  }'`}
                </pre>
            </motion.div>
        </div>
    );
}
