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
    proofLink: z.string().url('Please enter a valid URL'),
    workflow: z.string().min(10, 'Please describe a workflow (at least 10 characters)'),
    toolsUsed: z.array(z.string()).min(1, 'Please select at least one tool'),
    persona: z.string().min(1, 'Please select the option that best describes you'),
    testGoals: z.array(z.string()).min(1, 'Please select what you want to test'),
    useCases: z.array(z.string()).min(1, 'Please select where you would use specialist agents'),
    useCasesOther: z.string().optional(),
    timeCommitment: z.string().min(1, 'Please select a time commitment'),
    missionCommitment: z.string().min(1, 'Please indicate if you will complete the test mission'),
    feedbackModes: z.array(z.string()).min(1, 'Please select how you can provide feedback'),
}).superRefine((data, ctx) => {
    if (data.useCases.length > 2) {
        ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: 'Please select up to 2 options',
            path: ['useCases'],
        });
    }
    if (data.useCases.includes('other') && !data.useCasesOther?.trim()) {
        ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: 'Please specify the other use case',
            path: ['useCasesOther'],
        });
    }
});

type BetaFormValues = z.infer<typeof betaSchema>;

export function BetaForm() {
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const form = useForm<BetaFormValues>({
        resolver: zodResolver(betaSchema),
        defaultValues: {
            testGoals: [],
            toolsUsed: [],
            useCases: [],
            feedbackModes: [],
        },
    });
    const selectedUseCases = form.watch('useCases');

    const onSubmit = async (data: BetaFormValues) => {
        setIsSubmitting(true);
        try {
            const response = await fetch('/api/beta/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Failed to submit application');
            }

            console.log('Beta Application Submitted:', result);
            setIsSubmitted(true);
        } catch (error) {
            console.error('Failed to submit beta application:', error);
            alert('Failed to submit application. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    const toolsUsedOptions = [
        { id: 'chatgpt-claude', label: 'ChatGPT / Claude' },
        { id: 'zapier-make', label: 'Zapier / Make' },
        { id: 'langchain', label: 'LangChain' },
        { id: 'autogen-ag2', label: 'AutoGen / AG2' },
        { id: 'llamaindex', label: 'LlamaIndex' },
        { id: 'n8n', label: 'n8n' },
        { id: 'python', label: 'Python scripts' },
        { id: 'node', label: 'Node/TypeScript' },
        { id: 'none', label: 'None yet' },
    ];

    const testGoalOptions = [
        { id: 'discovery', label: 'Discovery' },
        { id: 'negotiation', label: 'Negotiation' },
        { id: 'payments', label: 'Payments' },
        { id: 'orchestration', label: 'Orchestration' },
        { id: 'all', label: 'All' },
    ];

    const useCaseOptions = [
        { id: 'agency', label: 'Automation agency work' },
        { id: 'data', label: 'Data / ETL / analytics' },
        { id: 'marketing', label: 'Marketing ops' },
        { id: 'finance', label: 'Finance ops' },
        { id: 'support', label: 'Customer support ops' },
        { id: 'sales', label: 'Sales ops' },
        { id: 'security', label: 'Security / compliance' },
        { id: 'dev-tooling', label: 'Dev tooling' },
        { id: 'other', label: 'Other' },
    ];

    const feedbackModeOptions = [
        { id: 'screen-walkthrough', label: 'I can record a 2-5 min screen walkthrough' },
        { id: 'bug-reports', label: 'I can write clear bug reports with steps to reproduce' },
        { id: 'feedback-call', label: 'I can join a 15-min feedback call' },
        { id: 'invite-testers', label: 'I can invite 2-5 qualified testers' },
        { id: 'none', label: 'None of the above' },
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
                <p className="text-slate-400 text-lg">You're in the queue. We'll reach out to you shortly via email.</p>
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
                            <SelectItem value="ai-ml-engineer">AI / ML Engineer</SelectItem>
                            <SelectItem value="software-engineer-ai">Software Engineer (AI apps)</SelectItem>
                            <SelectItem value="agent-builder">Agent Builder</SelectItem>
                            <SelectItem value="founder-product">Founder / Product</SelectItem>
                            <SelectItem value="mlops-platform">MLOps / Platform / DevOps</SelectItem>
                            <SelectItem value="enterprise-architect">Enterprise Architect / IT</SelectItem>
                            <SelectItem value="consultant-agency">Consultant / Agency</SelectItem>
                            <SelectItem value="researcher">Researcher</SelectItem>
                            <SelectItem value="other">Other</SelectItem>
                        </SelectContent>
                    </Select>
                    {form.formState.errors.role && (
                        <p className="text-red-400 text-sm">{form.formState.errors.role.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label htmlFor="proofLink" className="text-white text-base">
                        Share ONE link that proves your work (pick one): (LinkedIn profile, GitHub, Portfolio / website, company page, Product page, etc)
                    </Label>
                    <Input
                        id="proofLink"
                        type="url"
                        placeholder="https://..."
                        {...form.register('proofLink')}
                        className="bg-white/5 border-white/10 text-white placeholder:text-slate-600 focus:ring-[var(--accent-primary)] h-12"
                    />
                    {form.formState.errors.proofLink && (
                        <p className="text-red-400 text-sm">{form.formState.errors.proofLink.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label htmlFor="workflow" className="text-white text-base">
                        Describe a real workflow you want to run with SwarmSync (be specific).
                    </Label>
                    <Textarea
                        id="workflow"
                        placeholder="Example: My agent finds a specialist, negotiates a fixed fee, executes the task, and confirms payment."
                        {...form.register('workflow')}
                        className="bg-white/5 border-white/10 text-white placeholder:text-slate-600 focus:ring-[var(--accent-primary)] min-h-[120px]"
                    />
                    <p className="text-slate-400 text-sm">
                        Example: "My agent finds a specialist, negotiates a fixed fee, executes the task, and confirms payment."
                    </p>
                    {form.formState.errors.workflow && (
                        <p className="text-red-400 text-sm">{form.formState.errors.workflow.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label className="text-white text-base">Which tools have you used?</Label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {toolsUsedOptions.map((option) => (
                            <div key={option.id} className="flex items-center space-x-3">
                                <Checkbox
                                    id={`tool-${option.id}`}
                                    onCheckedChange={(checked) => {
                                        const current = form.getValues('toolsUsed');
                                        const updated = checked
                                            ? [...current, option.id]
                                            : current.filter(i => i !== option.id);
                                        form.setValue('toolsUsed', updated);
                                    }}
                                />
                                <Label htmlFor={`tool-${option.id}`} className="text-slate-300 font-normal cursor-pointer">
                                    {option.label}
                                </Label>
                            </div>
                        ))}
                    </div>
                    {form.formState.errors.toolsUsed && (
                        <p className="text-red-400 text-sm">{form.formState.errors.toolsUsed.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label className="text-white text-base">Which best describes you?</Label>
                    <Select onValueChange={(v) => form.setValue('persona', v)}>
                        <SelectTrigger className="bg-white/5 border-white/10 text-white h-12">
                            <SelectValue placeholder="Select one" />
                        </SelectTrigger>
                        <SelectContent className="bg-[#0f0f0f] border-white/10 text-white">
                            <SelectItem value="builder">Builder (I build agents/tools and want to connect SwarmSync to my workflows)</SelectItem>
                            <SelectItem value="operator">Operator (I run AI/automation in a team and care about reliability/governance)</SelectItem>
                            <SelectItem value="agent-seller">Agent Seller (I want to list an agent/service and get paid for jobs)</SelectItem>
                            <SelectItem value="explorer">Explorer (I'm evaluating / learning)</SelectItem>
                        </SelectContent>
                    </Select>
                    {form.formState.errors.persona && (
                        <p className="text-red-400 text-sm">{form.formState.errors.persona.message}</p>
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
                    <Label className="text-white text-base">Where would you use specialist agents most?</Label>
                    <p className="text-slate-400 text-sm">Choose up to 2.</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {useCaseOptions.map((option) => (
                            <div key={option.id} className="flex items-center space-x-3">
                                <Checkbox
                                    id={`usecase-${option.id}`}
                                    onCheckedChange={(checked) => {
                                        const current = form.getValues('useCases');
                                        if (checked && current.length >= 2) {
                                            return;
                                        }
                                        const updated = checked
                                            ? [...current, option.id]
                                            : current.filter(i => i !== option.id);
                                        form.setValue('useCases', updated);
                                    }}
                                />
                                <Label htmlFor={`usecase-${option.id}`} className="text-slate-300 font-normal cursor-pointer">
                                    {option.label}
                                </Label>
                            </div>
                        ))}
                    </div>
                    {selectedUseCases?.includes('other') && (
                        <Input
                            id="useCasesOther"
                            placeholder="Other: tell us where you would use specialists"
                            {...form.register('useCasesOther')}
                            className="bg-white/5 border-white/10 text-white placeholder:text-slate-600 focus:ring-[var(--accent-primary)] h-12"
                        />
                    )}
                    {form.formState.errors.useCases && (
                        <p className="text-red-400 text-sm">{form.formState.errors.useCases.message}</p>
                    )}
                    {form.formState.errors.useCasesOther && (
                        <p className="text-red-400 text-sm">{form.formState.errors.useCasesOther.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label className="text-white text-base">Time you can commit in the next 7 days</Label>
                    <Select onValueChange={(v) => form.setValue('timeCommitment', v)}>
                        <SelectTrigger className="bg-white/5 border-white/10 text-white h-12">
                            <SelectValue placeholder="Select a time commitment" />
                        </SelectTrigger>
                        <SelectContent className="bg-[#0f0f0f] border-white/10 text-white">
                            <SelectItem value="15-min">15 min</SelectItem>
                            <SelectItem value="30-min">30 min</SelectItem>
                            <SelectItem value="60-min">60 min</SelectItem>
                            <SelectItem value="2-plus-hours">2+ hours</SelectItem>
                        </SelectContent>
                    </Select>
                    {form.formState.errors.timeCommitment && (
                        <p className="text-red-400 text-sm">{form.formState.errors.timeCommitment.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label className="text-white text-base">Will you complete the test mission + feedback form?</Label>
                    <Select onValueChange={(v) => form.setValue('missionCommitment', v)}>
                        <SelectTrigger className="bg-white/5 border-white/10 text-white h-12">
                            <SelectValue placeholder="Select one" />
                        </SelectTrigger>
                        <SelectContent className="bg-[#0f0f0f] border-white/10 text-white">
                            <SelectItem value="yes">Yes</SelectItem>
                            <SelectItem value="no">No</SelectItem>
                        </SelectContent>
                    </Select>
                    {form.formState.errors.missionCommitment && (
                        <p className="text-red-400 text-sm">{form.formState.errors.missionCommitment.message}</p>
                    )}
                </div>

                <div className="space-y-4">
                    <Label className="text-white text-base">How can you provide feedback?</Label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {feedbackModeOptions.map((option) => (
                            <div key={option.id} className="flex items-center space-x-3">
                                <Checkbox
                                    id={`feedback-${option.id}`}
                                    onCheckedChange={(checked) => {
                                        const current = form.getValues('feedbackModes');
                                        const updated = checked
                                            ? [...current, option.id]
                                            : current.filter(i => i !== option.id);
                                        form.setValue('feedbackModes', updated);
                                    }}
                                />
                                <Label htmlFor={`feedback-${option.id}`} className="text-slate-300 font-normal cursor-pointer">
                                    {option.label}
                                </Label>
                            </div>
                        ))}
                    </div>
                    {form.formState.errors.feedbackModes && (
                        <p className="text-red-400 text-sm">{form.formState.errors.feedbackModes.message}</p>
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
