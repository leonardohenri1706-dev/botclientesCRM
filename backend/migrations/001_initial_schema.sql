-- BotClientes Database Schema
-- Standard PostgreSQL (Neon compatible)
-- Run in Neon SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (simplified for Neon)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Campaigns table
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    github_repo_url TEXT NOT NULL,
    target_niche VARCHAR(255),
    ai_rules JSONB DEFAULT '{
        "min_setup_price": 1200,
        "monthly_fee_range": [25, 50],
        "zero_commission_rule": true
    }'::jsonb,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for user campaigns
CREATE INDEX idx_campaigns_user_id ON campaigns(user_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);

-- Leads table
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    business_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL, -- E.164 format
    preview_url TEXT,
    calls_count INTEGER DEFAULT 0 CHECK (calls_count >= 0 AND calls_count <= 1),
    status VARCHAR(50) DEFAULT 'NOVO' CHECK (status IN ('NOVO', 'APRESENTADO', 'NEGOCIACAO', 'FECHADO', 'REJEITADO')),
    audio_path TEXT,
    audio_generated_at TIMESTAMPTZ,
    last_contact_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for leads
CREATE INDEX idx_leads_campaign_id ON leads(campaign_id);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_phone_number ON leads(phone_number);
CREATE INDEX idx_leads_calls_count ON leads(calls_count);

-- Scraping jobs table
CREATE TABLE scraping_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    location_lat DECIMAL(10, 8) NOT NULL,
    location_lng DECIMAL(11, 8) NOT NULL,
    location_radius INTEGER DEFAULT 1000,
    categories TEXT[] DEFAULT ARRAY['restaurant', 'store', 'health', 'beauty'],
    max_results INTEGER DEFAULT 100,
    total_found INTEGER DEFAULT 0,
    filtered_count INTEGER DEFAULT 0,
    qualified_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scraping_jobs_campaign_id ON scraping_jobs(campaign_id);
CREATE INDEX idx_scraping_jobs_status ON scraping_jobs(status);

-- Audio generation jobs table
CREATE TABLE audio_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    voice_id VARCHAR(100) DEFAULT 'default',
    output_format VARCHAR(10) DEFAULT 'ogg',
    file_path TEXT,
    duration_seconds DECIMAL(10, 2),
    file_size_bytes BIGINT,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    retries INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audio_jobs_lead_id ON audio_jobs(lead_id);
CREATE INDEX idx_audio_jobs_campaign_id ON audio_jobs(campaign_id);
CREATE INDEX idx_audio_jobs_status ON audio_jobs(status);

-- Outreach logs table
CREATE TABLE outreach_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    text_message TEXT,
    audio_sent BOOLEAN DEFAULT FALSE,
    audio_path TEXT,
    ia_intent VARCHAR(50),
    ia_response JSONB,
    status VARCHAR(50) DEFAULT 'sent' CHECK (status IN ('sent', 'delivered', 'read', 'failed', 'replied')),
    error_message TEXT,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ
);

CREATE INDEX idx_outreach_logs_lead_id ON outreach_logs(lead_id);
CREATE INDEX idx_outreach_logs_campaign_id ON outreach_logs(campaign_id);
CREATE INDEX idx_outreach_logs_status ON outreach_logs(status);
CREATE INDEX idx_outreach_logs_sent_at ON outreach_logs(sent_at DESC);

-- GitHub analysis cache table
CREATE TABLE github_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    repo_url TEXT NOT NULL,
    repo_owner VARCHAR(255),
    repo_name VARCHAR(255),
    analysis JSONB NOT NULL,
    suggested_ai_rules JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(campaign_id)
);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_github_analyses_updated_at BEFORE UPDATE ON github_analyses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Helper function for kanban stats
CREATE OR REPLACE FUNCTION get_campaign_kanban_stats(campaign_uuid UUID)
RETURNS TABLE (
    status VARCHAR(50),
    count BIGINT
) LANGUAGE sql SECURITY DEFINER AS $$
    SELECT 
        l.status,
        COUNT(*) as count
    FROM leads l
    WHERE l.campaign_id = campaign_uuid
    GROUP BY l.status
    ORDER BY 
        CASE l.status
            WHEN 'NOVO' THEN 1
            WHEN 'APRESENTADO' THEN 2
            WHEN 'NEGOCIACAO' THEN 3
            WHEN 'FECHADO' THEN 4
            WHEN 'REJEITADO' THEN 5
        END;
$$;

-- Insert default user for development
INSERT INTO users (id, email, name) 
VALUES ('00000000-0000-0000-0000-000000000000', 'dev@botclientes.local', 'Dev User')
ON CONFLICT (id) DO NOTHING;