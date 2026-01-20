'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { motion, AnimatePresence } from 'framer-motion';

const betaSchema = z.object({
    email: z.string().email('Invalid email address'),
    role: z.string().min(1, 'Please select a role'),
    building: z.string().min(10, 'Please tell us a bit more about what you are building'),
    interests: z.array(z.string()).min(1, 'Please select at least one description'),
    testGoals: z.array(z.string()).min(1, 'Please select what you want to test'),
    timeCommitment: z.string().min(1, 'Please select a time commitment'),
    feedbackConsent: z.string().min(1, 'Please indicate if you can provide feedback'),
});

type BetaFormValues = z.infer<typeof betaSchema>;

export function BetaForm() {
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const form = useForm<BetaFormValues>({
        resolver: zodResolver(betaSchema),
        defaultValues: {
            interests: [],
            testGoals: [],
        },
    });

    const onSubmit = async (data: BetaFormValues) => {
        setIsSubmitting(true);
        // Simulate API call
        await new Promise((resolve) => setTimeout(resolve, 1500));
        console.log('Beta Application Submitted:', data);
        setIsSubmitting(false);
        setIsSubmitted(true);
    };

    const interestsOptions = [
        { id: 'dev', label: 'AI Researcher / Engineer' },
        { id: 'founder', label: 'Startup Founder' },
        { id: 'enterprise', label: 'Enterprise Architect' },
        { id: 'hobbyist', label: 'AI Hobbyist' },
    ];

    const testGoalOptions = [
        { id: 'discovery', label: 'Discovery' },
        { id: 'negotiation', label: 'Negotiation' },
        { id: 'payments', label: 'Payments' },
        { id: 'orchestration', label: 'Orchestration' },
        { id: 'all', label: 'All' },
    ];

    if (isSubmitted) {
        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center space-y-6 py-12 px-8 rounded-[2rem] border border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl"
            >
                <div className="mx-auto w-16 h-16 rounded-full bg-[var(--accent-primary)]/20 flex items-center justify-center">
                    <svg className="w-8 h-8 text-[var(--accent-primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                </div>
                <h2 className="text-3xl font-display text-white">Application Received!</h2>
                <p className="text-slate-400 text-lg">You’re in the queue. We'll reach out to you shortly via email.</p>
                <Button onClick={() => setIsSubmitted(false)} variant="outline">Back to Start</Button>
            </motion.div>
        );
    }

    return (
        <div className="rounded-[2.5rem] border border-white/10 bg-white/5 p-8 md:p-12 backdrop-blur-sm shadow-2xl">
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                <div className="space-y-4">
                    <Label htmlFor="email" className="text-white text-base">Email Address</Label>
                    <Input
                        id="email"
                        placeholder="you@company.com"
                        {...form.register('email')}
                        className="bg-white/5 border-white/10 text-white placeholder:text-slate-600 focus:ring-[var(--accent-primary)] h-12"
                    />
                    {form.formState.errors.email && (
                        <p className="text-red-400 text-sm">{form.formState.errors.email.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label className="text-white text-base">Role</Label>
                    <Select onValueChange={(v) => form.setValue('role', v)}>
                        <SelectTrigger className="bg-white/5 border-white/10 text-white h-12">
                            <SelectValue placeholder="Select your role" />
                        </SelectTrigger>
                        <SelectContent className="bg-[#0f0f0f] border-white/10 text-white">
                            <SelectItem value="ai-dev">AI Dev</SelectItem>
                            <SelectItem value="agent-builder">Agent Builder</SelectItem>
                            <SelectItem value="enterprise">Enterprise</SelectItem>
                            <SelectItem value="other">Other</SelectItem>
                        </SelectContent>
                    </Select>
                    {form.formState.errors.role && (
                        <p className="text-red-400 text-sm">{form.formState.errors.role.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label htmlFor="building" className="text-white text-base">What are you building?</Label>
                    <Textarea
                        id="building"
                        placeholder="Describe your project or agent use case..."
                        {...form.register('building')}
                        className="bg-white/5 border-white/10 text-white placeholder:text-slate-600 focus:ring-[var(--accent-primary)] min-h-[100px]"
                    />
                    {form.formState.errors.building && (
                        <p className="text-red-400 text-sm">{form.formState.errors.building.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label className="text-white text-base">Which best describes you?</Label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {interestsOptions.map((option) => (
                            <div key={option.id} className="flex items-center space-x-3">
                                <Checkbox
                                    id={`interest-${option.id}`}
                                    onCheckedChange={(checked) => {
                                        const current = form.getValues('interests');
                                        const updated = checked
                                            ? [...current, option.id]
                                            : current.filter(i => i !== option.id);
                                        form.setValue('interests', updated);
                                    }}
                                />
                                <Label htmlFor={`interest-${option.id}`} className="text-slate-300 font-normal cursor-pointer">
                                    {option.label}
                                </Label>
                            </div>
                        ))}
                    </div>
                    {form.formState.errors.interests && (
                        <p className="text-red-400 text-sm">{form.formState.errors.interests.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label className="text-white text-base">What do you want to test?</Label>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                        {testGoalOptions.map((option) => (
                            <div key={option.id} className="flex items-center space-x-3">
                                <Checkbox
                                    id={`goal-${option.id}`}
                                    onCheckedChange={(checked) => {
                                        const current = form.getValues('testGoals');
                                        const updated = checked
                                            ? [...current, option.id]
                                            : current.filter(i => i !== option.id);
                                        form.setValue('testGoals', updated);
                                    }}
                                />
                                <Label htmlFor={`goal-${option.id}`} className="text-slate-300 font-normal cursor-pointer">
                                    {option.label}
                                </Label>
                            </div>
                        ))}
                    </div>
                    {form.formState.errors.testGoals && (
                        <p className="text-red-400 text-sm">{form.formState.errors.testGoals.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label className="text-white text-base">Time commitment per week</Label>
                    <RadioGroup onValueChange={(v) => form.setValue('timeCommitment', v)} className="flex flex-col gap-3">
                        <div className="flex items-center space-x-3">
                            <RadioGroupItem value="15min" id="t15" />
                            <Label htmlFor="t15" className="text-slate-300 font-normal cursor-pointer">15 min</Label>
                        </div>
                        <div className="flex items-center space-x-3">
                            <RadioGroupItem value="30min" id="t30" />
                            <Label htmlFor="t30" className="text-slate-300 font-normal cursor-pointer">30 min</Label>
                        </div>
                        <div className="flex items-center space-x-3">
                            <RadioGroupItem value="60min+" id="t60" />
                            <Label htmlFor="t60" className="text-slate-300 font-normal cursor-pointer">60 min+</Label>
                        </div>
                    </RadioGroup>
                    {form.formState.errors.timeCommitment && (
                        <p className="text-red-400 text-sm">{form.formState.errors.timeCommitment.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label className="text-white text-base font-semibold">Can you give feedback?</Label>
                    <RadioGroup
                        onValueChange={(v) => form.setValue('feedbackConsent', v)}
                        className="flex flex-row gap-8"
                    >
                        <div className="flex items-center space-x-3">
                            <RadioGroupItem value="yes" id="yes" />
                            <Label htmlFor="yes" className="text-slate-300 font-normal cursor-pointer">Yes</Label>
                        </div>
                        <div className="flex items-center space-x-3">
                            <RadioGroupItem value="no" id="no" />
                            <Label htmlFor="no" className="text-slate-300 font-normal cursor-pointer">No</Label>
                        </div>
                    </RadioGroup>
                    {form.formState.errors.feedbackConsent && (
                        <p className="text-red-400 text-sm">{form.formState.errors.feedbackConsent.message}</p>
                    )}
                </div>

                <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full h-14 text-lg font-bold uppercase tracking-widest bg-gradient-to-r from-[var(--accent-primary)] to-[#FFD87E] text-black hover:scale-[1.02] transition-transform duration-200"
                >
                    {isSubmitting ? 'Submitting...' : 'Apply for Beta'}
                </Button>
            </form>
        </div>
    );
}
