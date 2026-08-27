'use server';

import { revalidatePath } from 'next/cache';
import { leadApi, Lead, LeadStatus, LeadCreate } from '@/lib/api';

export async function moveLeadAction(leadId: string, newStatus: LeadStatus): Promise<Lead> {
  const updatedLead = await leadApi.move(leadId, newStatus);
  
  revalidatePath('/dashboard/crm');
  revalidatePath(`/dashboard/campaigns/${updatedLead.campaign_id}`);
  
  return updatedLead;
}

export async function createLeadAction(data: LeadCreate): Promise<Lead> {
  const lead = await leadApi.create(data);
  
  revalidatePath('/dashboard/crm');
  revalidatePath(`/dashboard/campaigns/${data.campaign_id}`);
  
  return lead;
}

export async function updateLeadAction(leadId: string, data: Partial<Lead>): Promise<Lead> {
  const updatedLead = await leadApi.update(leadId, data);
  
  revalidatePath('/dashboard/crm');
  revalidatePath(`/dashboard/campaigns/${updatedLead.campaign_id}`);
  
  return updatedLead;
}

export async function triggerOutreachAction(
  leadId: string,
  iaResponse: { text_message: string; needs_audio: boolean; audio_text?: string; intent: string },
  leadContext: { business_name: string; preview_url?: string; niche?: string; ai_rules?: Record<string, any> }
) {
  const result = await leadApi.triggerOutreach(leadId, {
    ia_response: iaResponse,
    lead_context: leadContext,
  });
  
  revalidatePath('/dashboard/crm');
  revalidatePath(`/dashboard/campaigns/${leadContext.niche}`);
  
  return result;
}

export async function scrapeCampaignAction(
  campaignId: string,
  location: { latitude: number; longitude: number; radius_meters: number },
  categories: string[] = ['restaurant', 'store', 'health', 'beauty'],
  maxResults = 100
) {
  const result = await leadApi.scrape(campaignId, {
    campaign_id: campaignId,
    location,
    categories,
    max_results: maxResults,
  });
  
  revalidatePath('/dashboard/crm');
  revalidatePath(`/dashboard/campaigns/${campaignId}`);
  
  return result;
}

export async function analyzeRepoAction(campaignId: string) {
  const result = await leadApi.analyzeRepo(campaignId);
  
  revalidatePath(`/dashboard/campaigns/${campaignId}`);
  
  return result;
}