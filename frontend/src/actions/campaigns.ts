'use server';

import { revalidatePath } from 'next/cache';
import { campaignApi, Campaign, AIRules } from '@/lib/api';

export async function createCampaignAction(data: {
  name: string;
  github_repo_url: string;
  target_niche?: string;
  ai_rules?: AIRules;
}): Promise<Campaign> {
  const campaign = await campaignApi.create(data);
  revalidatePath('/dashboard/campaigns');
  return campaign;
}

export async function updateCampaignAction(
  id: string,
  data: Partial<Campaign>
): Promise<Campaign> {
  const campaign = await campaignApi.update(id, data);
  revalidatePath('/dashboard/campaigns');
  revalidatePath(`/dashboard/campaigns/${id}`);
  return campaign;
}

export async function deleteCampaignAction(id: string): Promise<void> {
  await campaignApi.delete(id);
  revalidatePath('/dashboard/campaigns');
}

export async function getCampaignAction(id: string): Promise<Campaign> {
  return campaignApi.get(id);
}

export async function listCampaignsAction(skip = 0, limit = 50): Promise<Campaign[]> {
  return campaignApi.list(skip, limit);
}

export async function scrapeCampaignAction(
  campaignId: string,
  location: { latitude: number; longitude: number; radius_meters: number },
  categories: string[] = ['restaurant', 'store', 'health', 'beauty'],
  maxResults = 100
) {
  const result = await campaignApi.scrape(campaignId, {
    campaign_id: campaignId,
    location,
    categories,
    max_results: maxResults,
  });
  
  revalidatePath('/dashboard/campaigns');
  revalidatePath(`/dashboard/campaigns/${campaignId}`);
  
  return result;
}

export async function analyzeRepoAction(campaignId: string) {
  const result = await campaignApi.analyzeRepo(campaignId);
  
  revalidatePath(`/dashboard/campaigns/${campaignId}`);
  
  return result;
}