'use client';

import { useState } from 'react';

import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';

interface AnnualToggleProps {
  value: 'monthly' | 'annual';
  onChange: (value: 'monthly' | 'annual') => void;
}

export function AnnualToggle({ value, onChange }: AnnualToggleProps) {
  return (
    <div className="flex items-center justify-center gap-4 py-6">
      <RadioGroup value={value} onValueChange={onChange} className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <RadioGroupItem value="monthly" id="monthly" />
          <Label htmlFor="monthly" className="cursor-pointer text-slate-300">
            Monthly
          </Label>
        </div>
        <div className="flex items-center gap-2">
          <RadioGroupItem value="annual" id="annual" />
          <Label htmlFor="annual" className="cursor-pointer text-slate-300">
            Annual
            <span className="ml-2 text-xs text-emerald-400 font-semibold">Save 20%</span>
          </Label>
        </div>
      </RadioGroup>
    </div>
  );
}
