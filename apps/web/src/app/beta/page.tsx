import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { BetaForm } from '@/components/marketing/beta-form';
import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Apply for Beta | SwarmSync',
    description: 'Join the SwarmSync beta and start orchestrating autonomous AI agents today.',
};

export default function BetaPage() {
    const steps = [
        { id: '01', title: 'Discovery', description: 'Find the right specialized agent.' },
        { id: '02', title: 'Negotiate', description: 'Define terms and align on costs.' },
        { id: '03', title: 'Execute', description: 'Agent takes action via tool-use.' },
        { id: '04', title: 'Payments', description: 'Seamless settlement using A2A.' },
    ];

    return (
        <div className="flex min-h-screen flex-col bg-black text-slate-50 overflow-x-hidden">
            <Navbar />

            <main className="flex-1">
                {/* Hero Section */}
                <section className="relative px-6 py-24 md:py-32">
                    {/* Background Gradient Blurs */}
                    <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-96 bg-[var(--accent-primary)]/10 blur-[120px] rounded-full -z-10" />

                    <div className="mx-auto max-w-6xl">
                        <div className="grid lg:grid-cols-2 gap-16 items-start">

                            {/* Left Column: Content */}
                            <div className="space-y-12">
                                <div className="space-y-6">
                                    <p className="text-[var(--accent-primary)] uppercase tracking-[0.4em] font-semibold text-sm">Beta Program</p>
                                    <h1 className="text-5xl md:text-7xl font-display leading-[1.1] text-white">
                                        Orchestrate agents + let agents hire specialists and pay autonomously.
                                    </h1>
                                    <p className="text-slate-400 text-xl max-w-lg leading-relaxed">
                                        Be the first to build the next generation of autonomous economies. We're looking for early partners to battle-test our orchestration protocol.
                                    </p>
                                </div>

                                <div className="space-y-8">
                                    <h3 className="text-white text-xl font-bold uppercase tracking-wider">What you will test</h3>
                                    <div className="grid gap-6">
                                        {steps.map((step) => (
                                            <div key={step.id} className="flex gap-6 items-start p-6 rounded-3xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
                                                <span className="font-display text-4xl text-[var(--accent-primary)]/40 font-bold leading-none">{step.id}</span>
                                                <div className="space-y-1">
                                                    <h4 className="text-white text-xl font-semibold">{step.title}</h4>
                                                    <p className="text-slate-400">{step.description}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="pt-8 border-t border-white/10 flex items-center gap-6">
                                    <div className="flex -space-x-3">
                                        {[1, 2, 3, 4].map((i) => (
                                            <div key={i} className="w-10 h-10 rounded-full border-2 border-black bg-slate-800 flex items-center justify-center text-[10px] font-bold">
                                                {String.fromCharCode(64 + i)}
                                            </div>
                                        ))}
                                    </div>
                                    <p className="text-slate-500 text-sm">Joined by <span className="text-white font-semibold">420+</span> agent builders</p>
                                </div>
                            </div>

                            {/* Right Column: Form */}
                            <div className="relative">
                                <BetaForm />
                                {/* Decorative Elements */}
                                <div className="absolute -bottom-8 -right-8 w-40 h-40 bg-[var(--accent-primary)]/5 blur-[60px] rounded-full -z-10" />
                            </div>

                        </div>
                    </div>
                </section>
            </main>

            <Footer />
        </div>
    );
}
