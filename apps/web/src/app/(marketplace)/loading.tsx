import { Skeleton } from '@/components/ui/skeleton';

export default function Loading() {
    return (
        <div className="flex min-h-screen flex-col bg-black">
            <div className="flex-1 px-4 py-12">
                <div className="mx-auto max-w-6xl space-y-10">
                    <div className="space-y-6 rounded-[3rem] border border-white/10 bg-white/5 p-8">
                        <Skeleton className="h-4 w-24 bg-white/10" />
                        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                            <div className="space-y-2">
                                <Skeleton className="h-10 w-64 bg-white/10" />
                                <Skeleton className="h-6 w-96 bg-white/10" />
                            </div>
                            <div className="flex gap-3">
                                <Skeleton className="h-10 w-32 bg-white/10" />
                                <Skeleton className="h-10 w-32 bg-white/10" />
                            </div>
                        </div>
                        <Skeleton className="h-12 w-full bg-white/10 rounded-xl" />
                    </div>

                    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                        {[...Array(6)].map((_, i) => (
                            <div key={i} className="rounded-3xl border border-white/5 bg-white/5 p-6 space-y-4">
                                <Skeleton className="h-48 w-full bg-white/10 rounded-2xl" />
                                <Skeleton className="h-6 w-3/4 bg-white/10" />
                                <Skeleton className="h-4 w-full bg-white/10" />
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
