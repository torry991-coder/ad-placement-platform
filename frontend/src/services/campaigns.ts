import { api } from "./api";
import type {
  Campaign,
  CampaignCreate,
  CampaignUpdate,
  DashboardKPI,
  PaginatedResponse,
} from "./types";

export interface CampaignListParams {
  status?: string;
  search?: string;
  offset?: number;
  limit?: number;
}

/**
 * Fetch a paginated list of campaigns with optional filtering.
 */
export async function getCampaigns(
  params: CampaignListParams = {}
): Promise<PaginatedResponse<Campaign>> {
  const { data } = await api.get<PaginatedResponse<Campaign>>(
    "/api/campaigns/",
    { params }
  );
  return data;
}

/**
 * Fetch a single campaign by ID.
 */
export async function getCampaign(id: number): Promise<Campaign> {
  const { data } = await api.get<Campaign>(`/api/campaigns/${id}`);
  return data;
}

/**
 * Create a new campaign.
 */
export async function createCampaign(
  payload: CampaignCreate
): Promise<Campaign> {
  const { data } = await api.post<Campaign>("/api/campaigns/", payload);
  return data;
}

/**
 * Update an existing campaign (partial update).
 */
export async function updateCampaign(
  id: number,
  payload: CampaignUpdate
): Promise<Campaign> {
  const { data } = await api.patch<Campaign>(
    `/api/campaigns/${id}`,
    payload
  );
  return data;
}

/**
 * Delete a campaign.
 */
export async function deleteCampaign(id: number): Promise<void> {
  await api.delete(`/api/campaigns/${id}`);
}

/**
 * Fetch aggregate dashboard KPIs.
 */
export async function getDashboard(): Promise<DashboardKPI> {
  const { data } = await api.get<DashboardKPI>("/api/campaigns/dashboard");
  return data;
}
