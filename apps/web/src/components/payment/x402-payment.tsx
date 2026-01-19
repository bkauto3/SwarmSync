'use client';

import { Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { parseUnits } from 'viem';
import { useAccount, useWaitForTransactionReceipt, useWriteContract } from 'wagmi';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

const USDC_ABI = [
  {
    inputs: [
      { name: 'to', type: 'address' },
      { name: 'amount', type: 'uint256' },
    ],
    name: 'transfer',
    outputs: [{ name: '', type: 'bool' }],
    stateMutability: 'nonpayable',
    type: 'function',
  },
] as const;

interface X402PaymentProps {
  recipient: string;
  amount: number;
  onSuccess: (txHash: string) => void;
  onError: (error: Error) => void;
}

type Status = 'idle' | 'signing' | 'pending' | 'success' | 'error';

export function X402Payment({ recipient, amount, onSuccess, onError }: X402PaymentProps) {
  const { isConnected } = useAccount();
  const { writeContractAsync } = useWriteContract();
  const [txHash, setTxHash] = useState<`0x${string}` | undefined>();
  const [status, setStatus] = useState<Status>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash: txHash,
  });

  useEffect(() => {
    if (isSuccess && txHash) {
      setStatus('success');
      onSuccess(txHash);
    }
  }, [isSuccess, txHash, onSuccess]);

  const handlePayment = async () => {
    if (!isConnected) {
      const error = new Error('Please connect your wallet to continue');
      setStatus('error');
      setErrorMessage(error.message);
      onError(error);
      return;
    }

    try {
      setStatus('signing');
      setErrorMessage(null);

      const amountInUnits = parseUnits(amount.toString(), 6);

      const hash = await writeContractAsync({
        address: USDC_ADDRESS,
        abi: USDC_ABI,
        functionName: 'transfer',
        args: [recipient as `0x${string}`, amountInUnits],
      });

      setTxHash(hash);
      setStatus('pending');
    } catch (error) {
      setStatus('error');
      setErrorMessage((error as Error).message);
      onError(error as Error);
    }
  };

  return (
    <div className="space-y-4">
      {status === 'idle' && (
        <Button onClick={handlePayment} className="w-full" size="lg">
          Pay {amount} USDC
        </Button>
      )}

      {status === 'signing' && (
        <Alert>
          <AlertDescription className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Please sign the transaction in your wallet...
          </AlertDescription>
        </Alert>
      )}

      {(status === 'pending' || isConfirming) && (
        <Alert>
          <AlertDescription className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Transaction pending... This usually takes a few seconds.
          </AlertDescription>
        </Alert>
      )}

      {status === 'success' && txHash && (
        <Alert className="border-emerald-200 bg-emerald-50 text-emerald-800">
          <AlertDescription>✅ Payment confirmed! Transaction: {txHash.slice(0, 10)}...</AlertDescription>
        </Alert>
      )}

      {status === 'error' && errorMessage && (
        <Alert variant="destructive">
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}

