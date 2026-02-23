"use client";

import { motion } from "framer-motion";
import {
    Search,
    CheckCircle2,
    AlertTriangle,
    XCircle,
    Clock,
    Binary,
    Layers,
} from "lucide-react";
import { useState } from "react";
import { verifyResponse, type Claim, type VerifyResponse } from "@/lib/api";

export default function VerifyPage() {
    const [aiText, setAiText] = useState("");
    const [sourceText, setSourceText] = useState("");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<VerifyResponse | null>(null);
    const [error, setError] = useState("");
    const [demoMode, setDemoMode] = useState(false);

    const handleVerify = async () => {
        if (!aiText.trim() || !sourceText.trim()) return;
        setLoading(true);
        setError("");
        setResult(null);
        setDemoMode(false);

        try {
            const res = await verifyResponse(aiText, [sourceText]);
            setResult(res);
        } catch (err: any) {
            // Fallback to demo data
            setDemoMode(true);
            setResult({
                claims: [
                    { text: "The Eiffel Tower is in Paris.", status: "VERIFIED", confidence: 96.1, similarity_score: 0.961, matched_source: "The Eiffel Tower is located in Paris, France." },
                    { text: "It was built in 1889.", status: "VERIFIED", confidence: 88.7, similarity_score: 0.887, matched_source: "Construction finished in 1889." },
                    { text: "It stands 1,083 feet tall.", status: "UNCERTAIN", confidence: 62.3, similarity_score: 0.623, matched_source: "The tower is approximately 330 meters tall." },
                ],
                summary: { verified: 2, uncertain: 1, unsupported: 0 },
                metadata: { latency_ms: 47.3, embedding_ms: 32.1, provider: "BedrockEmbeddingProvider", total_claims: 3, source_chunks: 4 },
            });
        }

        setLoading(false);
    };

    const loadExample = () => {
        setAiText(
            "Python 3.11 was released in October 2022. It includes performance improvements, being up to 25% faster than Python 3.10. The new version introduces exception groups and the except* syntax for handling multiple exceptions simultaneously."
        );
        setSourceText(
            "Python 3.11 was officially released on October 24, 2022. This release focuses on performance improvements and better error reporting. According to official benchmarks, Python 3.11 is up to 10-60% faster than Python 3.10, with an average speedup of 25%. New features include exception groups (PEP 654) which allow programs to raise and handle multiple exceptions at once using the new except* syntax."
        );
    };

    const statusIcon = (status: string) => {
        if (status === "VERIFIED") return <CheckCircle2 size={16} color="var(--color-verified)" />;
        if (status === "UNCERTAIN") return <AlertTriangle size={16} color="var(--color-uncertain)" />;
        return <XCircle size={16} color="var(--color-unsupported)" />;
    };

    const statusColor = (status: string) => {
        if (status === "VERIFIED") return "var(--color-verified)";
        if (status === "UNCERTAIN") return "var(--color-uncertain)";
        return "var(--color-unsupported)";
    };

    return (
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
                <div>
                    <h1 style={{ fontSize: "1.6rem", fontWeight: 700, marginBottom: 4 }}>Verify</h1>
                    <p style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                        Check AI responses against source documents
                    </p>
                </div>
                <button onClick={loadExample} className="btn-secondary" style={{ fontSize: "0.8rem" }}>
                    Load Example
                </button>
            </div>

            {/* Input Section */}
            <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
                    <div>
                        <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 8 }}>
                            🤖 AI Response
                        </label>
                        <textarea
                            className="input-field"
                            rows={8}
                            value={aiText}
                            onChange={(e) => setAiText(e.target.value)}
                            placeholder="Paste the AI-generated text you want to verify..."
                        />
                    </div>
                    <div>
                        <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 8 }}>
                            📚 Source Documents
                        </label>
                        <textarea
                            className="input-field"
                            rows={8}
                            value={sourceText}
                            onChange={(e) => setSourceText(e.target.value)}
                            placeholder="Paste the source document(s) to verify against..."
                        />
                    </div>
                </div>

                <button
                    className="btn-primary"
                    onClick={handleVerify}
                    disabled={loading || !aiText.trim() || !sourceText.trim()}
                    style={{ width: "100%", padding: "14px", fontSize: "1rem" }}
                >
                    {loading ? (
                        <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                            <span className="skeleton" style={{ width: 18, height: 18, borderRadius: "50%" }} />
                            Verifying...
                        </span>
                    ) : (
                        <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                            <Search size={18} />
                            Verify Claims
                        </span>
                    )}
                </button>
            </div>

            {/* Error */}
            {error && (
                <div
                    style={{
                        background: "rgba(239, 68, 68, 0.1)",
                        border: "1px solid rgba(239, 68, 68, 0.3)",
                        borderRadius: 12,
                        padding: "12px 18px",
                        marginBottom: 20,
                        color: "var(--color-unsupported)",
                        fontSize: "0.85rem",
                    }}
                >
                    ❌ {error}
                </div>
            )}

            {/* Results */}
            {result && (
                <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}>
                    {demoMode && (
                        <div
                            style={{
                                background: "rgba(234, 179, 8, 0.1)",
                                border: "1px solid rgba(234, 179, 8, 0.3)",
                                borderRadius: 12,
                                padding: "10px 16px",
                                marginBottom: 16,
                                fontSize: "0.8rem",
                                color: "var(--color-uncertain)",
                            }}
                        >
                            ⚠️ Demo mode — set NEXT_PUBLIC_API_URL in .env.local for live results
                        </div>
                    )}

                    {/* Summary Cards */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 20 }}>
                        {[
                            { label: "Verified", value: result.summary.verified, color: "var(--color-verified)", icon: CheckCircle2 },
                            { label: "Uncertain", value: result.summary.uncertain, color: "var(--color-uncertain)", icon: AlertTriangle },
                            { label: "Unsupported", value: result.summary.unsupported, color: "var(--color-unsupported)", icon: XCircle },
                        ].map((s) => (
                            <div key={s.label} className="glass-card" style={{ padding: "16px 20px", textAlign: "center" }}>
                                <s.icon size={20} color={s.color} style={{ marginBottom: 6 }} />
                                <div style={{ fontSize: "1.5rem", fontWeight: 700, color: s.color }}>{s.value}</div>
                                <div style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)" }}>{s.label}</div>
                            </div>
                        ))}
                    </div>

                    {/* Metadata */}
                    <div className="glass-card" style={{ padding: "14px 20px", marginBottom: 20, display: "flex", gap: 28, flexWrap: "wrap" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
                            <Clock size={14} /> {result.metadata.latency_ms}ms total
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
                            <Binary size={14} /> {result.metadata.embedding_ms}ms embedding
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
                            <Layers size={14} /> {result.metadata.source_chunks} chunks
                        </div>
                        <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
                            Provider: <span style={{ color: "#818CF8" }}>{result.metadata.provider}</span>
                        </div>
                    </div>

                    {/* Claims */}
                    <div className="glass-card" style={{ padding: 24 }}>
                        <h2 style={{ fontSize: "1.05rem", fontWeight: 600, marginBottom: 18 }}>
                            Claim Analysis ({result.claims.length} claims)
                        </h2>

                        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                            {result.claims.map((claim, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: i * 0.1 }}
                                    style={{
                                        padding: "16px 18px",
                                        borderRadius: 12,
                                        background: "var(--color-bg-primary)",
                                        border: "1px solid var(--color-border)",
                                    }}
                                >
                                    <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
                                        {statusIcon(claim.status)}
                                        <span style={{ flex: 1, fontSize: "0.9rem", lineHeight: 1.5 }}>{claim.text}</span>
                                        <span
                                            className={`status-${claim.status.toLowerCase()}`}
                                            style={{ padding: "3px 10px", borderRadius: 6, fontSize: "0.7rem", fontWeight: 600, whiteSpace: "nowrap" }}
                                        >
                                            {claim.status}
                                        </span>
                                    </div>

                                    {/* Confidence bar */}
                                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                                        <span style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)", width: 70 }}>
                                            Confidence
                                        </span>
                                        <div className="confidence-bar" style={{ flex: 1 }}>
                                            <div
                                                className="confidence-bar-fill"
                                                style={{ width: `${claim.confidence}%`, background: statusColor(claim.status) }}
                                            />
                                        </div>
                                        <span style={{ fontSize: "0.8rem", fontWeight: 600, color: statusColor(claim.status), width: 45, textAlign: "right" }}>
                                            {claim.confidence}%
                                        </span>
                                    </div>

                                    {/* Matched source */}
                                    {claim.matched_source && (
                                        <div style={{ fontSize: "0.78rem", color: "var(--color-text-secondary)", lineHeight: 1.5, paddingLeft: 26 }}>
                                            📎 <em>{claim.matched_source}</em>
                                        </div>
                                    )}
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </motion.div>
            )}
        </div>
    );
}
