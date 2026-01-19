'use client';

import '@rainbow-me/rainbowkit/styles.css';

import { RainbowKitProvider, getDefaultConfig } from '@rainbow-me/rainbowkit';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionProvider } from 'next-auth/react';
import { ReactNode, useMemo, useState } from 'react';
import { WagmiProvider, http } from 'wagmi';
import { base } from 'wagmi/chains';

const walletConnectProjectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID;
const baseRpcUrl = process.env.NEXT_PUBLIC_BASE_RPC_URL || 'https://mainnet.base.org';

// Validate project ID - must be a non-empty string and not the demo placeholder
const isValidProjectId = walletConnectProjectId && 
  walletConnectProjectId.trim() !== '' && 
  walletConnectProjectId !== 'demo-agent-market';

// Create wagmi config as a singleton to prevent double initialization
let wagmiConfigSingleton: ReturnType<typeof getDefaultConfig> | null = null;

function getWagmiConfig() {
  // Window-level guard to prevent double initialization across remounts
  if (typeof window !== 'undefined') {
    if (window.__wagmiConfigInitialized) {
      // Return existing singleton if already initialized
      return wagmiConfigSingleton!;
    }
    window.__wagmiConfigInitialized = true;
  }

  if (!wagmiConfigSingleton && isValidProjectId) {
    wagmiConfigSingleton = getDefaultConfig({
      appName: 'AgentMarket',
      projectId: walletConnectProjectId!,
      chains: [base],
      transports: {
        [base.id]: http(baseRpcUrl),
      },
    });
  }
  return wagmiConfigSingleton;
}

// Extend Window interface for TypeScript
declare global {
  interface Window {
    __wagmiConfigInitialized?: boolean;
  }
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  // Use useMemo to ensure config is only created once per component instance
  const wagmiConfig = useMemo(() => getWagmiConfig(), []);

  // If no valid project ID, render children without WalletConnect providers
  if (!isValidProjectId || !wagmiConfig) {
    if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
      console.warn(
        'WalletConnect is disabled: NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID is not set or is invalid. ' +
        'Get a project ID from https://cloud.walletconnect.com'
      );
    }
    return (
      <SessionProvider>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </SessionProvider>
    );
  }

  return (
    <SessionProvider>
      <WagmiProvider config={wagmiConfig}>
        <QueryClientProvider client={queryClient}>
          <RainbowKitProvider>{children}</RainbowKitProvider>
        </QueryClientProvider>
      </WagmiProvider>
    </SessionProvider>
  );
}
