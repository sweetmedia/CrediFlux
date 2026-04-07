import { apiClient } from './client';

export interface SearchResult {
  id: number | string;
  type: 'customer' | 'loan' | 'payment' | 'contract';
  title: string;
  subtitle: string;
  url: string;
}

export interface SearchResults {
  query: string;
  total_results: number;
  results: {
    customers: SearchResult[];
    loans: SearchResult[];
    payments: SearchResult[];
    contracts: SearchResult[];
  };
}

export const searchAPI = {
  /**
   * Perform a global search across all entities
   */
  async globalSearch(query: string): Promise<SearchResults> {
    return apiClient.get<SearchResults>(`/api/search/?q=${encodeURIComponent(query)}`);
  },
};
