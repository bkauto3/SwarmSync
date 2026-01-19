import { Shield, Lock, CheckCircle2 } from 'lucide-react';

export function SecurityBadges() {
  return (
    <div className="flex flex-wrap items-center justify-center gap-6 py-8">
      <div className="flex items-center gap-2 text-slate-300">
        <Shield className="h-5 w-5 text-emerald-400" />
        <span className="text-sm font-medium">SOC 2 Type II</span>
      </div>
      <div className="flex items-center gap-2 text-slate-300">
        <Lock className="h-5 w-5 text-emerald-400" />
        <span className="text-sm font-medium">GDPR Compliant</span>
      </div>
      <div className="flex items-center gap-2 text-slate-300">
        <CheckCircle2 className="h-5 w-5 text-emerald-400" />
        <span className="text-sm font-medium">CCPA Compliant</span>
      </div>
      <div className="flex items-center gap-2 text-slate-300">
        <Shield className="h-5 w-5 text-emerald-400" />
        <span className="text-sm font-medium">Escrow Protected</span>
      </div>
    </div>
  );
}
