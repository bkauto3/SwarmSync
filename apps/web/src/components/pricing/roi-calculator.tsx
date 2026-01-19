'use client';

import { useState } from 'react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export function ROICalculator() {
  const [agents, setAgents] = useState(5);
  const [executions, setExecutions] = useState(1000);
  const [currentCost, setCurrentCost] = useState(5000);

  // Calculate recommended plan
  const getRecommendedPlan = () => {
    if (agents <= 3 && executions <= 100) return 'Free';
    if (agents <= 10 && executions <= 500) return 'Starter';
    if (agents <= 50 && executions <= 3000) return 'Pro';
    return 'Business';
  };

  const recommendedPlan = getRecommendedPlan();

  // Estimate time saved (hours per month)
  const estimatedTimeSaved = Math.round((executions * 0.5) / 60); // Assuming 0.5 min per execution saved

  // Estimate cost comparison
  const getPlanCost = (plan: string) => {
    switch (plan) {
      case 'Free':
        return 0;
      case 'Starter':
        return 29;
      case 'Pro':
        return 99;
      case 'Business':
        return 199;
      default:
        return 0;
    }
  };

  const swarmsyncCost = getPlanCost(recommendedPlan);
  const costSavings = currentCost - swarmsyncCost;
  const savingsPercent = currentCost > 0 ? Math.round((costSavings / currentCost) * 100) : 0;

  return (
    <Card className="border-white/10 bg-white/5">
      <CardHeader>
        <CardTitle className="text-2xl font-display text-white">ROI Calculator</CardTitle>
        <CardDescription className="text-slate-400">
          See how much time and money SwarmSync can save your team
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="agents" className="text-slate-300">
              Number of Agents
            </Label>
            <Input
              id="agents"
              type="number"
              min="1"
              value={agents}
              onChange={(e) => setAgents(parseInt(e.target.value) || 1)}
              className="bg-white/5 border-white/10 text-white"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="executions" className="text-slate-300">
              Executions per Month
            </Label>
            <Input
              id="executions"
              type="number"
              min="1"
              value={executions}
              onChange={(e) => setExecutions(parseInt(e.target.value) || 1)}
              className="bg-white/5 border-white/10 text-white"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="current-cost" className="text-slate-300">
              Current Monthly Cost ($)
            </Label>
            <Input
              id="current-cost"
              type="number"
              min="0"
              value={currentCost}
              onChange={(e) => setCurrentCost(parseInt(e.target.value) || 0)}
              className="bg-white/5 border-white/10 text-white"
            />
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3 pt-4 border-t border-white/10">
          <div className="space-y-1">
            <p className="text-xs text-slate-400 uppercase tracking-wide">Recommended Plan</p>
            <p className="text-2xl font-bold text-white">{recommendedPlan}</p>
            <p className="text-sm text-slate-400">
              ${getPlanCost(recommendedPlan)}/month
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-slate-400 uppercase tracking-wide">Time Saved</p>
            <p className="text-2xl font-bold text-emerald-400">{estimatedTimeSaved} hours</p>
            <p className="text-sm text-slate-400">per month</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-slate-400 uppercase tracking-wide">Cost Savings</p>
            <p className="text-2xl font-bold text-emerald-400">
              {costSavings >= 0 ? `$${costSavings.toLocaleString()}` : `-$${Math.abs(costSavings).toLocaleString()}`}
            </p>
            <p className="text-sm text-slate-400">
              {savingsPercent > 0 ? `${savingsPercent}%` : 'vs current cost'}
            </p>
          </div>
        </div>

        <div className="pt-4 border-t border-white/10">
          <Button asChild className="w-full bg-gradient-to-r from-[var(--accent-primary)] to-[#FFD87E] text-black font-semibold">
            <Link href="/register">Start Free Trial →</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
