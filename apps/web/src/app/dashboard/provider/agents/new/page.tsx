"use client";

import { useRouter } from 'next/navigation';
import { useState, FormEvent } from 'react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';

const categories = ['Research', 'Content', 'Code', 'Finance', 'Marketing', 'Other'];
const pricingModels = ['Subscription', 'Per-task', 'Custom'];
const capabilityOptions = ['Discovery', 'Research', 'Execution', 'Analysis', 'Reporting', 'Automation'];

export default function NewAgentPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: '',
    category: '',
    shortDescription: '',
    fullDescription: '',
    pricingModel: '',
    apiEndpoint: '',
    authMethod: '',
    responseTimeSLA: '',
    capabilityTags: [] as string[],
    pricingTiers: [
      { title: 'Base Access', price: '$0', description: 'Intro tier' },
    ],
    sampleOutputs: [] as string[],
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

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

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    console.log('New agent payload', formData);
    // In production, this would call an API
    setTimeout(() => {
      router.push('/dashboard/provider?success=true');
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-black text-slate-50">
      <div className="mx-auto max-w-3xl px-6 py-12">
        <div className="mb-8">
          <Link href="/dashboard/provider/agents" className="text-[var(--text-secondary)] hover:text-white mb-4 inline-block">
            ← Back to Agents
          </Link>
          <h1 className="text-3xl font-display text-white mb-2">Create New Agent</h1>
          <p className="text-[var(--text-secondary)]">Fill out all the details about your agent</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
              Agent Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white focus:border-[var(--accent-primary)] focus:outline-none"
              required
            />
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
          </div>

          <div>
            <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
              Short Description <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={formData.shortDescription}
              onChange={(e) => setFormData({ ...formData, shortDescription: e.target.value })}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white focus:border-[var(--accent-primary)] focus:outline-none"
              placeholder="Brief one-line description"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
              Full Description <span className="text-red-400">*</span>
            </label>
            <textarea
              value={formData.fullDescription}
              onChange={(e) => setFormData({ ...formData, fullDescription: e.target.value })}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white focus:border-[var(--accent-primary)] focus:outline-none"
              rows={6}
              maxLength={500}
              placeholder="Detailed description of what your agent does (up to 500 characters)"
              required
            />
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              {formData.fullDescription.length}/500 characters
            </p>
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
          </div>

          <div>
            <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
              API/Webhook Endpoint
            </label>
            <input
              type="url"
              value={formData.apiEndpoint}
              onChange={(e) => setFormData({ ...formData, apiEndpoint: e.target.value })}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white focus:border-[var(--accent-primary)] focus:outline-none"
              placeholder="https://api.example.com/agent"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
              Authentication Method
            </label>
            <select
              value={formData.authMethod}
              onChange={(e) => setFormData({ ...formData, authMethod: e.target.value })}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white focus:border-[var(--accent-primary)] focus:outline-none"
            >
              <option value="">Select method</option>
              <option value="api-key">API Key</option>
              <option value="bearer-token">Bearer Token</option>
              <option value="oauth">OAuth</option>
              <option value="none">None (Public)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
              Response Time SLA (seconds)
            </label>
            <input
              type="number"
              value={formData.responseTimeSLA}
              onChange={(e) => setFormData({ ...formData, responseTimeSLA: e.target.value })}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-white focus:border-[var(--accent-primary)] focus:outline-none"
              placeholder="e.g., 30"
            />
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
          </div>

          <div>
            <p className="text-sm font-semibold text-[var(--text-secondary)] mb-2">Pricing tiers</p>
            <div className="space-y-4">
              {formData.pricingTiers.map((tier, index) => (
                <div key={`tier-${index}`} className="rounded-2xl border border-white/10 bg-white/5 p-4 space-y-3">
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <input
                      type="text"
                      value={tier.title}
                      onChange={(e) => updatePricingTier(index, 'title', e.target.value)}
                      className="flex-1 rounded-lg border border-white/10 bg-black/80 px-3 py-2 text-white focus:border-[var(--accent-primary)] focus:outline-none"
                      placeholder="Tier title"
                    />
                    <input
                      type="text"
                      value={tier.price}
                      onChange={(e) => updatePricingTier(index, 'price', e.target.value)}
                      className="w-32 rounded-lg border border-white/10 bg-black/80 px-3 py-2 text-white focus:border-[var(--accent-primary)] focus:outline-none"
                      placeholder="$0"
                    />
                  </div>
                  <textarea
                    value={tier.description}
                    onChange={(e) => updatePricingTier(index, 'description', e.target.value)}
                    className="w-full rounded-lg border border-white/10 bg-black/80 px-3 py-2 text-white focus:border-[var(--accent-primary)] focus:outline-none"
                    rows={2}
                    placeholder="Describe what this tier includes"
                  />
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
            <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
              Sample outputs (optional)
            </label>
            <p className="text-xs text-[var(--text-muted)] mb-2">
              Upload prompt/response pairs or result screenshots to give reviewers a sense of how your agent performs.
            </p>
            <input
              type="file"
              multiple
              onChange={(e) => handleSampleOutputs(e.target.files)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-white file:rounded-md file:border-0 file:bg-[var(--accent-primary)] file:px-3 file:py-1"
            />
            {formData.sampleOutputs.length > 0 && (
              <p className="text-xs text-[var(--text-muted)] mt-2">{formData.sampleOutputs.join(', ')}</p>
            )}
          </div>

          <div className="flex gap-4">
            <Button type="submit" disabled={isSubmitting} className="flex-1">
              {isSubmitting ? 'Submitting...' : 'Submit for Review'}
            </Button>
            <Link href="/dashboard/provider/agents">
              <Button type="button" variant="outline">Cancel</Button>
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}

