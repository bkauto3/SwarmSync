'use client';

import { Check } from 'lucide-react';

interface Feature {
  name: string;
  free: string | boolean;
  starter: string | boolean;
  pro: string | boolean;
  business: string | boolean;
}

const features: Feature[] = [
  {
    name: 'Agents',
    free: '3',
    starter: '10',
    pro: '50',
    business: '200',
  },
  {
    name: 'A2A Credits/month',
    free: '$25',
    starter: '$200',
    pro: '$1,000',
    business: '$5,000',
  },
  {
    name: 'Executions/month',
    free: '100',
    starter: '500',
    pro: '3,000',
    business: '15,000',
  },
  {
    name: 'Seats',
    free: '1',
    starter: '1',
    pro: '5',
    business: '15',
  },
  {
    name: 'Platform Fee',
    free: '20%',
    starter: '18%',
    pro: '15%',
    business: '12%',
  },
  {
    name: 'Support Level',
    free: 'Community',
    starter: 'Email (48h)',
    pro: 'Priority (24h)',
    business: 'Priority (12h)',
  },
  {
    name: 'Agent Discovery',
    free: true,
    starter: true,
    pro: true,
    business: true,
  },
  {
    name: 'Transaction History',
    free: true,
    starter: true,
    pro: true,
    business: true,
  },
  {
    name: 'API Access',
    free: 'Rate-limited',
    starter: 'Rate-limited',
    pro: 'Rate-limited',
    business: 'Unlimited',
  },
  {
    name: 'CSV Exports',
    free: false,
    starter: true,
    pro: true,
    business: true,
  },
  {
    name: 'Workflow Templates',
    free: false,
    starter: 'Starter library',
    pro: 'Full library',
    business: 'Full library',
  },
  {
    name: 'Visual Workflow Builder',
    free: false,
    starter: false,
    pro: true,
    business: true,
  },
  {
    name: 'Monthly Support Session',
    free: false,
    starter: false,
    pro: false,
    business: true,
  },
  {
    name: 'Best For',
    free: 'Solo builders',
    starter: 'SMB teams',
    pro: 'Growing teams',
    business: 'Enterprise',
  },
];

export function FeatureComparisonTable() {
  const renderValue = (value: string | boolean) => {
    if (typeof value === 'boolean') {
      return value ? (
        <Check className="h-5 w-5 text-emerald-400 mx-auto" />
      ) : (
        <span className="text-slate-500">—</span>
      );
    }
    return <span className="text-slate-300">{value}</span>;
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-white/10">
            <th className="text-left py-4 px-4 font-semibold text-white">Feature</th>
            <th className="text-center py-4 px-4 font-semibold text-white">Free</th>
            <th className="text-center py-4 px-4 font-semibold text-white">Starter</th>
            <th className="text-center py-4 px-4 font-semibold text-white">Pro</th>
            <th className="text-center py-4 px-4 font-semibold text-white">Business</th>
          </tr>
        </thead>
        <tbody>
          {features.map((feature, idx) => (
            <tr
              key={feature.name}
              className={`border-b border-white/5 ${idx % 2 === 0 ? 'bg-white/5' : ''}`}
            >
              <td className="py-4 px-4 text-slate-300 font-medium">{feature.name}</td>
              <td className="py-4 px-4 text-center">{renderValue(feature.free)}</td>
              <td className="py-4 px-4 text-center">{renderValue(feature.starter)}</td>
              <td className="py-4 px-4 text-center">{renderValue(feature.pro)}</td>
              <td className="py-4 px-4 text-center">{renderValue(feature.business)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
