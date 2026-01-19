'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        // Log the error to an error reporting service
        console.error('Unhandled runtime error:', error);
    }, [error]);

    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4 px-4 text-center">
            <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">
                    Something went wrong!
                </h2>
                <p className="mx-auto max-w-[600px] text-gray-400 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                    We apologize for the inconvenience. An unexpected error occurred.
                </p>
            </div>
            <div className="flex flex-col gap-2 min-[400px]:flex-row justify-center">
                <Button
                    onClick={() => reset()}
                    size="lg"
                    variant="outline"
                    className="bg-white/5 border-white/10 hover:bg-white/10"
                >
                    Try again
                </Button>
                <Button
                    onClick={() => (window.location.href = '/')}
                    size="lg"
                    variant="default"
                >
                    Return Home
                </Button>
            </div>
            {error.digest && (
                <p className="text-xs text-gray-500 font-mono mt-8">
                    Error ID: {error.digest}
                </p>
            )}
        </div>
    );
}
