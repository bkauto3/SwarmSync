import { Navbar } from '@/components/layout/navbar';
import { Footer } from '@/components/layout/footer';
import ChromeNetworkBackground from '@/components/swarm/ChromeNetworkBackground';
import { TacticalButton } from '@/components/swarm/TacticalButton';
import { CheckCircle } from 'lucide-react';

export default function ThankYouPage() {
    return (
        <div className="flex min-h-screen flex-col bg-black text-slate-50 overflow-x-hidden">
            <Navbar />

            <main className="relative flex-1 flex items-center justify-center">
                <ChromeNetworkBackground />

                <div className="relative z-10 mx-auto max-w-2xl px-6 py-24 md:px-12 text-center">
                    <div className="mb-8 flex justify-center">
                        <div className="rounded-full bg-emerald-500/10 p-6">
                            <CheckCircle className="h-16 w-16 text-emerald-400" />
                        </div>
                    </div>

                    <h1 className="mb-4 text-4xl font-bold tracking-tight text-white md:text-5xl">
                        Inquiry <span className="text-[var(--accent-primary)]">Received</span>
                    </h1>

                    <p className="mb-12 text-lg text-slate-400">
                        Thank you for reaching out! Your inquiry has been sent directly to our team.
                    </p>

                    <div className="mb-12 rounded-2xl border border-white/10 bg-white/5 p-8 text-center backdrop-blur-sm">
                        <p className="text-slate-200 text-lg mb-4">
                            Our team will review your message and get back to you at the email address provided within 2-3 business days.
                        </p>
                        <p className="text-sm text-slate-500">
                            Need immediate assistance? Reach us at{' '}
                            <a href="mailto:rainking6693@gmail.com" className="text-[var(--accent-primary)] hover:underline whitespace-nowrap">
                                rainking6693@gmail.com
                            </a>
                        </p>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <TacticalButton href="/">
                            Return Home
                        </TacticalButton>
                        <TacticalButton variant="secondary" href="/frameworks">
                            Explore Frameworks
                        </TacticalButton>
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
}
