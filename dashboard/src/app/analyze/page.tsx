"use client";

import Link from "next/link";
import { useState } from "react";
import React from "react";
import {
  Shield,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Zap,
} from "lucide-react";
import { verifyResponse, type Claim, type ContradictionEvidence } from "@/lib/api";

/* =========================================================================== */
/*  TYPES                                                                       */
/* =========================================================================== */

interface VerificationResult {
  claims: Claim[];
  summary: { verified: number; uncertain: number; unsupported: number };
  metadata: { latency_ms: number; provider: string; total_claims: number };
}

/* =========================================================================== */
/*  CONSTANTS                                                                   */
/* =========================================================================== */

const EXAMPLE_AI =
  "The GDPR fine is 2% of annual global revenue. Aspirin is safe for children with fever. The plan offers unlimited storage capacity.";

const EXAMPLE_SOURCE =
  "GDPR fines can reach up to 4% of annual global turnover. Aspirin should NOT be given to children under 12 — risk of Reye syndrome. The plan includes a 100GB storage cap per account.";

const SIGNAL_LABELS: Record<string, string> = {
  NUMERICAL_MISMATCH:      "Numerical Mismatch",
  S2A_NEGATION_POLARITY:   "Negation Polarity",
  SEMANTIC_ANTONYM:        "Semantic Antonym",
  SUPERLATIVE_SWAP:        "Superlative Swap",
  SUPERLATIVE_VS_SPECIFIC: "Absolute vs. Specific",
};

const SIGNAL_ICONS: Record<string, string> = {
  NUMERICAL_MISMATCH:      "🔢",
  S2A_NEGATION_POLARITY:   "⚡",
  SEMANTIC_ANTONYM:        "🔄",
  SUPERLATIVE_SWAP:        "↕️",
  SUPERLATIVE_VS_SPECIFIC: "∞",
};

/* Severity to solid badge colours (text is always white for CRITICAL/HIGH/MEDIUM) */
const SEVERITY_BG: Record<string, string> = {
  CRITICAL: "#DC2626",
  HIGH:     "#EA580C",
  MEDIUM:   "#D97706",
  LOW:      "#4B5563",
};

/* Severity to translucent tint used for the card background */
const SEVERITY_TINT: Record<string, string> = {
  CRITICAL: "rgba(220,38,38,0.08)",
  HIGH:     "rgba(234,88,12,0.08)",
  MEDIUM:   "rgba(217,119,6,0.08)",
  LOW:      "rgba(99,102,241,0.08)",
};

const SEVERITY_BORDER: Record<string, string> = {
  CRITICAL: "rgba(220,38,38,0.25)",
  HIGH:     "rgba(234,88,12,0.25)",
  MEDIUM:   "rgba(217,119,6,0.25)",
  LOW:      "rgba(99,102,241,0.25)",
};

/* =========================================================================== */
/*  GLOBAL CSS KEYFRAMES (injected once)                                        */
/* =========================================================================== */

const KEYFRAMES = `
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
@keyframes cardSlideUp {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0);    }
}
`;

/* =========================================================================== */
/*  HELPERS                                                                     */
/* =========================================================================== */

function statusColor(status: string): string {
  if (status === "VERIFIED")  return "var(--color-verified)";
  if (status === "UNCERTAIN") return "var(--color-uncertain)";
  return "var(--color-unsupported)";
}

function statusBg(status: string): string {
  if (status === "VERIFIED")  return "rgba(34,197,94,0.08)";
  if (status === "UNCERTAIN") return "rgba(234,179,8,0.08)";
  return "rgba(239,68,68,0.08)";
}

function statusBorder(status: string): string {
  if (status === "VERIFIED")  return "rgba(34,197,94,0.2)";
  if (status === "UNCERTAIN") return "rgba(234,179,8,0.2)";
  return "rgba(239,68,68,0.2)";
}

function StatusIcon({ status }: { status: string }) {
  if (status === "VERIFIED")  return <CheckCircle2 size={18} color="var(--color-verified)" />;
  if (status === "UNCERTAIN") return <AlertTriangle size={18} color="var(--color-uncertain)" />;
  return <XCircle size={18} color="var(--color-unsupported)" />;
}

/**
 * FEATURE 3 — Source fragment highlighting.
 * Finds `fragment` inside `full` (case-insensitive) and wraps it in a <mark>.
 * Falls back to plain text if fragment is empty or not found.
 */
function highlightFragment(full: string, fragment: string): React.ReactNode {
  if (!fragment || !full) return full;
  const idx = full.toLowerCase().indexOf(fragment.toLowerCase());
  if (idx === -1) return full;
  return (
    <>
      {full.slice(0, idx)}
      <mark
        style={{
          background: "#FEF08A",
          borderRadius: 3,
          padding: "0 2px",
          color: "#1a1a1a",
          fontStyle: "normal",
        }}
      >
        {full.slice(idx, idx + fragment.length)}
      </mark>
      {full.slice(idx + fragment.length)}
    </>
  );
}

/* =========================================================================== */
/*  FEATURE 2 — Evidence Card                                                   */
/* =========================================================================== */

function EvidenceCard({
  evidence,
  index,
}: {
  evidence: ContradictionEvidence;
  index: number;
}) {
  const icon       = SIGNAL_ICONS[evidence.signal]  ?? "⚠";
  const label      = SIGNAL_LABELS[evidence.signal] ?? evidence.signal;
  const badgeBg    = SEVERITY_BG[evidence.severity]     ?? "#4B5563";
  const cardBg     = SEVERITY_TINT[evidence.severity]   ?? "rgba(99,102,241,0.08)";
  const cardBorder = SEVERITY_BORDER[evidence.severity] ?? "rgba(99,102,241,0.25)";

  return (
    <div
      id={`evidence-placeholder-${index}`}
      style={{
        marginTop: 14,
        borderRadius: 12,
        background: cardBg,
        border: `1px solid ${cardBorder}`,
        overflow: "hidden",
      }}
    >
      {/* ── Header row ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 14px",
          borderBottom: `1px solid ${cardBorder}`,
        }}
      >
        <span style={{ fontSize: "1rem" }}>{icon}</span>
        <span
          style={{
            fontSize: "0.72rem",
            fontWeight: 700,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            color: "var(--color-text-secondary)",
            flex: 1,
          }}
        >
          {label}
        </span>
        {/* Severity badge — solid fill */}
        <span
          style={{
            fontSize: "0.65rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            padding: "3px 10px",
            borderRadius: 20,
            background: badgeBg,
            color: "#FFFFFF",
          }}
        >
          {evidence.severity}
        </span>
      </div>

      {/* ── Fragment comparison row ── */}
      {(evidence.claim_fragment || evidence.source_fragment) && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 10,
            padding: "12px 14px",
            borderBottom: evidence.explanation ? `1px solid ${cardBorder}` : "none",
          }}
        >
          {evidence.claim_fragment && (
            <div>
              <div
                style={{
                  fontSize: "0.62rem",
                  fontWeight: 700,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: "#EF4444",
                  marginBottom: 5,
                }}
              >
                Claim says:
              </div>
              <div
                style={{
                  padding: "7px 10px",
                  borderRadius: 8,
                  background: "rgba(239,68,68,0.1)",
                  border: "1px solid rgba(239,68,68,0.2)",
                  fontSize: "0.82rem",
                  fontFamily: "monospace",
                  color: "#FCA5A5",
                  wordBreak: "break-word",
                }}
              >
                &quot;{evidence.claim_fragment}&quot;
              </div>
            </div>
          )}
          {evidence.source_fragment && (
            <div>
              <div
                style={{
                  fontSize: "0.62rem",
                  fontWeight: 700,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: "#22C55E",
                  marginBottom: 5,
                }}
              >
                Source says:
              </div>
              <div
                style={{
                  padding: "7px 10px",
                  borderRadius: 8,
                  background: "rgba(34,197,94,0.1)",
                  border: "1px solid rgba(34,197,94,0.2)",
                  fontSize: "0.82rem",
                  fontFamily: "monospace",
                  color: "#86EFAC",
                  wordBreak: "break-word",
                }}
              >
                &quot;{evidence.source_fragment}&quot;
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Explanation + penalty ── */}
      {(evidence.explanation || evidence.penalty_applied) && (
        <div style={{ padding: "10px 14px", display: "flex", flexDirection: "column", gap: 4 }}>
          {evidence.explanation && (
            <p
              style={{
                margin: 0,
                fontSize: "0.8rem",
                color: "var(--color-text-secondary)",
                lineHeight: 1.55,
              }}
            >
              <strong style={{ color: "var(--color-text-primary, #F1F1F3)", fontWeight: 600 }}>
                Explanation:
              </strong>{" "}
              {evidence.explanation}
            </p>
          )}
          {evidence.penalty_applied !== undefined && (
            <p
              style={{
                margin: 0,
                fontSize: "0.75rem",
                color: "var(--color-text-secondary)",
              }}
            >
              Penalty applied:{" "}
              <code
                style={{
                  padding: "1px 6px",
                  borderRadius: 4,
                  background: "rgba(255,255,255,0.06)",
                  fontSize: "0.78rem",
                  fontFamily: "monospace",
                }}
              >
                &times;{evidence.penalty_applied.toFixed(2)}
              </code>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* =========================================================================== */
/*  FEATURE 1 — Claim Card with staggered entry animation                       */
/* =========================================================================== */

function ClaimCard({ claim, index }: { claim: Claim; index: number }) {
  const color  = statusColor(claim.status);
  const bg     = statusBg(claim.status);
  const border = statusBorder(claim.status);

  const label =
    claim.status === "VERIFIED"  ? "✓  VERIFIED"  :
    claim.status === "UNCERTAIN" ? "⚠  UNCERTAIN" :
    "✗  FLAGGED";

  /* Fragment to highlight inside matched_source */
  const sourceFragment = claim.contradiction_evidence?.source_fragment ?? "";

  return (
    <div
      style={{
        padding: "20px 22px",
        borderRadius: 14,
        background: bg,
        border: `1px solid ${border}`,
        marginBottom: 14,
        /* FEATURE 1 — staggered slide-up animation */
        animation: `cardSlideUp 400ms ease-out both`,
        animationDelay: `${index * 200}ms`,
      }}
    >
      {/* Top row — status badge + score */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 10 }}>
        <StatusIcon status={claim.status} />
        <div style={{ flex: 1 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              flexWrap: "wrap",
              marginBottom: 6,
            }}
          >
            <span
              style={{
                fontSize: "0.7rem",
                fontWeight: 700,
                letterSpacing: "0.06em",
                color,
                padding: "3px 10px",
                borderRadius: 20,
                background: bg,
                border: `1px solid ${border}`,
              }}
            >
              {label}
            </span>
            <span
              style={{
                fontSize: "0.75rem",
                color: "var(--color-text-secondary)",
                marginLeft: "auto",
              }}
            >
              Score: {claim.similarity_score.toFixed(4)}
            </span>
          </div>

          {/* Claim text */}
          <p
            style={{
              fontSize: "0.92rem",
              lineHeight: 1.55,
              margin: 0,
              color: "var(--color-text-primary, #F1F1F3)",
            }}
          >
            {claim.text}
          </p>

          {/* FEATURE 3 — matched_source with fragment highlighting */}
          {claim.matched_source && (
            <p
              style={{
                fontSize: "0.78rem",
                color: "var(--color-text-secondary)",
                fontStyle: "italic",
                marginTop: 8,
                marginBottom: 0,
                lineHeight: 1.55,
              }}
            >
              Matched: &quot;{highlightFragment(claim.matched_source, sourceFragment)}&quot;
            </p>
          )}
        </div>
      </div>

      {/* Confidence bar */}
      <div
        style={{
          height: 4,
          borderRadius: 4,
          background: "var(--color-border)",
          overflow: "hidden",
          marginBottom: 0,
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${claim.confidence}%`,
            background: color,
            borderRadius: 4,
            transition: "width 0.6s ease",
          }}
        />
      </div>

      {/* FEATURE 2 — full evidence card */}
      {claim.contradiction_evidence && (
        <EvidenceCard evidence={claim.contradiction_evidence} index={index} />
      )}
    </div>
  );
}

/* =========================================================================== */
/*  SUMMARY BAR                                                                 */
/* =========================================================================== */

function SummaryBar({ summary }: { summary: VerificationResult["summary"] }) {
  const total = summary.verified + summary.uncertain + summary.unsupported;

  const pills = [
    { label: "Verified",    count: summary.verified,    color: "var(--color-verified)",    bg: "rgba(34,197,94,0.1)",  border: "rgba(34,197,94,0.25)"  },
    { label: "Uncertain",   count: summary.uncertain,   color: "var(--color-uncertain)",   bg: "rgba(234,179,8,0.1)", border: "rgba(234,179,8,0.25)" },
    { label: "Unsupported", count: summary.unsupported, color: "var(--color-unsupported)", bg: "rgba(239,68,68,0.1)",  border: "rgba(239,68,68,0.25)"  },
  ];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "16px 20px",
        borderRadius: 12,
        background: "var(--color-bg-secondary, rgba(255,255,255,0.03))",
        border: "1px solid var(--color-border)",
        marginBottom: 16,
        flexWrap: "wrap",
      }}
    >
      <span
        style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-text-secondary)" }}
      >
        {total} claim{total !== 1 ? "s" : ""} analyzed
      </span>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {pills.map((p) => (
          <span
            key={p.label}
            style={{
              padding: "4px 12px",
              borderRadius: 20,
              fontSize: "0.75rem",
              fontWeight: 600,
              color: p.color,
              background: p.bg,
              border: `1px solid ${p.border}`,
            }}
          >
            {p.count} {p.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/* =========================================================================== */
/*  FEATURE 4 — Risk Level Banner                                               */
/* =========================================================================== */

function RiskBanner({ summary }: { summary: VerificationResult["summary"] }) {
  const { verified: _v, uncertain, unsupported } = summary;

  let risk: string;
  let message: string;
  let bg: string;
  let border: string;
  let color: string;
  let icon: string;

  if (unsupported > 0) {
    risk    = "HIGH RISK";
    message = `${unsupported} hallucination${unsupported > 1 ? "s" : ""} detected — review before publishing`;
    bg      = "rgba(220,38,38,0.08)";
    border  = "rgba(220,38,38,0.3)";
    color   = "#FCA5A5";
    icon    = "🚨";
  } else if (uncertain > 0) {
    risk    = "REVIEW NEEDED";
    message = `${uncertain} uncertain claim${uncertain > 1 ? "s" : ""} — additional sources recommended`;
    bg      = "rgba(217,119,6,0.08)";
    border  = "rgba(217,119,6,0.3)";
    color   = "#FCD34D";
    icon    = "⚠️";
  } else {
    risk    = "ALL CLEAR";
    message = "All claims verified against source document";
    bg      = "rgba(34,197,94,0.08)";
    border  = "rgba(34,197,94,0.3)";
    color   = "#86EFAC";
    icon    = "✅";
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "14px 20px",
        borderRadius: 12,
        background: bg,
        border: `1px solid ${border}`,
        marginBottom: 10,
      }}
    >
      <span style={{ fontSize: "1.2rem" }}>{icon}</span>
      <div>
        <span
          style={{
            fontSize: "0.72rem",
            fontWeight: 800,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color,
            display: "block",
            marginBottom: 2,
          }}
        >
          {risk}
        </span>
        <span style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
          {message}
        </span>
      </div>
    </div>
  );
}

/* =========================================================================== */
/*  MAIN PAGE                                                                   */
/* =========================================================================== */

export default function AnalyzePage() {
  const [aiResponse, setAiResponse] = useState("");
  const [sourceDoc,  setSourceDoc]  = useState("");
  const [isLoading,  setIsLoading]  = useState(false);
  const [result,     setResult]     = useState<VerificationResult | null>(null);
  const [error,      setError]      = useState<string | null>(null);

  const loadExample = () => {
    setAiResponse(EXAMPLE_AI);
    setSourceDoc(EXAMPLE_SOURCE);
    setResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!aiResponse.trim() || !sourceDoc.trim()) return;
    setIsLoading(true);
    setResult(null);
    setError(null);
    try {
      const data = await verifyResponse(aiResponse.trim(), [sourceDoc.trim()]);
      setResult(data as VerificationResult);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Verification failed. Check your API key and connection."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const canAnalyze =
    aiResponse.trim().length > 0 && sourceDoc.trim().length > 0 && !isLoading;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-bg-primary, #0A0A0F)",
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Inject all keyframes once */}
      <style>{KEYFRAMES}</style>

      {/* ── NAV ── */}
      <nav
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          background: "rgba(10,10,15,0.9)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--color-border)",
        }}
      >
        <div
          style={{
            maxWidth: 1100,
            margin: "0 auto",
            padding: "14px 24px",
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <Link
            href="/"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              textDecoration: "none",
              color: "var(--color-text-secondary)",
              fontSize: "0.85rem",
            }}
          >
            <ArrowLeft size={16} />
            Back
          </Link>
          <div style={{ width: 1, height: 18, background: "var(--color-border)" }} />
          <Link
            href="/"
            style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none" }}
          >
            <Shield size={22} color="#6366F1" />
            <span style={{ fontSize: "1rem", fontWeight: 700, color: "#F1F1F3" }}>
              TruthLayer
            </span>
          </Link>
          <span
            style={{
              marginLeft: "auto",
              fontSize: "0.78rem",
              fontWeight: 600,
              padding: "4px 12px",
              borderRadius: 20,
              background: "rgba(99,102,241,0.1)",
              border: "1px solid rgba(99,102,241,0.3)",
              color: "#818CF8",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <Zap size={12} />
            Five-Signal Engine
          </span>
        </div>
      </nav>

      {/* ── MAIN CONTENT ── */}
      <main style={{ maxWidth: 1100, margin: "0 auto", padding: "48px 24px 80px" }}>

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <h1
            style={{
              fontSize: "clamp(1.8rem, 4vw, 2.8rem)",
              fontWeight: 800,
              letterSpacing: "-0.02em",
              marginBottom: 14,
              lineHeight: 1.15,
            }}
          >
            Real-Time Claim{" "}
            <span className="animated-gradient-text">Analyzer</span>
          </h1>
          <p
            style={{
              fontSize: "1rem",
              color: "var(--color-text-secondary)",
              lineHeight: 1.7,
              maxWidth: 580,
              margin: "0 auto",
            }}
          >
            Paste any AI response and source document — watch the five-signal engine verify
            each claim against your source, claim by claim.
          </p>
        </div>

        {/* Two-panel input row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
            gap: 20,
            marginBottom: 16,
          }}
        >
          {/* Left — AI Response */}
          <div>
            <label
              htmlFor="ai-response-input"
              style={{
                display: "block",
                fontSize: "0.8rem",
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                marginBottom: 8,
                letterSpacing: "0.03em",
              }}
            >
              🤖 AI Response
            </label>
            <textarea
              id="ai-response-input"
              className="input-field"
              rows={8}
              value={aiResponse}
              onChange={(e) => setAiResponse(e.target.value)}
              placeholder="Paste the AI-generated text to verify..."
              style={{ width: "100%", resize: "vertical", fontSize: "0.88rem", lineHeight: 1.6 }}
            />
          </div>

          {/* Right — Source Document */}
          <div>
            <label
              htmlFor="source-document-input"
              style={{
                display: "block",
                fontSize: "0.8rem",
                fontWeight: 600,
                color: "var(--color-text-secondary)",
                marginBottom: 8,
                letterSpacing: "0.03em",
              }}
            >
              📚 Source Document
            </label>
            <textarea
              id="source-document-input"
              className="input-field"
              rows={8}
              value={sourceDoc}
              onChange={(e) => setSourceDoc(e.target.value)}
              placeholder="Paste your ground-truth source document..."
              style={{ width: "100%", resize: "vertical", fontSize: "0.88rem", lineHeight: 1.6 }}
            />
          </div>
        </div>

        {/* Prefill button */}
        <div style={{ marginBottom: 20 }}>
          <button
            onClick={loadExample}
            style={{
              background: "none",
              border: "none",
              color: "#818CF8",
              fontSize: "0.82rem",
              cursor: "pointer",
              padding: 0,
              textDecoration: "underline",
              textUnderlineOffset: 3,
            }}
          >
            Load example →
          </button>
        </div>

        {/* Analyze button */}
        <button
          id="analyze-button"
          className="btn-primary"
          onClick={handleAnalyze}
          disabled={!canAnalyze}
          style={{
            width: "100%",
            fontSize: "1rem",
            padding: "16px 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            marginBottom: 40,
            opacity: canAnalyze ? 1 : 0.5,
            cursor: canAnalyze ? "pointer" : "not-allowed",
          }}
        >
          {isLoading ? (
            <>
              <Loader2
                size={18}
                style={{ animation: "spin 1s linear infinite" }}
              />
              Analyzing with Five-Signal Engine...
            </>
          ) : (
            "Analyze with Five-Signal Verification →"
          )}
        </button>

        {/* Error state */}
        {error && (
          <div
            style={{
              padding: "16px 20px",
              borderRadius: 12,
              background: "rgba(239,68,68,0.08)",
              border: "1px solid rgba(239,68,68,0.25)",
              color: "#FCA5A5",
              fontSize: "0.9rem",
              marginBottom: 24,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <XCircle size={18} color="#EF4444" />
            {error}
          </div>
        )}

        {/* Results section */}
        {result && (
          <div>
            {/* FEATURE 4 — Risk banner */}
            <RiskBanner summary={result.summary} />

            {/* Summary pill bar */}
            <SummaryBar summary={result.summary} />

            <div
              style={{
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <h2 style={{ fontSize: "1rem", fontWeight: 700, margin: 0 }}>
                Claim-by-Claim Results
              </h2>
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "var(--color-text-secondary)",
                  marginLeft: "auto",
                }}
              >
                {result.metadata?.latency_ms
                  ? `${Math.round(result.metadata.latency_ms)}ms`
                  : ""}
              </span>
            </div>

            {/* FEATURE 1 — staggered animated cards */}
            {result.claims.map((claim, i) => (
              <ClaimCard key={i} claim={claim} index={i} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
