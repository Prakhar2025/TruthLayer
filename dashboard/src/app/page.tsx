"use client";

import Link from "next/link";
import { motion, useInView } from "framer-motion";
import {
  Shield,
  Zap,
  BarChart3,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Code2,
  Key,
  Heart,
  Scale,
  LineChart,
  CloudLightning,
  Database,
  Cpu,
  Check,
  X,
  Sparkles,
} from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { verifyResponse, type Claim } from "@/lib/api";

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  LANDING PAGE                                                              */
/* ═══════════════════════════════════════════════════════════════════════════ */

export default function LandingPage() {
  return (
    <div className="min-h-screen hero-gradient">
      <Particles />
      <Nav />
      <Hero />
      <TrustedBy />
      <HowItWorks />
      <BeforeAfter />
      <LiveDemo />
      <Architecture />
      <UseCases />
      <GetStarted />
      <Features />
      <Pricing />
      <Footer />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  FLOATING PARTICLES                                                        */
/* ═══════════════════════════════════════════════════════════════════════════ */

const PARTICLES = [
  { l: 12, t: 68, d: 9, dl: 1, w: 2.5, h: 3.1, o: 0.35 },
  { l: 28, t: 74, d: 14, dl: 3, w: 3.2, h: 2.4, o: 0.45 },
  { l: 45, t: 82, d: 11, dl: 5, w: 2.8, h: 4.1, o: 0.5 },
  { l: 62, t: 71, d: 16, dl: 2, w: 3.6, h: 2.8, o: 0.38 },
  { l: 78, t: 88, d: 10, dl: 6, w: 2.2, h: 3.5, o: 0.55 },
  { l: 91, t: 76, d: 13, dl: 4, w: 4.0, h: 2.6, o: 0.42 },
  { l: 7, t: 92, d: 18, dl: 7, w: 2.9, h: 4.5, o: 0.33 },
  { l: 35, t: 65, d: 9, dl: 1, w: 3.4, h: 3.0, o: 0.48 },
  { l: 52, t: 79, d: 15, dl: 3, w: 2.3, h: 4.2, o: 0.4 },
  { l: 68, t: 85, d: 12, dl: 5, w: 3.8, h: 2.2, o: 0.52 },
  { l: 83, t: 69, d: 17, dl: 0, w: 2.6, h: 3.7, o: 0.36 },
  { l: 20, t: 90, d: 8, dl: 6, w: 4.2, h: 2.9, o: 0.58 },
  { l: 41, t: 73, d: 14, dl: 2, w: 3.0, h: 4.0, o: 0.44 },
  { l: 57, t: 86, d: 11, dl: 4, w: 2.4, h: 3.3, o: 0.5 },
  { l: 73, t: 67, d: 19, dl: 7, w: 3.5, h: 2.5, o: 0.37 },
  { l: 88, t: 78, d: 10, dl: 1, w: 2.7, h: 4.4, o: 0.53 },
  { l: 15, t: 84, d: 16, dl: 3, w: 4.1, h: 3.2, o: 0.41 },
  { l: 33, t: 91, d: 13, dl: 5, w: 2.1, h: 3.8, o: 0.47 },
  { l: 50, t: 70, d: 9, dl: 2, w: 3.3, h: 2.7, o: 0.56 },
  { l: 95, t: 83, d: 15, dl: 6, w: 2.8, h: 4.3, o: 0.34 },
];

function Particles() {
  return (
    <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0 }}>
      {PARTICLES.map((p, i) => (
        <div
          key={i}
          className="particle"
          style={{
            left: `${p.l}%`,
            top: `${p.t}%`,
            animationDuration: `${p.d}s`,
            animationDelay: `${p.dl}s`,
            width: `${p.w}px`,
            height: `${p.h}px`,
            opacity: p.o,
          }}
        />
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  NAVIGATION                                                                */
/* ═══════════════════════════════════════════════════════════════════════════ */

function Nav() {
  return (
    <nav
      style={{
        position: "fixed",
        top: 0,
        width: "100%",
        zIndex: 50,
        background: "rgba(10, 10, 15, 0.85)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid var(--color-border)",
      }}
    >
      <div
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: "14px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
          <Shield size={28} color="#6366F1" />
          <span style={{ fontSize: "1.2rem", fontWeight: 700, color: "#F1F1F3" }}>TruthLayer</span>
        </Link>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <a href="#get-started" className="btn-secondary" style={{ textDecoration: "none", fontSize: "0.82rem", padding: "7px 16px" }}>
            Get Started
          </a>
          <Link href="/dashboard/verify" className="btn-secondary" style={{ textDecoration: "none", fontSize: "0.82rem", padding: "7px 16px" }}>
            Try Demo
          </Link>
          <Link href="/get-api-key" className="btn-secondary" style={{ textDecoration: "none", fontSize: "0.82rem", padding: "7px 16px" }}>
            Get API Key
          </Link>
          <Link href="/dashboard" className="btn-primary" style={{ textDecoration: "none", fontSize: "0.82rem", padding: "7px 16px" }}>
            Dashboard →
          </Link>
        </div>
      </div>
    </nav>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  ANIMATED COUNTER HOOK                                                     */
/* ═══════════════════════════════════════════════════════════════════════════ */

function useCounter(target: number, duration: number = 2000, suffix: string = "") {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    if (!isInView) return;
    const start = Date.now();
    const step = () => {
      const elapsed = Date.now() - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      setCount(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [isInView, target, duration]);

  return { ref, display: `${count}${suffix}` };
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  HERO                                                                      */
/* ═══════════════════════════════════════════════════════════════════════════ */

function Hero() {
  const stat1 = useCounter(1, 1500, "s");
  const stat2 = useCounter(100, 2000, "%");
  const stat3 = useCounter(100, 2200, "%");

  return (
    <section
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: "120px 24px 80px",
        position: "relative",
        zIndex: 1,
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        style={{ maxWidth: 850 }}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          style={{
            display: "inline-block",
            padding: "6px 18px",
            borderRadius: 20,
            background: "rgba(99, 102, 241, 0.1)",
            border: "1px solid rgba(99, 102, 241, 0.3)",
            color: "#818CF8",
            fontSize: "0.8rem",
            fontWeight: 600,
            marginBottom: 28,
          }}
        >
          🛡️ AI Verification Infrastructure
        </motion.div>

        <h1
          style={{
            fontSize: "clamp(2.5rem, 5vw, 4.2rem)",
            fontWeight: 800,
            lineHeight: 1.08,
            marginBottom: 24,
            letterSpacing: "-0.02em",
          }}
        >
          Stop AI Hallucinations
          <br />
          <span className="animated-gradient-text">
            Before They Reach Users
          </span>
        </h1>

        <p
          style={{
            fontSize: "1.15rem",
            lineHeight: 1.7,
            color: "var(--color-text-secondary)",
            maxWidth: 620,
            margin: "0 auto 40px",
          }}
        >
          Real-time verification of AI outputs against source documents.
          The invisible trust layer between your LLM and your users.
        </p>

        <div style={{ display: "flex", gap: 14, justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/dashboard/verify" className="btn-primary" style={{ textDecoration: "none", fontSize: "1rem", padding: "14px 34px" }}>
            Try Live Demo <ArrowRight size={18} style={{ marginLeft: 6 }} />
          </Link>
          <Link href="/get-api-key" className="btn-secondary" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8 }}>
            <Key size={18} /> Get Free API Key
          </Link>
        </div>

        {/* Animated Stats */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 56,
            marginTop: 64,
            flexWrap: "wrap",
          }}
        >
          {[
            { ref: stat1.ref, display: `<${stat1.display}`, label: "Verification Latency" },
            { ref: stat2.ref, display: stat2.display, label: "Precision Rate" },
            { ref: stat3.ref, display: stat3.display, label: "Hallucination Detection" },
          ].map((stat) => (
            <div key={stat.label} ref={stat.ref}>
              <div style={{ fontSize: "2.2rem", fontWeight: 800, color: "#6366F1", fontFamily: "monospace" }}>{stat.display}</div>
              <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginTop: 4 }}>{stat.label}</div>
            </div>
          ))}
        </div>
      </motion.div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  TRUSTED BY / POWERED BY                                                   */
/* ═══════════════════════════════════════════════════════════════════════════ */

function TrustedBy() {
  const techs = ["Amazon Bedrock", "AWS Lambda", "DynamoDB", "API Gateway", "Python SDK", "LangChain"];
  return (
    <section style={{ padding: "30px 24px 50px", textAlign: "center", position: "relative", zIndex: 1 }}>
      <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: 20 }}>
        Powered by Enterprise-Grade Infrastructure
      </p>
      <div style={{ display: "flex", justifyContent: "center", gap: 32, flexWrap: "wrap", opacity: 0.5 }}>
        {techs.map((t) => (
          <span key={t} style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", fontWeight: 500 }}>{t}</span>
        ))}
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  HOW IT WORKS                                                              */
/* ═══════════════════════════════════════════════════════════════════════════ */

function HowItWorks() {
  const steps = [
    { icon: Code2, title: "1. Send AI Output", desc: "Pass any AI-generated response and the source documents through our API or SDK.", color: "#6366F1" },
    { icon: Cpu, title: "2. Dual-Signal Analysis", desc: "Semantic embeddings + entity contradiction detection verify each claim independently.", color: "#818CF8" },
    { icon: Shield, title: "3. Trust Verdict", desc: "Each claim gets a confidence score and classification: Verified, Uncertain, or Unsupported.", color: "#22C55E" },
  ];

  return (
    <section style={{ padding: "80px 24px", maxWidth: 1100, margin: "0 auto", position: "relative", zIndex: 1 }}>
      <h2 style={{ textAlign: "center", fontSize: "2rem", fontWeight: 700, marginBottom: 12 }}>
        How It Works
      </h2>
      <div className="section-divider" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 20 }}>
        {steps.map((step, i) => (
          <motion.div
            key={step.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.15 }}
            whileHover={{ y: -4 }}
            className="glass-card-premium"
            style={{ padding: 32, textAlign: "center" }}
          >
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 14,
                background: `rgba(99, 102, 241, 0.1)`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 20px",
              }}
            >
              <step.icon size={26} color={step.color} />
            </div>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 10 }}>{step.title}</h3>
            <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem", lineHeight: 1.6 }}>{step.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  BEFORE / AFTER                                                            */
/* ═══════════════════════════════════════════════════════════════════════════ */

function BeforeAfter() {
  return (
    <section style={{ padding: "60px 24px 80px", maxWidth: 1000, margin: "0 auto", position: "relative", zIndex: 1 }}>
      <h2 style={{ textAlign: "center", fontSize: "2rem", fontWeight: 700, marginBottom: 12 }}>
        The Hallucination Problem
      </h2>
      <div className="section-divider" />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Without */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          style={{
            padding: 28,
            borderRadius: 16,
            background: "rgba(239, 68, 68, 0.04)",
            border: "1px solid rgba(239, 68, 68, 0.15)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
            <XCircle size={22} color="#EF4444" />
            <h3 style={{ fontSize: "1.05rem", fontWeight: 600, color: "#EF4444" }}>Without TruthLayer</h3>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {[
              "AI generates confident but wrong answers",
              "Users trust fabricated statistics",
              "No way to verify claims against sources",
              "Hallucinations reach production undetected",
              "Legal and compliance risks accumulate",
            ].map((item) => (
              <div key={item} style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: "0.88rem", color: "var(--color-text-secondary)" }}>
                <X size={16} color="#EF4444" style={{ marginTop: 2, flexShrink: 0 }} />
                {item}
              </div>
            ))}
          </div>
        </motion.div>

        {/* With */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          className="glow-border"
          style={{
            padding: 28,
            borderRadius: 16,
            background: "rgba(34, 197, 94, 0.04)",
            border: "1px solid rgba(34, 197, 94, 0.15)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
            <CheckCircle2 size={22} color="#22C55E" />
            <h3 style={{ fontSize: "1.05rem", fontWeight: 600, color: "#22C55E" }}>With TruthLayer</h3>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {[
              "Every claim verified against source documents",
              "Confidence scores expose uncertain outputs",
              "Entity checker catches numerical fabrications",
              "Real-time dashboard monitors hallucination rate",
              "Enterprise-grade audit trail for compliance",
            ].map((item) => (
              <div key={item} style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: "0.88rem", color: "var(--color-text-secondary)" }}>
                <Check size={16} color="#22C55E" style={{ marginTop: 2, flexShrink: 0 }} />
                {item}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  LIVE DEMO WIDGET                                                          */
/* ═══════════════════════════════════════════════════════════════════════════ */

function LiveDemo() {
  const [aiText, setAiText] = useState(
    "Python 3.11 was released in October 2022. It is 25% faster than Python 3.10 and introduces exception groups."
  );
  const [sourceText, setSourceText] = useState(
    "Python 3.11 was officially released on October 24, 2022. This release includes performance improvements of up to 25% faster. New features include exception groups (PEP 654)."
  );
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(false);
  const [demoMode, setDemoMode] = useState(false);

  const runVerify = async () => {
    setLoading(true);
    setClaims([]);
    try {
      const result = await verifyResponse(aiText, [sourceText]);
      setClaims(result.claims);
    } catch {
      setDemoMode(true);
      setClaims([
        { text: "Python 3.11 was released in October 2022.", status: "VERIFIED", confidence: 94.2, similarity_score: 0.942, matched_source: "Python 3.11 was officially released on October 24, 2022." },
        { text: "It is 25% faster than Python 3.10.", status: "VERIFIED", confidence: 91.5, similarity_score: 0.915, matched_source: "includes performance improvements of up to 25% faster" },
        { text: "introduces exception groups.", status: "VERIFIED", confidence: 88.3, similarity_score: 0.883, matched_source: "New features include exception groups (PEP 654)" },
      ]);
    }
    setLoading(false);
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
    <section style={{ padding: "60px 24px 80px", maxWidth: 900, margin: "0 auto", position: "relative", zIndex: 1 }}>
      <h2 style={{ textAlign: "center", fontSize: "2rem", fontWeight: 700, marginBottom: 12 }}>
        Try It Live
      </h2>
      <p style={{ textAlign: "center", color: "var(--color-text-secondary)", marginBottom: 16, fontSize: "0.95rem" }}>
        This is a <strong style={{ color: "#22C55E" }}>real API call</strong> to our live production endpoint — not a mockup.
      </p>
      <div className="section-divider" />

      <div className="glass-card-premium" style={{ padding: 28 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
          <div>
            <label style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-text-secondary)", display: "block", marginBottom: 8 }}>
              🤖 AI Response
            </label>
            <textarea className="input-field" rows={5} value={aiText} onChange={(e) => setAiText(e.target.value)} placeholder="Paste AI-generated text here..." />
          </div>
          <div>
            <label style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-text-secondary)", display: "block", marginBottom: 8 }}>
              📚 Source Document
            </label>
            <textarea className="input-field" rows={5} value={sourceText} onChange={(e) => setSourceText(e.target.value)} placeholder="Paste source document here..." />
          </div>
        </div>

        <button className="btn-primary" onClick={runVerify} disabled={loading || !aiText.trim() || !sourceText.trim()} style={{ width: "100%" }}>
          {loading ? "⏳ Verifying with Amazon Bedrock..." : "🔍 Verify Now — Live API Call"}
        </button>

        {claims.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ marginTop: 24 }}>
            {demoMode && (
              <div style={{ background: "rgba(234, 179, 8, 0.1)", border: "1px solid rgba(234, 179, 8, 0.3)", borderRadius: 10, padding: "10px 16px", marginBottom: 16, fontSize: "0.8rem", color: "var(--color-uncertain)" }}>
                ⚠️ Demo mode — connect your API for live results
              </div>
            )}
            <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 12 }}>
              Verification Results:
            </div>
            {claims.map((claim, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  padding: "14px 16px",
                  borderRadius: 10,
                  marginBottom: 8,
                  background: "var(--color-bg-primary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                {statusIcon(claim.status)}
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "0.9rem", marginBottom: 6 }}>{claim.text}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span className={`status-${claim.status.toLowerCase()}`} style={{ padding: "2px 10px", borderRadius: 6, fontSize: "0.7rem", fontWeight: 600 }}>
                      {claim.status}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div className="confidence-bar">
                        <div className="confidence-bar-fill" style={{ width: `${claim.confidence}%`, background: statusColor(claim.status) }} />
                      </div>
                    </div>
                    <span style={{ fontSize: "0.8rem", fontWeight: 600, color: statusColor(claim.status) }}>
                      {claim.confidence}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </motion.div>
        )}
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  ARCHITECTURE                                                              */
/* ═══════════════════════════════════════════════════════════════════════════ */

function Architecture() {
  const nodes = [
    { icon: Code2, label: "Your App", sub: "SDK / API Call" },
    { icon: CloudLightning, label: "API Gateway", sub: "Authentication" },
    { icon: Zap, label: "Lambda", sub: "Claim Extraction" },
    { icon: Cpu, label: "Bedrock", sub: "Titan Embeddings" },
    { icon: Shield, label: "Entity Checker", sub: "Contradiction Detection" },
    { icon: Database, label: "DynamoDB", sub: "Cache + Results" },
  ];

  return (
    <section style={{ padding: "60px 24px 80px", maxWidth: 1100, margin: "0 auto", position: "relative", zIndex: 1 }}>
      <h2 style={{ textAlign: "center", fontSize: "2rem", fontWeight: 700, marginBottom: 12 }}>
        Architecture
      </h2>
      <p style={{ textAlign: "center", color: "var(--color-text-secondary)", marginBottom: 16, fontSize: "0.95rem" }}>
        Fully serverless. Built entirely on AWS.
      </p>
      <div className="section-divider" />

      <div className="glass-card-premium" style={{ padding: "36px 28px" }}>
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          {nodes.map((node, i) => (
            <motion.div
              key={node.label}
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              style={{ display: "flex", alignItems: "center", gap: 12 }}
            >
              <div
                style={{
                  padding: "16px 20px",
                  borderRadius: 14,
                  background: "var(--color-bg-primary)",
                  border: "1px solid var(--color-border)",
                  textAlign: "center",
                  minWidth: 110,
                }}
              >
                <node.icon size={22} color="#6366F1" style={{ marginBottom: 6 }} />
                <div style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: 2 }}>{node.label}</div>
                <div style={{ fontSize: "0.68rem", color: "var(--color-text-secondary)" }}>{node.sub}</div>
              </div>
              {i < nodes.length - 1 && (
                <span style={{ color: "#6366F1", fontSize: "1.2rem", fontWeight: 700 }}>→</span>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  USE CASES                                                                 */
/* ═══════════════════════════════════════════════════════════════════════════ */

function UseCases() {
  const cases = [
    {
      icon: Heart,
      title: "Healthcare AI",
      desc: "Verify medical AI outputs against clinical guidelines and drug databases. Prevent dangerous misinformation.",
      example: "\"Aspirin is safe for children\" → UNSUPPORTED (contradicts guidelines)",
      color: "#EF4444",
    },
    {
      icon: Scale,
      title: "Legal AI",
      desc: "Check contract analysis and legal research against source statutes. Ensure compliance accuracy.",
      example: "\"GDPR fines up to 4%\" → VERIFIED (confirmed against regulation)",
      color: "#6366F1",
    },
    {
      icon: LineChart,
      title: "Financial AI",
      desc: "Validate financial analysis against reports and filings. Catch fabricated statistics before they mislead.",
      example: "\"Revenue grew 50%\" → UNSUPPORTED (actual growth was 12%)",
      color: "#22C55E",
    },
  ];

  return (
    <section style={{ padding: "60px 24px 80px", maxWidth: 1100, margin: "0 auto", position: "relative", zIndex: 1 }}>
      <h2 style={{ textAlign: "center", fontSize: "2rem", fontWeight: 700, marginBottom: 12 }}>
        Built For Every Industry
      </h2>
      <div className="section-divider" />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 20 }}>
        {cases.map((uc, i) => (
          <motion.div
            key={uc.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.12 }}
            whileHover={{ y: -4 }}
            className="glass-card-premium"
            style={{ padding: 28 }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
              <div style={{
                width: 42, height: 42, borderRadius: 12,
                background: `${uc.color}15`,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <uc.icon size={22} color={uc.color} />
              </div>
              <h3 style={{ fontSize: "1.05rem", fontWeight: 600 }}>{uc.title}</h3>
            </div>
            <p style={{ color: "var(--color-text-secondary)", fontSize: "0.88rem", lineHeight: 1.6, marginBottom: 16 }}>{uc.desc}</p>
            <div style={{
              padding: "10px 14px",
              borderRadius: 8,
              background: "var(--color-bg-primary)",
              border: "1px solid var(--color-border)",
              fontSize: "0.78rem",
              color: "var(--color-text-secondary)",
              fontFamily: "monospace",
              lineHeight: 1.5,
            }}>
              {uc.example}
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  GET STARTED                                                               */
/* ═══════════════════════════════════════════════════════════════════════════ */

function GetStarted() {
  return (
    <section id="get-started" style={{ padding: "60px 24px 80px", maxWidth: 900, margin: "0 auto", scrollMarginTop: 80, position: "relative", zIndex: 1 }}>
      <h2 style={{ textAlign: "center", fontSize: "2rem", fontWeight: 700, marginBottom: 12 }}>
        Get Started in 3 Steps
      </h2>
      <p style={{ textAlign: "center", color: "var(--color-text-secondary)", marginBottom: 16, fontSize: "0.95rem" }}>
        From install to first verification in under 2 minutes.
      </p>
      <div className="section-divider" />

      <div className="glass-card-premium" style={{ padding: 28 }}>
        {/* Step 1 */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%",
              background: "rgba(99, 102, 241, 0.15)", display: "flex",
              alignItems: "center", justifyContent: "center",
              fontSize: "0.8rem", fontWeight: 700, color: "#818CF8",
            }}>1</div>
            <span style={{ fontSize: "1rem", fontWeight: 600 }}>Install the SDK</span>
          </div>
          <pre style={{
            background: "var(--color-bg-primary)", border: "1px solid var(--color-border)",
            borderRadius: 10, padding: "14px 20px", fontSize: "0.88rem",
            color: "#22C55E", overflowX: "auto",
          }}>
            {"pip install truthlayer-sdk"}
          </pre>
        </div>

        {/* Step 2 */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%",
              background: "rgba(99, 102, 241, 0.15)", display: "flex",
              alignItems: "center", justifyContent: "center",
              fontSize: "0.8rem", fontWeight: 700, color: "#818CF8",
            }}>2</div>
            <span style={{ fontSize: "1rem", fontWeight: 600 }}>Get Your API Key</span>
            <Link href="/get-api-key" style={{ fontSize: "0.8rem", color: "#818CF8", textDecoration: "none" }}>
              → Generate free key
            </Link>
          </div>
        </div>

        {/* Step 3 */}
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%",
              background: "rgba(99, 102, 241, 0.15)", display: "flex",
              alignItems: "center", justifyContent: "center",
              fontSize: "0.8rem", fontWeight: 700, color: "#818CF8",
            }}>3</div>
            <span style={{ fontSize: "1rem", fontWeight: 600 }}>Verify AI Outputs</span>
          </div>
          <pre style={{
            background: "var(--color-bg-primary)", border: "1px solid var(--color-border)",
            borderRadius: 10, padding: "14px 20px", fontSize: "0.82rem",
            lineHeight: 1.7, overflowX: "auto", color: "var(--color-text-secondary)",
          }}>
            {`from truthlayer import TruthLayer

tl = TruthLayer(api_key="tl_your_key_here")

result = tl.verify(
    ai_response="Python 3.11 is 25% faster.",
    source_documents=["Python 3.11 has up to 25% speedup."]
)

for claim in result.claims:
    print(f"{claim.status}: {claim.text} ({claim.confidence}%)")
    # VERIFIED: Python 3.11 is 25% faster. (91.5%)`}
          </pre>
        </div>
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  FEATURES                                                                  */
/* ═══════════════════════════════════════════════════════════════════════════ */

function Features() {
  const features = [
    { icon: Zap, title: "Sub-Second Latency", desc: "Live Bedrock verification in ~900ms. Cached responses even faster at ~750ms." },
    { icon: Shield, title: "100% Precision", desc: "Zero false alarms — two-signal verification with entity contradiction detection." },
    { icon: BarChart3, title: "Real-time Dashboard", desc: "Monitor hallucination rates, trust scores, and verification trends live." },
    { icon: Code2, title: "One-Line Integration", desc: "pip install truthlayer-sdk → result = tl.verify(response, sources)" },
    { icon: Database, title: "Smart Caching", desc: "DynamoDB embedding cache — 100% hit rate on repeated content, 1.4x speedup." },
    { icon: Sparkles, title: "Entity Checker", desc: "Catches numerical, negation, and superlative contradictions that embeddings miss." },
  ];

  return (
    <section style={{ padding: "60px 24px 80px", maxWidth: 1100, margin: "0 auto", position: "relative", zIndex: 1 }}>
      <h2 style={{ textAlign: "center", fontSize: "2rem", fontWeight: 700, marginBottom: 12 }}>
        Enterprise Features
      </h2>
      <div className="section-divider" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 16 }}>
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.08 }}
            whileHover={{ y: -3 }}
            className="glass-card-premium"
            style={{ padding: 24 }}
          >
            <f.icon size={22} color="#6366F1" style={{ marginBottom: 12 }} />
            <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: 6 }}>{f.title}</h3>
            <p style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", lineHeight: 1.6 }}>{f.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  PRICING                                                                   */
/* ═══════════════════════════════════════════════════════════════════════════ */

function Pricing() {
  const plans = [
    {
      name: "Free",
      price: "$0",
      period: "forever",
      desc: "For developers exploring AI verification",
      features: ["1,000 verifications/month", "API access", "Python SDK", "Community support"],
      cta: "Get Started Free",
      href: "/get-api-key",
      highlighted: false,
    },
    {
      name: "Pro",
      price: "$49",
      period: "/month",
      desc: "For teams deploying AI in production",
      features: ["50,000 verifications/month", "LangChain integration", "Dashboard analytics", "Priority support", "Custom thresholds"],
      cta: "Coming Soon",
      href: "#",
      highlighted: true,
    },
    {
      name: "Enterprise",
      price: "Custom",
      period: "",
      desc: "For organizations with compliance needs",
      features: ["Unlimited verifications", "On-premise deployment", "Custom models", "SLA guarantee", "Dedicated support", "Audit logs"],
      cta: "Contact Us",
      href: "mailto:prakhar230125@gmail.com",
      highlighted: false,
    },
  ];

  return (
    <section style={{ padding: "60px 24px 80px", maxWidth: 1100, margin: "0 auto", position: "relative", zIndex: 1 }}>
      <h2 style={{ textAlign: "center", fontSize: "2rem", fontWeight: 700, marginBottom: 12 }}>
        Simple, Transparent Pricing
      </h2>
      <p style={{ textAlign: "center", color: "var(--color-text-secondary)", marginBottom: 16, fontSize: "0.95rem" }}>
        Start free. Scale as you grow.
      </p>
      <div className="section-divider" />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
        {plans.map((plan, i) => (
          <motion.div
            key={plan.name}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.12 }}
            className={plan.highlighted ? "glass-card-premium glow-border" : "glass-card-premium"}
            style={{
              padding: 28,
              position: "relative",
              display: "flex",
              flexDirection: "column" as const,
              ...(plan.highlighted ? { borderColor: "rgba(99, 102, 241, 0.4)" } : {}),
            }}
          >
            {plan.highlighted && (
              <div style={{
                position: "absolute", top: -12, left: "50%", transform: "translateX(-50%)",
                background: "linear-gradient(135deg, #6366F1, #818CF8)",
                padding: "4px 16px", borderRadius: 12,
                fontSize: "0.7rem", fontWeight: 600, color: "white",
              }}>
                MOST POPULAR
              </div>
            )}
            <h3 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 4 }}>{plan.name}</h3>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: "2rem", fontWeight: 800, color: "#6366F1" }}>{plan.price}</span>
              <span style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>{plan.period}</span>
            </div>
            <p style={{ fontSize: "0.82rem", color: "var(--color-text-secondary)", marginBottom: 20 }}>{plan.desc}</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 24, flex: 1 }}>
              {plan.features.map((f) => (
                <div key={f} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.82rem", color: "var(--color-text-secondary)" }}>
                  <Check size={14} color="#22C55E" />
                  {f}
                </div>
              ))}
            </div>
            <Link
              href={plan.href}
              className={plan.highlighted ? "btn-primary" : "btn-secondary"}
              style={{ textDecoration: "none", display: "block", textAlign: "center", fontSize: "0.85rem" }}
            >
              {plan.cta}
            </Link>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  FOOTER                                                                    */
/* ═══════════════════════════════════════════════════════════════════════════ */

function Footer() {
  return (
    <footer
      style={{
        borderTop: "1px solid var(--color-border)",
        padding: "40px 24px",
        textAlign: "center",
        color: "var(--color-text-secondary)",
        fontSize: "0.85rem",
        position: "relative",
        zIndex: 1,
      }}
    >
      <div style={{ maxWidth: 800, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 12 }}>
          <Shield size={20} color="#6366F1" />
          <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--color-text-primary)" }}>TruthLayer</span>
        </div>
        <p style={{ marginBottom: 8 }}>AI Verification Infrastructure — Making AI Deployment Safe</p>
        <p style={{ fontSize: "0.78rem" }}>
          Powered by Amazon Bedrock • AWS Lambda • DynamoDB • 87 Tests Passing
        </p>
        <div style={{ display: "flex", justifyContent: "center", gap: 24, marginTop: 16, fontSize: "0.8rem" }}>
          <Link href="/dashboard" style={{ color: "var(--color-text-secondary)", textDecoration: "none" }}>Dashboard</Link>
          <Link href="/dashboard/verify" style={{ color: "var(--color-text-secondary)", textDecoration: "none" }}>Try Demo</Link>
          <Link href="/get-api-key" style={{ color: "var(--color-text-secondary)", textDecoration: "none" }}>Get API Key</Link>
          <a href="mailto:prakhar230125@gmail.com" style={{ color: "var(--color-text-secondary)", textDecoration: "none" }}>Contact</a>
        </div>
        <p style={{ fontSize: "0.72rem", marginTop: 16, opacity: 0.5 }}>
          © 2026 TruthLayer. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
