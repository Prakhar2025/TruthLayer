"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    Shield,
    Search,
    FileText,
    BarChart3,
    Settings,
    Home,
} from "lucide-react";
import { ReactNode } from "react";

export default function DashboardLayout({
    children,
}: {
    children: ReactNode;
}) {
    const pathname = usePathname();

    const links = [
        { href: "/dashboard", icon: Home, label: "Overview" },
        { href: "/dashboard/verify", icon: Search, label: "Verify" },
        { href: "/dashboard/documents", icon: FileText, label: "Documents" },
        { href: "/dashboard/analytics", icon: BarChart3, label: "Analytics" },
    ];

    return (
        <div style={{ display: "flex", minHeight: "100vh" }}>
            {/* Sidebar */}
            <aside
                style={{
                    width: 240,
                    background: "var(--color-bg-secondary)",
                    borderRight: "1px solid var(--color-border)",
                    padding: "20px 12px",
                    display: "flex",
                    flexDirection: "column",
                    position: "fixed",
                    top: 0,
                    left: 0,
                    bottom: 0,
                    zIndex: 40,
                }}
            >
                <Link
                    href="/"
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        textDecoration: "none",
                        padding: "8px 16px",
                        marginBottom: 28,
                    }}
                >
                    <Shield size={24} color="#6366F1" />
                    <span style={{ fontSize: "1.05rem", fontWeight: 700, color: "#F1F1F3" }}>
                        TruthLayer
                    </span>
                </Link>

                <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    {links.map((link) => {
                        const isActive =
                            link.href === "/dashboard"
                                ? pathname === "/dashboard"
                                : pathname.startsWith(link.href);

                        return (
                            <Link
                                key={link.href}
                                href={link.href}
                                className={`sidebar-link ${isActive ? "active" : ""}`}
                            >
                                <link.icon size={18} />
                                {link.label}
                            </Link>
                        );
                    })}
                </nav>

                <div style={{ flex: 1 }} />

                {/* Bottom info */}
                <div
                    style={{
                        padding: "14px 16px",
                        borderRadius: 12,
                        background: "rgba(99, 102, 241, 0.06)",
                        border: "1px solid rgba(99, 102, 241, 0.1)",
                    }}
                >
                    <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "#818CF8", marginBottom: 4 }}>
                        AWS Free Tier
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                        Powered by Bedrock,<br />Lambda & DynamoDB
                    </div>
                </div>
            </aside>

            {/* Main content */}
            <main
                className="gradient-bg"
                style={{
                    flex: 1,
                    marginLeft: 240,
                    padding: "28px 32px",
                    minHeight: "100vh",
                }}
            >
                {children}
            </main>
        </div>
    );
}
