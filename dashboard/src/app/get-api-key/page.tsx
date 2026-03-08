"use client";

import Link from "next/link";
import { Shield, Copy, Check, ArrowLeft, Key, AlertTriangle } from "lucide-react";
import { useState, FormEvent } from "react";
import { generateApiKey } from "@/lib/api";

/* ────────────────────────────────────────────────────────── */
/*  Types                                                     */
/* ────────────────────────────────────────────────────────── */
interface GeneratedKey {
    apiKey: string;
    owner: string;
    permissions: string[];
    rateLimit: number;
}

type FormState = "idle" | "loading" | "success" | "error";

const USE_CASES = [
    "Customer Support Chatbot",
    "Document QA System",
    "Legal Contract Analysis",
    "Content Verification",
    "Research Assistant",
    "Internal Tool",
    "Other",
];

/* ────────────────────────────────────────────────────────── */
/*  Page                                                      */
/* ────────────────────────────────────────────────────────── */
export default function GetApiKeyPage() {
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [useCase, setUseCase] = useState("");
    const [state, setState] = useState<FormState>("idle");
    const [generatedKey, setGeneratedKey] = useState<GeneratedKey | null>(null);
    const [errorMsg, setErrorMsg] = useState("");
    const [copied, setCopied] = useState(false);

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        setState("loading");
        setErrorMsg("");

        try {
            const result = await generateApiKey(name, email, useCase);
            setGeneratedKey({
                apiKey: result.api_key,
                owner: result.owner,
                permissions: result.permissions,
                rateLimit: result.rate_limit,
            });
            setState("success");
        } catch (err: any) {
            setErrorMsg(err.message || "Failed to generate API key");
            setState("error");
        }
    }

    async function handleCopy() {
        if (!generatedKey) return;
        try {
            await navigator.clipboard.writeText(generatedKey.apiKey);
            setCopied(true);
            setTimeout(() => setCopied(false), 3000);
        } catch {
            // Fallback for HTTP contexts
            const textArea = document.createElement("textarea");
            textArea.value = generatedKey.apiKey;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand("copy");
            document.body.removeChild(textArea);
            setCopied(true);
            setTimeout(() => setCopied(false), 3000);
        }
    }

    function handleDownloadEnv() {
        if (!generatedKey) return;
        const envContent = [
            `# TruthLayer API Key — Generated ${new Date().toISOString()}`,
            `# Owner: ${generatedKey.owner}`,
            `TRUTHLAYER_API_KEY=${generatedKey.apiKey}`,
            `TRUTHLAYER_API_URL=https://qoa10ns4c5.execute-api.us-east-1.amazonaws.com/prod`,
        ].join("\n");
        const blob = new Blob([envContent], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = ".env.truthlayer";
        a.click();
        URL.revokeObjectURL(url);
    }

    return (
        <div style={{ minHeight: "100vh", background: "#0A0A0F" }}>
            {/* Nav */}
            <nav
                style={{
                    position: "fixed",
                    top: 0,
                    width: "100%",
                    zIndex: 50,
                    background: "rgba(10, 10, 15, 0.8)",
                    backdropFilter: "blur(16px)",
                    borderBottom: "1px solid rgba(255,255,255,0.06)",
                }}
            >
                <div
                    style={{
                        maxWidth: 1200,
                        margin: "0 auto",
                        padding: "16px 24px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                    }}
                >
                    <Link
                        href="/"
                        style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}
                    >
                        <Shield size={28} color="#6366F1" />
                        <span style={{ fontSize: "1.2rem", fontWeight: 700, color: "#F1F1F3" }}>
                            TruthLayer
                        </span>
                    </Link>
                    <Link
                        href="/"
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            color: "#9CA3AF",
                            textDecoration: "none",
                            fontSize: "0.875rem",
                        }}
                    >
                        <ArrowLeft size={16} />
                        Back to Home
                    </Link>
                </div>
            </nav>

            {/* Main Content */}
            <main
                style={{
                    maxWidth: 560,
                    margin: "0 auto",
                    padding: "120px 24px 64px",
                }}
            >
                {/* Header */}
                <div style={{ textAlign: "center", marginBottom: 40 }}>
                    <div
                        style={{
                            width: 64,
                            height: 64,
                            borderRadius: 16,
                            background: "linear-gradient(135deg, #6366F1, #8B5CF6)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            margin: "0 auto 20px",
                        }}
                    >
                        <Key size={32} color="#fff" />
                    </div>
                    <h1
                        style={{
                            fontSize: "1.75rem",
                            fontWeight: 800,
                            color: "#F1F1F3",
                            margin: "0 0 8px",
                        }}
                    >
                        Get Your API Key
                    </h1>
                    <p
                        style={{
                            color: "#9CA3AF",
                            fontSize: "0.95rem",
                            margin: 0,
                            lineHeight: 1.5,
                        }}
                    >
                        Generate a free API key to start verifying AI outputs.
                        <br />
                        1,000 requests/month included.
                    </p>
                </div>

                {/* Form or Result */}
                {state !== "success" ? (
                    <form onSubmit={handleSubmit}>
                        {/* Card */}
                        <div
                            style={{
                                background: "rgba(255,255,255,0.03)",
                                border: "1px solid rgba(255,255,255,0.08)",
                                borderRadius: 16,
                                padding: 32,
                            }}
                        >
                            {/* Name */}
                            <div style={{ marginBottom: 20 }}>
                                <label
                                    htmlFor="name"
                                    style={{
                                        display: "block",
                                        color: "#D1D5DB",
                                        fontSize: "0.875rem",
                                        fontWeight: 500,
                                        marginBottom: 6,
                                    }}
                                >
                                    Full Name *
                                </label>
                                <input
                                    id="name"
                                    type="text"
                                    required
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="Prakhar Shukla"
                                    style={{
                                        width: "100%",
                                        padding: "10px 14px",
                                        background: "rgba(255,255,255,0.05)",
                                        border: "1px solid rgba(255,255,255,0.1)",
                                        borderRadius: 8,
                                        color: "#F1F1F3",
                                        fontSize: "0.9rem",
                                        outline: "none",
                                        boxSizing: "border-box",
                                    }}
                                />
                            </div>

                            {/* Email */}
                            <div style={{ marginBottom: 20 }}>
                                <label
                                    htmlFor="email"
                                    style={{
                                        display: "block",
                                        color: "#D1D5DB",
                                        fontSize: "0.875rem",
                                        fontWeight: 500,
                                        marginBottom: 6,
                                    }}
                                >
                                    Email Address *
                                </label>
                                <input
                                    id="email"
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="you@company.com"
                                    style={{
                                        width: "100%",
                                        padding: "10px 14px",
                                        background: "rgba(255,255,255,0.05)",
                                        border: "1px solid rgba(255,255,255,0.1)",
                                        borderRadius: 8,
                                        color: "#F1F1F3",
                                        fontSize: "0.9rem",
                                        outline: "none",
                                        boxSizing: "border-box",
                                    }}
                                />
                            </div>

                            {/* Use Case */}
                            <div style={{ marginBottom: 28 }}>
                                <label
                                    htmlFor="useCase"
                                    style={{
                                        display: "block",
                                        color: "#D1D5DB",
                                        fontSize: "0.875rem",
                                        fontWeight: 500,
                                        marginBottom: 6,
                                    }}
                                >
                                    Use Case
                                </label>
                                <select
                                    id="useCase"
                                    value={useCase}
                                    onChange={(e) => setUseCase(e.target.value)}
                                    style={{
                                        width: "100%",
                                        padding: "10px 14px",
                                        background: "rgba(255,255,255,0.05)",
                                        border: "1px solid rgba(255,255,255,0.1)",
                                        borderRadius: 8,
                                        color: useCase ? "#F1F1F3" : "#6B7280",
                                        fontSize: "0.9rem",
                                        outline: "none",
                                        boxSizing: "border-box",
                                        appearance: "none",
                                    }}
                                >
                                    <option value="" style={{ background: "#1a1a2e" }}>
                                        Select a use case (optional)
                                    </option>
                                    {USE_CASES.map((uc) => (
                                        <option key={uc} value={uc} style={{ background: "#1a1a2e", color: "#F1F1F3" }}>
                                            {uc}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Error */}
                            {state === "error" && (
                                <div
                                    style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 8,
                                        padding: "10px 14px",
                                        background: "rgba(239, 68, 68, 0.1)",
                                        border: "1px solid rgba(239, 68, 68, 0.3)",
                                        borderRadius: 8,
                                        marginBottom: 20,
                                        color: "#FCA5A5",
                                        fontSize: "0.85rem",
                                    }}
                                >
                                    <AlertTriangle size={16} />
                                    {errorMsg}
                                </div>
                            )}

                            {/* Submit */}
                            <button
                                type="submit"
                                disabled={state === "loading"}
                                style={{
                                    width: "100%",
                                    padding: "12px 20px",
                                    background: state === "loading"
                                        ? "rgba(99, 102, 241, 0.5)"
                                        : "linear-gradient(135deg, #6366F1, #8B5CF6)",
                                    color: "#fff",
                                    border: "none",
                                    borderRadius: 10,
                                    fontSize: "0.95rem",
                                    fontWeight: 600,
                                    cursor: state === "loading" ? "not-allowed" : "pointer",
                                    transition: "all 0.2s",
                                }}
                            >
                                {state === "loading" ? "Generating..." : "Generate API Key"}
                            </button>
                        </div>
                    </form>
                ) : (
                    /* ── Success: Show the key ── */
                    <div
                        style={{
                            background: "rgba(255,255,255,0.03)",
                            border: "1px solid rgba(99, 102, 241, 0.3)",
                            borderRadius: 16,
                            padding: 32,
                        }}
                    >
                        {/* Success badge */}
                        <div
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                                padding: "8px 14px",
                                background: "rgba(34, 197, 94, 0.1)",
                                border: "1px solid rgba(34, 197, 94, 0.3)",
                                borderRadius: 8,
                                marginBottom: 24,
                                color: "#86EFAC",
                                fontSize: "0.85rem",
                                fontWeight: 500,
                            }}
                        >
                            <Check size={16} />
                            API key generated successfully
                        </div>

                        {/* Key display */}
                        <label
                            style={{
                                display: "block",
                                color: "#D1D5DB",
                                fontSize: "0.8rem",
                                fontWeight: 500,
                                marginBottom: 6,
                                textTransform: "uppercase",
                                letterSpacing: "0.05em",
                            }}
                        >
                            Your API Key
                        </label>
                        <div
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                                padding: "12px 14px",
                                background: "rgba(0,0,0,0.3)",
                                border: "1px solid rgba(255,255,255,0.1)",
                                borderRadius: 8,
                                marginBottom: 16,
                            }}
                        >
                            <code
                                style={{
                                    flex: 1,
                                    color: "#A5B4FC",
                                    fontSize: "0.85rem",
                                    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                                    wordBreak: "break-all",
                                    lineHeight: 1.4,
                                }}
                            >
                                {generatedKey?.apiKey}
                            </code>
                            <button
                                onClick={handleCopy}
                                title="Copy to clipboard"
                                style={{
                                    background: "rgba(255,255,255,0.06)",
                                    border: "1px solid rgba(255,255,255,0.1)",
                                    borderRadius: 6,
                                    padding: "6px 10px",
                                    cursor: "pointer",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 4,
                                    color: copied ? "#86EFAC" : "#9CA3AF",
                                    fontSize: "0.75rem",
                                    flexShrink: 0,
                                    transition: "all 0.2s",
                                }}
                            >
                                {copied ? <Check size={14} /> : <Copy size={14} />}
                                {copied ? "Copied!" : "Copy"}
                            </button>
                        </div>

                        {/* Warning */}
                        <div
                            style={{
                                display: "flex",
                                alignItems: "flex-start",
                                gap: 8,
                                padding: "10px 14px",
                                background: "rgba(234, 179, 8, 0.08)",
                                border: "1px solid rgba(234, 179, 8, 0.2)",
                                borderRadius: 8,
                                marginBottom: 24,
                                color: "#FDE68A",
                                fontSize: "0.8rem",
                                lineHeight: 1.4,
                            }}
                        >
                            <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
                            <span>
                                Save this key now. For security, it cannot be retrieved again.
                                Only the SHA-256 hash is stored on our servers.
                            </span>
                        </div>

                        {/* Details */}
                        <div
                            style={{
                                display: "grid",
                                gridTemplateColumns: "1fr 1fr",
                                gap: 12,
                                marginBottom: 24,
                            }}
                        >
                            <div
                                style={{
                                    padding: "12px 14px",
                                    background: "rgba(255,255,255,0.03)",
                                    borderRadius: 8,
                                    border: "1px solid rgba(255,255,255,0.06)",
                                }}
                            >
                                <div style={{ color: "#6B7280", fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
                                    Rate Limit
                                </div>
                                <div style={{ color: "#F1F1F3", fontSize: "0.95rem", fontWeight: 600 }}>
                                    {generatedKey?.rateLimit?.toLocaleString()}/mo
                                </div>
                            </div>
                            <div
                                style={{
                                    padding: "12px 14px",
                                    background: "rgba(255,255,255,0.03)",
                                    borderRadius: 8,
                                    border: "1px solid rgba(255,255,255,0.06)",
                                }}
                            >
                                <div style={{ color: "#6B7280", fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
                                    Permissions
                                </div>
                                <div style={{ color: "#F1F1F3", fontSize: "0.95rem", fontWeight: 600 }}>
                                    {generatedKey?.permissions?.length} scopes
                                </div>
                            </div>
                        </div>

                        {/* Actions */}
                        <div style={{ display: "flex", gap: 10 }}>
                            <button
                                onClick={handleDownloadEnv}
                                style={{
                                    flex: 1,
                                    padding: "10px 16px",
                                    background: "rgba(255,255,255,0.05)",
                                    border: "1px solid rgba(255,255,255,0.1)",
                                    borderRadius: 8,
                                    color: "#D1D5DB",
                                    fontSize: "0.85rem",
                                    cursor: "pointer",
                                    fontWeight: 500,
                                }}
                            >
                                Download .env
                            </button>
                            <Link
                                href="/dashboard"
                                style={{
                                    flex: 1,
                                    padding: "10px 16px",
                                    background: "linear-gradient(135deg, #6366F1, #8B5CF6)",
                                    border: "none",
                                    borderRadius: 8,
                                    color: "#fff",
                                    fontSize: "0.85rem",
                                    textAlign: "center",
                                    textDecoration: "none",
                                    fontWeight: 500,
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                }}
                            >
                                Go to Dashboard
                            </Link>
                        </div>
                    </div>
                )}

                {/* Quick Start Code */}
                <div
                    style={{
                        marginTop: 32,
                        background: "rgba(255,255,255,0.02)",
                        border: "1px solid rgba(255,255,255,0.06)",
                        borderRadius: 12,
                        padding: 24,
                    }}
                >
                    <h3
                        style={{
                            color: "#D1D5DB",
                            fontSize: "0.85rem",
                            fontWeight: 600,
                            margin: "0 0 12px",
                        }}
                    >
                        Quick Start
                    </h3>
                    <pre
                        style={{
                            background: "rgba(0,0,0,0.3)",
                            borderRadius: 8,
                            padding: 16,
                            overflow: "auto",
                            margin: 0,
                            fontSize: "0.8rem",
                            lineHeight: 1.5,
                            color: "#A5B4FC",
                            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                        }}
                    >
                        {`from truthlayer import TruthLayer

tl = TruthLayer(
    api_key="YOUR_KEY",
    api_url="https://qoa10ns4c5.execute-api..."
)

result = tl.verify(
    ai_response="...",
    source_documents=["..."]
)
print(result.trust_score)  # 94.2`}
                    </pre>
                </div>
            </main>
        </div>
    );
}
