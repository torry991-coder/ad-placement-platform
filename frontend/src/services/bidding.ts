import { api } from "./api";
import type {
  AuctionRequest,
  AuctionResponse,
  BatchAuctionResponse,
} from "./types";

export interface BiddingStrategy {
  id: string;
  name: string;
  description: string;
  requires_target_cpa: boolean;
  requires_target_roas: boolean;
}

/**
 * Run a single real-time auction simulation.
 */
export async function runAuction(
  params: AuctionRequest
): Promise<AuctionResponse> {
  const { data } = await api.post<AuctionResponse>(
    "/api/bidding/auction",
    params
  );
  return data;
}

/**
 * Run multiple auction simulations in a single batch (max 100).
 */
export async function runBatchAuctions(
  auctions: AuctionRequest[]
): Promise<BatchAuctionResponse> {
  const { data } = await api.post<BatchAuctionResponse>(
    "/api/bidding/batch",
    { auctions }
  );
  return data;
}

/**
 * List all available bid strategies with descriptions.
 */
export async function getStrategies(): Promise<BiddingStrategy[]> {
  const { data } = await api.get<{ strategies: BiddingStrategy[] }>(
    "/api/bidding/strategies"
  );
  return data.strategies;
}
