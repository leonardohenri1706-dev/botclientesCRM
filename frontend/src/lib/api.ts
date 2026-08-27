const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const campaignApi = {
  create: (data: { name: string; github_repo_url: string; target_niche?: string; ai_rules?: any }) =>
    fetchApi<Campaign>('/campaigns', { method: 'POST', body: JSON.stringify(data) }),

  list: (skip = 0, limit = 50) =>
    fetchApi<Campaign[]>(`/campaigns?skip=${skip}&limit=${limit}`),

  get: (id: string) =>
    fetchApi<Campaign>(`/campaigns/${id}`),

  update: (id: string, data: Partial<Campaign>) =>
    fetchApi<Campaign>(`/campaigns/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  delete: (id: string) =>
    fetchApi<void>(`/campaigns/${id}`, { method: 'DELETE' }),

  scrape: (id: string, data: ScrapingRequest) =>
    fetchApi<ScrapingResponse>(`/campaigns/${id}/scrape`, { method: 'POST', body: JSON.stringify(data) }),

  analyzeRepo: (id: string) =>
    fetchApi<any>(`/campaigns/${id}/analyze-repo`, { method: 'POST' }),
};

export const leadApi = {
  create: (data: LeadCreate) =>
    fetchApi<Lead>('/leads', { method: 'POST', body: JSON.stringify(data) }),

  list: (campaignId: string, status?: LeadStatus, skip = 0, limit = 100) => {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    if (status) params.set('status', status);
    return fetchApi<Lead[]>(`/campaigns/${campaignId}/leads?${params}`);
  },

  get: (id: string) =>
    fetchApi<Lead>(`/leads/${id}`),

  update: (id: string, data: Partial<Lead>) =>
    fetchApi<Lead>(`/leads/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  move: (id: string, newStatus: LeadStatus) =>
    fetchApi<Lead>(`/leads/${id}/move`, { method: 'POST', body: JSON.stringify({ new_status: newStatus }) }),

  triggerOutreach: (id: string, data: { ia_response: IAResponse; lead_context: LeadContext }) =>
    fetchApi<any>(`/leads/${id}/outreach`, { method: 'POST', body: JSON.stringify(data) }),
};

export const audioApi = {
  getQueueStatus: () =>
    fetchApi<{ queue_size: number; processing: number; completed: number; max_concurrent: number }>('/audio/queue/status'),

  getJobStatus: (jobId: string) =>
    fetchApi<any>(`/audio/jobs/${jobId}`),
};

// Types
export interface Campaign {
  id: string;
  name: string;
  github_repo_url: string;
  target_niche: string | null;
  ai_rules: AIRules | null;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface AIRules {
  min_setup_price: number;
  monthly_fee_range: [number, number];
  zero_commission_rule: boolean;
}

export interface Lead {
  id: string;
  campaign_id: string;
  business_name: string;
  phone_number: string;
  preview_url: string | null;
  calls_count: number;
  status: LeadStatus;
  created_at: string;
  updated_at: string;
  audio_path?: string | null;
  audio_generated_at?: string | null;
  last_contact_at?: string | null;
}

export type LeadStatus = 'NOVO' | 'APRESENTADO' | 'NEGOCIACAO' | 'FECHADO' | 'REJEITADO';

export interface LeadCreate {
  campaign_id: string;
  business_name: string;
  phone_number: string;
  preview_url?: string;
}

export interface ScrapingRequest {
  campaign_id: string;
  location: {
    latitude: number;
    longitude: number;
    radius_meters: number;
  };
  categories?: string[];
  max_results?: number;
}

export interface ScrapedBusiness {
  place_id: string;
  business_name: string;
  phone_number: string | null;
  address: string;
  latitude: number;
  longitude: number;
  category: string;
  rating: number | null;
  user_ratings_total: number | null;
  website: string | null;
  has_competitor_infrastructure: boolean;
}

export interface ScrapingResponse {
  campaign_id: string;
  total_found: number;
  businesses: ScrapedBusiness[];
  filtered_count: number;
  qualified_leads: ScrapedBusiness[];
}

export interface IAResponse {
  text_message: string;
  needs_audio: boolean;
  audio_text?: string;
  intent: 'presentation' | 'objection_handling' | 'closing' | 'followup';
}

export interface LeadContext {
  business_name: string;
  preview_url?: string;
  niche?: string;
  ai_rules?: Record<string, any>;
}