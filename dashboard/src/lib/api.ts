/**
 * TruthLayer API Client
 * Communicates with the TruthLayer API Gateway backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://your-api-url.execute-api.us-east-1.amazonaws.com/prod';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

interface VerifyRequest {
  ai_response: string;
  source_documents: string[];
}

interface Claim {
  text: string;
  status: 'VERIFIED' | 'UNCERTAIN' | 'UNSUPPORTED';
  confidence: number;
  similarity_score: number;
  matched_source: string;
}

interface VerifyResponse {
  claims: Claim[];
  summary: {
    verified: number;
    uncertain: number;
    unsupported: number;
  };
  metadata: {
    latency_ms: number;
    embedding_ms: number;
    provider: string;
    total_claims: number;
    source_chunks: number;
    request_id?: string;
  };
}

interface Document {
  document_id: string;
  title: string;
  content?: string;
  content_length: number;
  created_at: number;
  metadata?: Record<string, string>;
}

interface AnalyticsSummary {
  total_verifications: number;
  total_claims: number;
  avg_latency_ms: number;
  accuracy_breakdown: {
    verified: number;
    uncertain: number;
    unsupported: number;
  };
  verification_rate: number;
}

interface TrendData {
  date: string;
  verifications: number;
  verified: number;
  uncertain: number;
  unsupported: number;
  avg_latency_ms: number;
}

async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(API_KEY && { 'x-api-key': API_KEY }),
    ...(options.headers as Record<string, string> || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.message || `API error: ${response.status}`);
  }

  return data as T;
}

// ---- Verify ----
export async function verifyResponse(
  aiResponse: string,
  sourceDocuments: string[]
): Promise<VerifyResponse> {
  return apiCall<VerifyResponse>('/verify', {
    method: 'POST',
    body: JSON.stringify({
      ai_response: aiResponse,
      source_documents: sourceDocuments,
    }),
  });
}

// ---- Documents ----
export async function uploadDocument(
  title: string,
  content: string,
  metadata?: Record<string, string>
): Promise<{ document_id: string; message: string }> {
  return apiCall('/documents', {
    method: 'POST',
    body: JSON.stringify({ title, content, metadata }),
  });
}

export async function listDocuments(
  limit = 50
): Promise<{ documents: Document[]; count: number }> {
  return apiCall(`/documents?limit=${limit}`);
}

export async function getDocument(id: string): Promise<Document> {
  return apiCall(`/documents/${id}`);
}

export async function deleteDocument(id: string): Promise<{ message: string }> {
  return apiCall(`/documents/${id}`, { method: 'DELETE' });
}

// ---- Analytics ----
export async function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  return apiCall('/analytics?action=summary');
}

export async function getAnalyticsTrends(
  days = 7
): Promise<{ trends: TrendData[]; days: number }> {
  return apiCall(`/analytics?action=trends&days=${days}`);
}

export async function getRecentVerifications(
  limit = 20
): Promise<{ verifications: any[]; count: number }> {
  return apiCall(`/analytics?action=recent&limit=${limit}`);
}

// ---- Health ----
export async function checkHealth(): Promise<{
  status: string;
  version: string;
}> {
  return apiCall('/health');
}

// ---- API Keys ----
interface GenerateKeyResponse {
  api_key: string;
  owner: string;
  permissions: string[];
  rate_limit: number;
  message: string;
}

export async function generateApiKey(
  owner: string,
  email: string,
  useCase?: string,
): Promise<GenerateKeyResponse> {
  // Note: this endpoint does NOT require an existing x-api-key header.
  // We call the API directly without the shared API_KEY.
  const url = `${API_URL}/keys`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ owner, email, use_case: useCase || '' }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || `API error: ${response.status}`);
  }
  return data as GenerateKeyResponse;
}

// ---- Types re-export ----
export type {
  Claim,
  VerifyRequest,
  VerifyResponse,
  Document,
  AnalyticsSummary,
  TrendData,
  GenerateKeyResponse,
};
