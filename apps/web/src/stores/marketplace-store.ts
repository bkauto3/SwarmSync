'use client';

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface MarketplaceState {
  favorites: string[];
  compare: string[];
  toggleFavorite: (slug: string) => void;
  toggleCompare: (slug: string) => void;
}

export const useMarketplaceStore = create<MarketplaceState>()(
  persist(
    (set, get) => ({
      favorites: [],
      compare: [],
      toggleFavorite: (slug) => {
        const favorites = get().favorites.includes(slug)
          ? get().favorites.filter((item) => item !== slug)
          : [...get().favorites, slug];
        set({ favorites });
      },
      toggleCompare: (slug) => {
        const compare = get().compare.includes(slug)
          ? get().compare.filter((item) => item !== slug)
          : [...get().compare.slice(-2), slug].filter(
              (item, index, array) => array.indexOf(item) === index,
            );
        set({ compare });
      },
    }),
    {
      name: 'marketplace-preferences',
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
