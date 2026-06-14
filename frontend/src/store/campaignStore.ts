import { create } from "zustand";
import { getCampaigns, getCampaign } from "../services/campaigns";
import type { Campaign } from "../services/types";

export interface CampaignStore {
  /** All campaigns (current page). */
  campaigns: Campaign[];
  /** Currently selected campaign (full detail). */
  selectedCampaign: Campaign | null;
  /** Whether a fetch is in progress. */
  loading: boolean;
  /** Last error message, or null. */
  error: string | null;

  /** Fetch the campaign list (GET /api/campaigns/). */
  fetchCampaigns: (params?: {
    status?: string;
    search?: string;
    offset?: number;
    limit?: number;
  }) => Promise<void>;
  /** Select and fetch a single campaign by id. */
  selectCampaign: (id: number) => Promise<void>;
  /** Clear the current error. */
  clearError: () => void;
}

export const useCampaignStore = create<CampaignStore>()((set) => ({
  campaigns: [],
  selectedCampaign: null,
  loading: false,
  error: null,

  fetchCampaigns: async (params) => {
    set({ loading: true, error: null });
    try {
      const result = await getCampaigns(params);
      set({ campaigns: result.data, loading: false });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch campaigns";
      set({ error: message, loading: false });
    }
  },

  selectCampaign: async (id: number) => {
    set({ loading: true, error: null });
    try {
      const campaign = await getCampaign(id);
      set({ selectedCampaign: campaign, loading: false });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch campaign";
      set({ error: message, loading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
