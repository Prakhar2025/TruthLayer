"use client";

import { motion } from "framer-motion";
import {
    FileText,
    Upload,
    Trash2,
    Clock,
    Plus,
    Eye,
    X,
} from "lucide-react";
import { useState, useEffect } from "react";
import {
    listDocuments,
    uploadDocument,
    deleteDocument,
    type Document,
} from "@/lib/api";

export default function DocumentsPage() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [showUpload, setShowUpload] = useState(false);
    const [title, setTitle] = useState("");
    const [content, setContent] = useState("");
    const [uploading, setUploading] = useState(false);
    const [viewDoc, setViewDoc] = useState<Document | null>(null);

    // Load documents
    useEffect(() => {
        loadDocs();
    }, []);

    const loadDocs = async () => {
        setLoading(true);
        try {
            const res = await listDocuments();
            setDocuments(res.documents);
        } catch {
            // Demo data
            setDocuments([
                { document_id: "demo-1", title: "Python 3.11 Release Notes", content_length: 2340, created_at: Date.now() / 1000 - 3600 },
                { document_id: "demo-2", title: "AWS Lambda Best Practices", content_length: 5120, created_at: Date.now() / 1000 - 86400 },
                { document_id: "demo-3", title: "Machine Learning Fundamentals", content_length: 8940, created_at: Date.now() / 1000 - 172800 },
            ]);
        }
        setLoading(false);
    };

    const handleUpload = async () => {
        if (!content.trim()) return;
        setUploading(true);
        try {
            await uploadDocument(title || "Untitled Document", content);
            setTitle("");
            setContent("");
            setShowUpload(false);
            await loadDocs();
        } catch {
            // Demo mode - just add locally
            setDocuments((prev) => [
                {
                    document_id: `demo-${Date.now()}`,
                    title: title || "Untitled Document",
                    content_length: content.length,
                    created_at: Date.now() / 1000,
                },
                ...prev,
            ]);
            setTitle("");
            setContent("");
            setShowUpload(false);
        }
        setUploading(false);
    };

    const handleDelete = async (id: string) => {
        try {
            await deleteDocument(id);
        } catch {
            // Demo mode
        }
        setDocuments((prev) => prev.filter((d) => d.document_id !== id));
    };

    const formatDate = (ts: number) => {
        const d = new Date(ts * 1000);
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    };

    const formatSize = (chars: number) => {
        if (chars > 10000) return `${(chars / 1000).toFixed(1)}K chars`;
        return `${chars.toLocaleString()} chars`;
    };

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
                <div>
                    <h1 style={{ fontSize: "1.6rem", fontWeight: 700, marginBottom: 4 }}>Documents</h1>
                    <p style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                        Manage source documents for verification
                    </p>
                </div>
                <button
                    className="btn-primary"
                    onClick={() => setShowUpload(!showUpload)}
                    style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem" }}
                >
                    {showUpload ? <X size={16} /> : <Plus size={16} />}
                    {showUpload ? "Cancel" : "Upload Document"}
                </button>
            </div>

            {/* Upload Form */}
            {showUpload && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="glass-card"
                    style={{ padding: 24, marginBottom: 20 }}
                >
                    <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16 }}>Upload New Document</h3>
                    <div style={{ marginBottom: 14 }}>
                        <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                            Document Title
                        </label>
                        <input
                            className="input-field"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="Enter document title..."
                        />
                    </div>
                    <div style={{ marginBottom: 16 }}>
                        <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: 6 }}>
                            Content
                        </label>
                        <textarea
                            className="input-field"
                            rows={8}
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            placeholder="Paste document content here..."
                        />
                    </div>
                    <button
                        className="btn-primary"
                        onClick={handleUpload}
                        disabled={uploading || !content.trim()}
                        style={{ display: "flex", alignItems: "center", gap: 6 }}
                    >
                        <Upload size={16} />
                        {uploading ? "Uploading..." : "Upload Document"}
                    </button>
                </motion.div>
            )}

            {/* Documents List */}
            {loading ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="skeleton" style={{ height: 80, borderRadius: 12 }} />
                    ))}
                </div>
            ) : documents.length === 0 ? (
                <div
                    className="glass-card"
                    style={{
                        padding: "60px 24px",
                        textAlign: "center",
                        color: "var(--color-text-secondary)",
                    }}
                >
                    <FileText size={40} style={{ marginBottom: 16, opacity: 0.4 }} />
                    <p style={{ fontSize: "1rem", marginBottom: 8 }}>No documents yet</p>
                    <p style={{ fontSize: "0.85rem" }}>Upload source documents to verify AI responses against.</p>
                </div>
            ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {documents.map((doc, i) => (
                        <motion.div
                            key={doc.document_id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="glass-card"
                            style={{
                                padding: "18px 22px",
                                display: "flex",
                                alignItems: "center",
                                gap: 16,
                            }}
                        >
                            <div
                                style={{
                                    width: 42,
                                    height: 42,
                                    borderRadius: 10,
                                    background: "rgba(99, 102, 241, 0.1)",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    flexShrink: 0,
                                }}
                            >
                                <FileText size={20} color="#6366F1" />
                            </div>

                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: 4 }}>
                                    {doc.title}
                                </div>
                                <div style={{ display: "flex", gap: 16, fontSize: "0.78rem", color: "var(--color-text-secondary)" }}>
                                    <span>{formatSize(doc.content_length)}</span>
                                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                        <Clock size={12} /> {formatDate(doc.created_at)}
                                    </span>
                                </div>
                            </div>

                            <button
                                onClick={() => handleDelete(doc.document_id)}
                                style={{
                                    background: "transparent",
                                    border: "none",
                                    cursor: "pointer",
                                    padding: 8,
                                    borderRadius: 8,
                                    transition: "background 0.2s",
                                    color: "var(--color-text-secondary)",
                                }}
                                onMouseOver={(e) => {
                                    (e.target as HTMLElement).style.background = "rgba(239, 68, 68, 0.1)";
                                    (e.target as HTMLElement).style.color = "var(--color-unsupported)";
                                }}
                                onMouseOut={(e) => {
                                    (e.target as HTMLElement).style.background = "transparent";
                                    (e.target as HTMLElement).style.color = "var(--color-text-secondary)";
                                }}
                            >
                                <Trash2 size={16} />
                            </button>
                        </motion.div>
                    ))}
                </div>
            )}
        </div>
    );
}
