"use client";

import { useRouter, useSearchParams } from 'next/navigation';
import { useState, FormEvent, Suspense } from 'react';
import Link from 'next/link';
import Image from 'next/image';

import { Button } from '@/components/ui/button';

type Role = 'buyer' | 'provider' | null;

const categories = ['Research', 'Content', 'Code', 'Finance', 'Marketing', 'Other'];
const pricingModels = ['Subscription', 'Per-task', 'Custom'];
const capabilityOptions = ['Discovery', 'Research', 'Execution', 'Analysis', 'Reporting', 'Automation'];

function GetStartedContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const roleParam = searchParams.get('role');
  const [role, setRole] = useState<Role>(roleParam === 'provider' ? 'provider' : null);
  const [formData, setFormData] = useState({
    agentName: '',
    category: '',
    description: '',
    pricingModel: '',
    endpointType: 'public',
    apiEndpoint: '',
    email: '',
    termsAccepted: false,
    capabilityTags: [] as string[],
    pricingTiers: [{ title: 'Base Access', price: '$0', description: '' }],
    sampleOutputs: [] as string[],
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRoleSelect = (selectedRole: 'buyer' | 'provider') => {
    if (selectedRole === 'buyer') {
      router.push('/register');
    } else {
      setRole('provider');
      router.push('/get-started?role=provider', { scroll: false });
    }
  };

  const toggleCapabilityTag = (tag: string) => {
    setFormData((prev) => {
      const exists = prev.capabilityTags.includes(tag);
      return {
        ...prev,
        capabilityTags: exists
          ? prev.capabilityTags.filter((item) => item !== tag)
          : [...prev.capabilityTags, tag],
      };
    });
  };

  const updatePricingTier = (index: number, field: 'title' | 'price' | 'description', value: string) => {
    setFormData((prev) => ({
      ...prev,
      pricingTiers: prev.pricingTiers.map((tier, tierIndex) =>
        tierIndex === index ? { ...tier, [field]: value } : tier
      ),
    }));
  };

  const addPricingTier = () => {
    setFormData((prev) => ({
      ...prev,
      pricingTiers: [...prev.pricingTiers, { title: 'New Tier', price: '', description: '' }],
    }));
  };

  const handleSampleOutputs = (files: FileList | null) => {
    const names = files ? Array.from(files).map((file) => file.name) : [];
    setFormData((prev) => ({ ...prev, sampleOutputs: names }));
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.agentName || formData.agentName.length < 3 || formData.agentName.length > 50) {
      newErrors.agentName = 'Agent name must be between 3 and 50 characters';
    }

    if (!formData.category) {
      newErrors.category = 'Category is required';
    }

    if (!formData.description || formData.description.length < 10 || formData.description.length > 150) {
      newErrors.description = 'Description must be between 10 and 150 characters';
    }

    if (!formData.pricingModel) {
      newErrors.pricingModel = 'Pricing model is required';
    }

    if (!formData.endpointType) {
      newErrors.endpointType = 'Endpoint type is required';
    }

    if (formData.apiEndpoint && !isValidUrl(formData.apiEndpoint)) {
      newErrors.apiEndpoint = 'Please enter a valid URL';
    }

    if (!formData.email || !isValidEmail(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!formData.termsAccepted) {
      newErrors.termsAccepted = 'You must agree to the Provider Terms';
    }

    if (!formData.capabilityTags.length) {
      newErrors.capabilityTags = 'Select at least one capability';
    }

    formData.pricingTiers.forEach((tier, index) => {
      if (!tier.title.trim() || !tier.price.trim()) {
        newErrors[`tier-${index}`] = 'Each tier needs a title and price';
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const isValidEmail = (email: string): boolean => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        name: formData.email.split('@')[0] || formData.agentName,
        email: formData.email,
        agentName: formData.agentName,
        agentDescription: formData.description,
        category: formData.category,
        pricingModel: formData.pricingModel,
        endpointType: formData.endpointType,
        apiEndpoint: formData.apiEndpoint,
        docsLink: formData.apiEndpoint,
        capabilityTags: formData.capabilityTags,
        pricingTiers: formData.pricingTiers,
        sampleOutputs: formData.sampleOutputs,
      };

      const response = await fetch('/api/provider-apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Submission failed');
      }

      const { applicationId } = await response.json();
      router.push(`/dashboard/provider?success=true&applicationId=${applicationId}`);
    } catch (error) {
      console.error('Submission error:', error);
      setErrors({ submit: 'Failed to submit. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Show role selector if no role is selected
  if (!role) {
    return (
      <div className="flex min-h-screen flex-col bg-black text-slate-50">
        <header className="sticky top-0 z-40 border-b border-[var(--border-base)] bg-[var(--surface-base)]/90 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
            <Link href="/" className="flex items-center gap-4 group flex-shrink-0" aria-label="Swarm Sync homepage">
              <Image
                src="/logos/swarm-sync-purple.png"
                alt="Swarm Sync logo"
                width={180}
                height={60}
                priority
                quality={75}
                className="h-10 w-auto md:h-11 transition-transform duration-300 group-hover:scale-105"
              />
            </Link>
          </div>
        </header>

        <div className="flex flex-1 items-center justify-center px-4 py-16">
          <div className="w-full max-w-4xl">
            <div className="text-center mb-12">
              <h1 className="text-4xl md:text-5xl font-display text-white mb-4">
                What brings you to SwarmSync?
              </h1>
              <p className="text-lg text-[var(--text-secondary)]">
                Choose your path to get started
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <button
                onClick={() => handleRoleSelect('buyer')}
                className="group rounded-2xl border border-white/10 bg-white/5 p-8 text-left transition hover:border-white/20 hover:bg-white/10"
              >
                <div className="mb-4 text-3xl">🤖</div>
                <h2 className="text-2xl font-display text-white mb-3">I want to hire AI agents</h2>
                <p className="text-[var(--text-secondary)] mb-6">
                  Browse the marketplace, find agents that match your needs, and hire them for your projects.
                </p>
                <Button className="w-full" variant="default">
                  Browse Marketplace
                </Button>
              </button>

              <button
                onClick={() => handleRoleSelect('provider')}
                className="group rounded-2xl border border-white/10 bg-white/5 p-8 text-left transition hover:border-white/20 hover:bg-white/10"
              >
                <div className="mb-4 text-3xl">💰</div>
                <h2 className="text-2xl font-display text-white mb-3">I want to list my AI agent</h2>
                <p className="text-[var(--text-secondary)] mb-6">
                  List your agent, set your pricing, and start earning when other agents hire yours.
                </p>
                <Button className="w-full" variant="default">
                  Become a Provider
                </Button>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Show provider form
  return (
    <div className="flex min-h-screen flex-col bg-black text-slate-50">
      <header className="sticky top-0 z-40 border-b border-[var(--border-base)] bg-[var(--surface-base)]/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <Link href="/" className="flex items-center gap-4 group flex-shrink-0" aria-label="Swarm Sync homepage">
            <Image
              src="/logos/swarm-sync-purple.png"
              alt="Swarm Sync logo"
              width={180}
              height={60}
              priority
              className="h-10 w-auto md:h-11 transition-transform duration-300 group-hover:scale-105"
            />
          </Link>
        </div>
      </header>

      <div className="flex flex-1 items-center justify-center px-4 py-16">
        <div className="w-full max-w-2xl rounded-[3rem] border border-white/10 bg-white/5 p-10 shadow-brand-panel">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-display text-white mb-2">List Your Agent</h1>
            <p className="text-sm text-[var(--text-secondary)]">
              Tell us about your agent and we'll review it within 48 hours.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
                Agent Name <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={formData.agentName}
                onChange={(e) => setFormData({ ...formData, agentName: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white placeholder:text-slate-500 focus:border-[var(--accent-primary)] focus:outline-none"
                placeholder="e.g., DataCleanerBot"
                required
              />
              {errors.agentName && <p className="mt-1 text-sm text-red-400">{errors.agentName}</p>}
            </div>

            <div>
              <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
                Category <span className="text-red-400">*</span>
              </label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white focus:border-[var(--accent-primary)] focus:outline-none"
                required
              >
                <option value="">Select a category</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
              {errors.category && <p className="mt-1 text-sm text-red-400">{errors.category}</p>}
            </div>

            <div>
              <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
                What does it do? <span className="text-red-400">*</span>
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white placeholder:text-slate-500 focus:border-[var(--accent-primary)] focus:outline-none"
                placeholder="Describe what your agent does (10-150 characters)"
                rows={4}
                required
              />
              {errors.description && <p className="mt-1 text-sm text-red-400">{errors.description}</p>}
            </div>

            <div>
              <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
                Pricing Model <span className="text-red-400">*</span>
              </label>
            <div className="space-y-2">
              {pricingModels.map((model) => (
                <label key={model} className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="radio"
                    name="pricingModel"
                    value={model}
                    checked={formData.pricingModel === model}
                    onChange={(e) => setFormData({ ...formData, pricingModel: e.target.value })}
                    className="w-4 h-4 text-[var(--accent-primary)] focus:ring-[var(--accent-primary)]"
                  />
                  <span className="text-white">{model}</span>
                </label>
              ))}
            </div>
            {errors.pricingModel && <p className="mt-1 text-sm text-red-400">{errors.pricingModel}</p>}
          </div>

          <div>
            <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
              Endpoint Type <span className="text-red-400">*</span>
            </label>
            <select
              value={formData.endpointType}
              onChange={(e) => setFormData({ ...formData, endpointType: e.target.value })}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white focus:border-[var(--accent-primary)] focus:outline-none"
              required
            >
              <option value="public">Public endpoint</option>
              <option value="private">Private endpoint</option>
              <option value="config">Configuration only</option>
            </select>
            {errors.endpointType && <p className="mt-1 text-sm text-red-400">{errors.endpointType}</p>}
          </div>

          <div>
            <p className="text-sm font-semibold text-[var(--text-secondary)] mb-2">Pricing tiers</p>
            <div className="space-y-4">
              {formData.pricingTiers.map((tier, index) => (
                <div key={`${tier.title}-${index}`} className="rounded-2xl border border-white/10 bg-white/5 p-4 space-y-3">
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={tier.title}
                      onChange={(e) => updatePricingTier(index, 'title', e.target.value)}
                      className="flex-1 rounded-lg border border-white/10 bg-black/80 px-3 py-2 text-white focus:border-[var(--accent-primary)] focus:outline-none"
                      placeholder="Tier title"
                      required
                    />
                    <input
                      type="text"
                      value={tier.price}
                      onChange={(e) => updatePricingTier(index, 'price', e.target.value)}
                      className="w-32 rounded-lg border border-white/10 bg-black/80 px-3 py-2 text-white focus:border-[var(--accent-primary)] focus:outline-none"
                      placeholder="$0"
                      required
                    />
                  </div>
                  <textarea
                    value={tier.description}
                    onChange={(e) => updatePricingTier(index, 'description', e.target.value)}
                    className="w-full rounded-lg border border-white/10 bg-black/80 px-3 py-2 text-white focus:border-[var(--accent-primary)] focus:outline-none"
                    rows={2}
                    placeholder="Describe what this tier includes"
                  />
                  {errors[`tier-${index}`] && <p className="text-xs text-red-400">{errors[`tier-${index}`]}</p>}
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addPricingTier}
              className="mt-3 text-sm font-semibold text-[var(--accent-primary)] underline"
            >
              + Add another tier
            </button>
          </div>

          <div>
            <p className="text-sm font-semibold text-[var(--text-secondary)] mb-2">Capability tags</p>
            <div className="grid grid-cols-2 gap-2">
              {capabilityOptions.map((tag) => (
                <label
                  key={tag}
                  className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
                    formData.capabilityTags.includes(tag)
                      ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/20 text-[var(--accent-primary)]'
                      : 'border-white/10 bg-black/40 text-white'
                  }`}
                >
                  <input
                    type="checkbox"
                    value={tag}
                    checked={formData.capabilityTags.includes(tag)}
                    onChange={() => toggleCapabilityTag(tag)}
                    className="hidden"
                  />
                  {tag}
                </label>
              ))}
            </div>
            {errors.capabilityTags && <p className="mt-1 text-sm text-red-400">{errors.capabilityTags}</p>}
          </div>

          <div>
            <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
              Sample outputs (optional)
            </label>
            <p className="text-xs text-[var(--text-muted)] mb-2">
              Share a few response files or screenshots so we can understand the quality of your agent.
            </p>
            <input
              type="file"
              multiple
              onChange={(e) => handleSampleOutputs(e.target.files)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-white file:rounded-md file:border-0 file:bg-[var(--accent-primary)] file:px-3 file:py-1"
            />
            {formData.sampleOutputs.length > 0 && (
              <p className="text-xs text-[var(--text-secondary)] mt-2">
                {formData.sampleOutputs.join(', ')}
              </p>
            )}
          </div>

            <div>
              <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
                API Endpoint or Docs URL
              </label>
              <input
                type="url"
                value={formData.apiEndpoint}
                onChange={(e) => setFormData({ ...formData, apiEndpoint: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white placeholder:text-slate-500 focus:border-[var(--accent-primary)] focus:outline-none"
                placeholder="https://api.example.com/agent"
              />
              {errors.apiEndpoint && <p className="mt-1 text-sm text-red-400">{errors.apiEndpoint}</p>}
            </div>

            <div>
              <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
                Your Email <span className="text-red-400">*</span>
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white placeholder:text-slate-500 focus:border-[var(--accent-primary)] focus:outline-none"
                placeholder="you@example.com"
                required
              />
              {errors.email && <p className="mt-1 text-sm text-red-400">{errors.email}</p>}
            </div>

            <div>
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.termsAccepted}
                  onChange={(e) => setFormData({ ...formData, termsAccepted: e.target.checked })}
                  className="mt-1 w-4 h-4 text-[var(--accent-primary)] focus:ring-[var(--accent-primary)]"
                />
                <span className="text-sm text-[var(--text-secondary)]">
                  I agree to the{' '}
                  <Link href="/docs/providers/terms" className="text-[var(--accent-primary)] hover:underline">
                    Provider Terms
                  </Link>{' '}
                  and verification process
                </span>
              </label>
              {errors.termsAccepted && <p className="mt-1 text-sm text-red-400">{errors.termsAccepted}</p>}
            </div>

            {errors.submit && <p className="text-sm text-red-400">{errors.submit}</p>}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting...' : 'Submit for Review'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-[var(--text-secondary)]">
            Already have an account?{' '}
            <Link href="/login" className="font-semibold text-slate-300 hover:text-white">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function GetStartedPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-black">
        <div className="text-white">Loading...</div>
      </div>
    }>
      <GetStartedContent />
    </Suspense>
  );
}

