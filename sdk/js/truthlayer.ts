/**
 * TruthLayer JavaScript/TypeScript SDK
 * One-line AI hallucination verification
 *
 * Usage:
 *   import { TruthLayer } from './truthlayer';
 *   const tl = new TruthLayer({ apiKey: 'tl_xxx', apiUrl: 'https://your-api/prod' });
 *   const result = await tl.verify('AI output', ['source doc']);
 *   console.log(result.trustScore, result.hasHallucinations);
 */

export interface Claim {
    text: string;
    status: 'VERIFIED' | 'UNCERTAIN' | 'UNSUPPORTED';
    confidence: number;
    similarityScore: number;
    matchedSource: string;
}

export interface VerificationSummary {
    verified: number;
    uncertain: number;
    unsupported: number;
}

export interface VerificationMetadata {
    latencyMs: number;
    embeddingMs: number;
    provider: string;
    totalClaims: number;
    sourceChunks: number;
    requestId?: string;
}

export interface VerificationResult {
    claims: Claim[];
    summary: VerificationSummary;
    metadata: VerificationMetadata;
    trustScore: number;
    hasHallucinations: boolean;
    raw: any;
}

export interface TruthLayerConfig {
    apiKey: string;
    apiUrl?: string;
    timeout?: number;
}

export class TruthLayerError extends Error {
    statusCode: number;
    constructor(message: string, statusCode: number = 0) {
        super(message);
        this.name = 'TruthLayerError';
        this.statusCode = statusCode;
    }
}

export class TruthLayer {
    private apiKey: string;
    private apiUrl: string;
    private timeout: number;

    constructor(config: TruthLayerConfig) {
        this.apiKey = config.apiKey;
        this.apiUrl = (config.apiUrl || 'https://your-api.execute-api.us-east-1.amazonaws.com/prod').replace(/\/$/, '');
        this.timeout = config.timeout || 30000;
    }

    /**
     * Verify an AI response against source documents.
     */
    async verify(aiResponse: string, sourceDocuments: string[]): Promise<VerificationResult> {
        const data = await this.request('POST', '/verify', {
            ai_response: aiResponse,
            source_documents: sourceDocuments,
        });

        const claims: Claim[] = (data.claims || []).map((c: any) => ({
            text: c.text,
            status: c.status,
            confidence: c.confidence,
            similarityScore: c.similarity_score,
            matchedSource: c.matched_source || '',
        }));

        const summary: VerificationSummary = data.summary || { verified: 0, uncertain: 0, unsupported: 0 };

        const metadata: VerificationMetadata = {
            latencyMs: data.metadata?.latency_ms || 0,
            embeddingMs: data.metadata?.embedding_ms || 0,
            provider: data.metadata?.provider || '',
            totalClaims: data.metadata?.total_claims || 0,
            sourceChunks: data.metadata?.source_chunks || 0,
            requestId: data.metadata?.request_id,
        };

        // Compute trust score
        const verifiedConfidence = claims
            .filter((c) => c.status === 'VERIFIED')
            .reduce((sum, c) => sum + c.confidence, 0);
        const trustScore = claims.length > 0 ? Math.round((verifiedConfidence / claims.length) * 100) / 100 : 0;

        return {
            claims,
            summary,
            metadata,
            trustScore,
            hasHallucinations: summary.unsupported > 0,
            raw: data,
        };
    }

    /**
     * Check API health.
     */
    async health(): Promise<{ status: string; version: string }> {
        return this.request('GET', '/health');
    }

    private async request(method: string, endpoint: string, body?: any): Promise<any> {
        const url = `${this.apiUrl}${endpoint}`;

        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), this.timeout);

        try {
            const response = await fetch(url, {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': this.apiKey,
                },
                body: body ? JSON.stringify(body) : undefined,
                signal: controller.signal,
            });

            const data = await response.json();

            if (!response.ok) {
                throw new TruthLayerError(data.message || `API error: ${response.status}`, response.status);
            }

            return data;
        } catch (err: any) {
            if (err instanceof TruthLayerError) throw err;
            throw new TruthLayerError(`Request failed: ${err.message}`);
        } finally {
            clearTimeout(timer);
        }
    }
}

export default TruthLayer;
