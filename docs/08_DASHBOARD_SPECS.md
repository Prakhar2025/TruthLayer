# Dashboard Specifications

## 1. Overview

The TruthLayer Dashboard provides real-time monitoring of verification operations, document management, and analytics visualization.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRUTHLAYER DASHBOARD                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │Overview │  │Documents│  │ History │  │Analytics│  │Settings │           │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   [ Main Content Area ]                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. UI Component Breakdown

### 2.1 Navigation Sidebar

```
┌──────────────────┐
│  🛡️ TruthLayer   │  ← Logo
├──────────────────┤
│  📊 Overview     │  ← Active indicator
│  📁 Documents    │
│  🕐 History      │
│  📈 Analytics    │
│  ⚙️ Settings     │
├──────────────────┤
│  API Usage       │  ← Footer stats
│  ████░░ 45%      │
│  4,500/10,000    │
└──────────────────┘
```

**Component Props:**
```typescript
interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  badge?: number;  // Notification count
}

interface Sidebar {
  items: NavItem[];
  activeItem: string;
  usageStats: {
    current: number;
    limit: number;
    percentage: number;
  };
}
```

### 2.2 Overview Page

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Overview                                              [Period: 24h ▼]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Verifications│  │ Avg Score    │  │ Avg Latency  │  │ Claims       │ │
│  │    1,247     │  │   76.4%      │  │   72ms       │  │   4,521      │ │
│  │   ↑ 12%      │  │   ↑ 3%       │  │   ↓ 8ms      │  │   ↑ 15%      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                    Verification Trend (24h)                          ││
│  │  100 ─┤                                    ╭─────                   ││
│  │   80 ─┤              ╭────╮   ╭───╮       │                         ││
│  │   60 ─┤    ╭───╮    │    │   │   │   ╭───╯                          ││
│  │   40 ─┤───╯   ╰────╯    ╰───╯   ╰───╯                               ││
│  │   20 ─┤                                                              ││
│  │       └──────────────────────────────────────────────────────────    ││
│  │        00:00    04:00    08:00    12:00    16:00    20:00    24:00   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ┌─────────────────────────┐  ┌────────────────────────────────────────┐│
│  │    Verdict Distribution │  │        Recent Verifications            ││
│  │                         │  │                                         ││
│  │    🟢 Verified    66%   │  │  • "Q4 Report" - Verified (92%)        ││
│  │    🟡 Uncertain   25%   │  │  • "Product FAQ" - Partial (71%)       ││
│  │    🔴 Unsupported  9%   │  │  • "HR Policy" - Unsupported (34%)     ││
│  │                         │  │  • "Tech Spec" - Verified (88%)        ││
│  │      [Donut Chart]      │  │  • "Sales Data" - Verified (95%)       ││
│  │                         │  │                                         ││
│  └─────────────────────────┘  └────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

**Component Structure:**
```typescript
// MetricCard Component
interface MetricCardProps {
  title: string;
  value: string | number;
  change: number;  // Percentage change
  changeDirection: 'up' | 'down';
  changePositive: boolean;  // Is the change good or bad?
}

// TrendChart Component
interface TrendChartProps {
  data: {
    timestamp: Date;
    value: number;
  }[];
  period: '1h' | '24h' | '7d' | '30d';
  yAxisLabel: string;
}

// VerdictDonut Component
interface VerdictDonutProps {
  verified: number;
  uncertain: number;
  unsupported: number;
}
```

### 2.3 Documents Page

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Documents                                    [+ Upload Document]       │
├─────────────────────────────────────────────────────────────────────────┤
│  🔍 Search documents...                        [Filter ▼] [Sort ▼]      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 📄 Q4 2024 Financial Report                                      │   │
│  │    Status: 🟢 Ready    Chunks: 127    Verifications: 234        │   │
│  │    Tags: finance, quarterly    Uploaded: 2 hours ago            │   │
│  │    [View Details] [Delete]                                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 📄 Product Documentation v2.1                                    │   │
│  │    Status: 🟡 Processing (45%)    Chunks: --    Verifications: 0│   │
│  │    Tags: product, docs    Uploaded: 5 minutes ago               │   │
│  │    [View Details] [Cancel]                                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 📄 HR Policy Handbook                                            │   │
│  │    Status: 🔴 Failed    Error: Unsupported file format          │   │
│  │    Tags: hr, policy    Uploaded: 1 day ago                      │   │
│  │    [Retry] [Delete]                                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│                         [Load More]                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Verification History Page

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Verification History                           [Export CSV]            │
├─────────────────────────────────────────────────────────────────────────┤
│  Filter: [All Verdicts ▼] [All Documents ▼] [Date Range: Last 7 days]  │
├───────┬────────────────┬───────────┬────────────┬────────────┬─────────┤
│ Score │ Verdict        │ Document  │ Claims     │ Latency    │ Time    │
├───────┼────────────────┼───────────┼────────────┼────────────┼─────────┤
│ 92%   │ 🟢 Verified    │ Q4 Report │ 5 claims   │ 67ms       │ 2m ago  │
├───────┼────────────────┼───────────┼────────────┼────────────┼─────────┤
│ 71%   │ 🟡 Partial     │ FAQ Doc   │ 8 claims   │ 89ms       │ 5m ago  │
├───────┼────────────────┼───────────┼────────────┼────────────┼─────────┤
│ 34%   │ 🔴 Unsupported │ HR Policy │ 3 claims   │ 45ms       │ 12m ago │
├───────┼────────────────┼───────────┼────────────┼────────────┼─────────┤
│ 88%   │ 🟢 Verified    │ Tech Spec │ 6 claims   │ 72ms       │ 1h ago  │
└───────┴────────────────┴───────────┴────────────┴────────────┴─────────┘
│                                                                          │
│  Showing 1-50 of 1,247          [Previous] [1] [2] [3] ... [25] [Next]  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.5 Verification Detail Modal

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Verification Details                                            [✕]   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Overall Score: ████████░░ 78%          Verdict: 🟡 PARTIALLY_VERIFIED  │
│  Document: Q4 2024 Financial Report     Processed: 87ms                │
│                                                                          │
│  ──────────────────────────────────────────────────────────────────────  │
│                                                                          │
│  AI Response:                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ "The company reported revenue of $4.2 billion for Q4 2024,        │ │
│  │  representing a 15% YoY increase. The company has 500 employees   │ │
│  │  across 12 global offices."                                        │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  Claims Breakdown:                                                       │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ 🟢 94% │ "revenue of $4.2 billion for Q4 2024"                     │ │
│  │        │ Source: "...reported revenue of $4.2 billion..."          │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │ 🟢 89% │ "15% YoY increase"                                        │ │
│  │        │ Source: "...representing a 15% year-over-year..."         │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │ 🔴 45% │ "500 employees"                                           │ │
│  │        │ No matching source found                                   │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │ 🟡 72% │ "12 global offices"                                       │ │
│  │        │ Source: "...operations in 14 countries..."                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│                                      [Copy JSON] [View Raw] [Close]     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Real-Time Visualization Requirements

### 3.1 WebSocket Connection

```typescript
// Real-time updates via WebSocket
interface WebSocketMessage {
  type: 'verification' | 'document' | 'analytics';
  action: 'created' | 'updated' | 'deleted';
  data: any;
  timestamp: string;
}

// Connection configuration
const wsConfig = {
  url: 'wss://api.truthlayer.io/v1/ws',
  reconnectInterval: 5000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000
};
```

### 3.2 Live Updates

| Data Type | Update Frequency | Trigger |
|-----------|------------------|---------|
| Verification count | Real-time | On each verification |
| Trend chart | 1 minute | Polling |
| Document status | Real-time | WebSocket |
| Analytics summary | 5 minutes | Polling |
| Recent verifications | Real-time | WebSocket |

### 3.3 Chart Libraries

```json
{
  "dependencies": {
    "recharts": "^2.10.0",
    "@tremor/react": "^3.12.0"
  }
}
```

---

## 4. Metrics to Display

### 4.1 Overview Metrics

| Metric | Description | Format |
|--------|-------------|--------|
| Total Verifications | Count in period | Integer with comma separators |
| Average Confidence | Mean score | Percentage (XX.X%) |
| Average Latency | Mean processing time | Xms |
| Claims Processed | Total claims verified | Integer |
| Verified Rate | % of VERIFIED verdicts | Percentage |
| API Usage | Requests vs limit | Progress bar + fraction |

### 4.2 Document Metrics

| Metric | Description |
|--------|-------------|
| Status | READY, PROCESSING, FAILED |
| Chunks Count | Number of text chunks |
| Verification Count | Times used for verification |
| File Size | Original file size |
| Processing Time | Time to process document |

### 4.3 Verification Metrics

| Metric | Description |
|--------|-------------|
| Overall Score | 0-100% confidence |
| Verdict | VERIFIED, PARTIAL, UNSUPPORTED |
| Claims Count | Number of claims extracted |
| Processing Time | End-to-end latency |
| Matched Chunks | Chunks with high similarity |

---

## 5. User Interaction Flows

### 5.1 Document Upload Flow

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Click  │────▶│ Select  │────▶│ Upload  │────▶│Processing│───▶│  Ready  │
│ Upload  │     │  File   │     │ Started │     │ Status   │     │ to Use  │
└─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘
                                     │               │
                                     ▼               ▼
                              [Progress Bar]  [Real-time %]
```

### 5.2 Verification Testing Flow (Dashboard)

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Select  │────▶│  Enter  │────▶│  Click  │────▶│  View   │
│Document │     │AI Text  │     │ Verify  │     │ Result  │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
```

### 5.3 Filter & Search Flow

```
User enters search query
        │
        ▼
┌─────────────────┐
│ Debounce 300ms  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ API Request     │────▶│ Update Results  │
│ with filters    │     │ with animation  │
└─────────────────┘     └─────────────────┘
```

---

## 6. Color Coding System

### 6.1 Verdict Colors

```css
:root {
  /* Verified - Green */
  --color-verified: #22c55e;
  --color-verified-bg: #dcfce7;
  --color-verified-border: #86efac;
  
  /* Uncertain - Yellow/Amber */
  --color-uncertain: #f59e0b;
  --color-uncertain-bg: #fef3c7;
  --color-uncertain-border: #fcd34d;
  
  /* Unsupported - Red */
  --color-unsupported: #ef4444;
  --color-unsupported-bg: #fee2e2;
  --color-unsupported-border: #fca5a5;
}
```

### 6.2 Score Color Gradient

```typescript
function getScoreColor(score: number): string {
  if (score >= 0.85) return '#22c55e';  // Green
  if (score >= 0.70) return '#84cc16';  // Light green
  if (score >= 0.60) return '#f59e0b';  // Amber
  if (score >= 0.45) return '#f97316';  // Orange
  return '#ef4444';                      // Red
}
```

### 6.3 Status Colors

| Status | Color | Hex |
|--------|-------|-----|
| Ready | Green | #22c55e |
| Processing | Blue | #3b82f6 |
| Failed | Red | #ef4444 |
| Pending | Gray | #6b7280 |

### 6.4 Accessibility

- All color combinations meet WCAG 2.1 AA contrast requirements
- Icons accompany colors for colorblind users
- Text labels for all status indicators
