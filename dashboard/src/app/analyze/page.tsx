"use client";

import Link from "next/link";
import { useState } from "react";
import { Shield, ArrowLeft, Loader2, CheckCircle2, AlertTriangle, XCircle, Zap, AlertCircle } from "lucide-react";
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
  NUMERICAL_MISMATCH:     "Numerical Mismatch",
  S2A_NEGATION_POLARITY:  "Negation Polarity",
  SEMANTIC_ANTONYM:       "Semantic Antonym",
  SUPERLATIVE_SWAP:       "Superlative Swap",
  SUPERLATIVE_VS_SPECIFIC:"Absolute vs. Specific",
};

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "#EF4444",
  HIGH:     "#F97316",
  MEDIUM:   "#EAB308",
  LOW:      "#6366F1",
};

/* =========================================================================== */
/*  HELPERS                                                                     */
/* =========================================================================== */

function statusColor(status: string): string {
  if (status === "VERIFIED")   return "var(--color-verified)";
  if (status === "UNCERTAIN")  return "var(--color-uncertain)";
  return "var(--color-unsupported)";
}

function statusBg(status: string): string {
  if (status === "VERIFIED")   return "rgba(34,197,94,0.08)";
  if (status === "UNCERTAIN")  return "rgba(234,179,8,0.08)";
  return "rgba(239,68,68,0.08)";
}

function statusBorder(status: string): string {
  if (status === "VERIFIED")   return "rgba(34,197,94,0.2)";
  if (status === "UNCERTAIN")  return "rgba(234,179,8,0.2)";
  return "rgba(239,68,68,0.2)";
}

function StatusIcon({ status }: { status: string }) {
  if (status === "VERIFIED")  return <CheckCircle2 size={18} color="var(--color-verified)" />;
  if (status === "UNCERTAIN") return <AlertTriangle size={18} color="var(--color-uncertain)" />;
  return <XCircle size={18} color="var(--color-unsupported)" />;
}

/* =========================================================================== */
/*  EVIDENCE PLACEHOLDER CARD (injected inline for Task 8)                     */
/* =========================================================================== */

function EvidencePlaceholder({
  evidence,
  index,
}: {
  evidence: ContradictionEvidence;
  index: number;
}) {
  const color = SEVERITY_COLORS[evidence.severity] || "#6366F1";

  return (
    <div
      id={`evidence-placeholder-${index}`}
      style={{
        marginTop: 12,
        padding: "12px 16px",
        borderRadius: 10,
        background: `${color}10`,
        border: `1px solid ${color}30`,
      }}
    >
      {/* Signal badge */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <AlertCircle size={14} color={color} />
        <span
          style={{
            fontSize: "0.7rem",
            fontWeight: 700,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            color,
          }}
        >
          {SIGNAL_LABELS[evidence.signal] ?? evidence.signal}
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: "0.68rem",
            fontWeight: 600,
            padding: "2px 8px",
            borderRadius: 6,
            background: `${color}20`,
            color,
          }}
        >
          {evidence.severity}
        </span>
      </div>

      {/* Fragment comparison */}
      {(evidence.claim_fragment || evidence.source_fragment) && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 8,
            marginBottom: 8,
          }}
        >
          {evidence.claim_fragment && (
            <div
              style={{
                padding: "6px 10px",
                borderRadius: 6,
                background: "rgba(239,68,68,0.08)",
                fontSize: "0.78rem",
                color: "var(--color-text-secondary)",
                fontFamily: "monospace",
              }}
            >
              <span style={{ fontSize: "0.65rem", fontWeight: 600, color: "#EF4444", display: "block", marginBottom: 2 }}>
                CLAIM
              </span>
              {evidence.claim_fragment}
            </div>
          )}
          {evidence.source_fragment && (
            <div
              style={{
                padding: "6px 10px",
                borderRadius: 6,
                background: "rgba(34,197,94,0.08)",
                fontSize: "0.78rem",
                color: "var(--color-text-secondary)",
                fontFamily: "monospace",
              }}
            >
              <span style={{ fontSize: "0.65rem", fontWeight: 600, color: "#22C55E", display: "block", marginBottom: 2 }}>
                SOURCE
              </span>
              {evidence.source_fragment}
            </div>
          )}
        </div>
      )}

      {/* Explanation */}
      {evidence.explanation && (
        <p style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.5 }}>
          {evidence.explanation}
        </p>
      )}
    </div>
  );
}

/* =========================================================================== */
/*  CLAIM CARD                                                                  */
/* =========================================================================== */

function ClaimCard({ claim, index }: { claim: Claim; index: number }) {
  const color  = statusColor(claim.status);
  const bg     = statusBg(claim.status);
  const border = statusBorder(claim.status);

  const label =
    claim.status === "VERIFIED"   ? "✓  VERIFIED"  :
    claim.status === "UNCERTAIN"  ? "⚠  UNCERTAIN" :
    "✗  FLAGGED";

  return (
    <div
      style={{
        padding: "20px 22px",
        borderRadius: 14,
        background: bg,
        border: `1px solid ${border}`,
        marginBottom: 14,
      }}
    >
      {/* Top row — status + score */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 10 }}>
        <StatusIcon status={claim.status} />
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 6 }}>
            <span
              style={{
                fontSize: "0.7rem",
                fontWeight: 700,
                letterSpacing: "0.06em",
                color,
                padding: "3px 10px",
                borderRadius: 20,
                background: `${bg}`,
                border: `1px solid ${border}`,
              }}
            >
              {label}
            </span>
            <span style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)", marginLeft: "auto" }}>
              Score: {claim.similarity_score.toFixed(4)}
            </span>
          </div>

          {/* Claim text */}
          <p style={{ fontSize: "0.92rem", lineHeight: 1.55, margin: 0, color: "var(--color-text-primary, #F1F1F3)" }}>
            {claim.text}
          </p>

          {/* Matched source */}
          {claim.matched_source && (
            <p
              style={{
                fontSize: "0.78rem",
                color: "var(--color-text-secondary)",
                fontStyle: "italic",
                marginTop: 8,
                marginBottom: 0,
                lineHeight: 1.5,
              }}
            >
              Matched: &quot;{claim.matched_source}&quot;
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
          marginBottom: claim.contradiction_evidence ? 0 : 0,
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

      {/* Evidence placeholder — Task 8 animates this */}
      {claim.contradiction_evidence && (
        <EvidencePlaceholder evidence={claim.contradiction_evidence} index={index} />
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
    { label: "Verified",     count: summary.verified,     color: "var(--color-verified)",     bg: "rgba(34,197,94,0.1)",     border: "rgba(34,197,94,0.25)"  },
    { label: "Uncertain",    count: summary.uncertain,    color: "var(--color-uncertain)",    bg: "rgba(234,179,8,0.1)",     border: "rgba(234,179,8,0.25)"  },
    { label: "Unsupported",  count: summary.unsupported,  color: "var(--color-unsupported)",  bg: "rgba(239,68,68,0.1)",     border: "rgba(239,68,68,0.25)"  },
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
        marginBottom: 24,
        flexWrap: "wrap",
      }}
    >
      <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-text-secondary)" }}>
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
/*  MAIN PAGE                                                                   */
/* =========================================================================== */

export default function AnalyzePage() {
  const [aiResponse, setAiResponse]   = useState("");
  const [sourceDoc,  setSourceDoc]    = useState("");
  const [isLoading,  setIsLoading]    = useState(false);
  const [result,     setResult]       = useState<VerificationResult | null>(null);
  const [error,      setError]        = useState<string | null>(null);

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
      setError(err instanceof Error ? err.message : "Verification failed. Check your API key and connection.");
    } finally {
      setIsLoading(false);
    }
  };

  const canAnalyze = aiResponse.trim().length > 0 && sourceDoc.trim().length > 0 && !isLoading;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-bg-primary, #0A0A0F)",
        fontFamily: "Inter, sans-serif",
      }}
    >
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
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none" }}>
            <Shield size={22} color="#6366F1" />
            <span style={{ fontSize: "1rem", fontWeight: 700, color: "#F1F1F3" }}>TruthLayer</span>
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
            Dual-Signal Engine
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
            Paste any AI response and source document — watch the dual-signal engine verify
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
              <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} />
              Analyzing with Dual-Signal Engine...
            </>
          ) : (
            "Analyze with Dual-Signal Verification →"
          )}
        </button>

        {/* Spinner keyframes injected inline */}
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>

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
            <SummaryBar summary={result.summary} />

            <div style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, margin: 0 }}>
                Claim-by-Claim Results
              </h2>
              <span style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)", marginLeft: "auto" }}>
                {result.metadata?.latency_ms ? `${Math.round(result.metadata.latency_ms)}ms` : ""}
              </span>
            </div>

            {result.claims.map((claim, i) => (
              <ClaimCard key={i} claim={claim} index={i} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
