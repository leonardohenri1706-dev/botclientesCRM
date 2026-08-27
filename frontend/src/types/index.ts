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

export interface AudioJob {
  job_id: string;
  lead_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: {
    file_path: string;
    duration_seconds: number;
    file_size_bytes: number;
    format: string;
  };
  error?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  retries: number;
}

export interface OutreachLog {
  id: string;
  lead_id: string;
  campaign_id: string;
  phone_number: string;
  text_message: string | null;
  audio_sent: boolean;
  audio_path: string | null;
  ia_intent: string | null;
  ia_response: Record<string, any> | null;
  status: 'sent' | 'delivered' | 'read' | 'failed' | 'replied';
  error_message: string | null;
  sent_at: string;
  delivered_at?: string;
  read_at?: string;
  replied_at?: string;
}

export interface GitHubAnalysis {
  repository: string;
  files_analyzed: string[];
  icp_profile: {
    company_size: string | null;
    industry: string[];
    pain_points: string[];
    tech_maturity: string;
    budget_range: string | null;
  };
  objection_args: string[];
  pricing_signals: {
    setup_fee: number | null;
    monthly_range: [number, number] | null;
    commission_model: string | null;
    pricing_tiers: any[];
  };
  tech_stack: string[];
  target_market: string;
}