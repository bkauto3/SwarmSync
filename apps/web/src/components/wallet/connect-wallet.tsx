'use client';

import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useAccount } from 'wagmi';

export function ConnectWallet() {
  const { address, isConnected } = useAccount();

  return (
    <div className="flex items-center gap-4">
      <ConnectButton />
      {isConnected && address && (
        <div className="text-sm text-muted-foreground">
          {address.slice(0, 6)}...{address.slice(-4)}
        </div>
      )}
    </div>
  );
}

