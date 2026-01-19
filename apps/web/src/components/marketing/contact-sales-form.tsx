'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

export function ContactSalesForm() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    company: '',
    message: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus('idle');

    try {
      // Send form data to our API route
      const response = await fetch('/api/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          framework: `ENTERPRISE_SALES - ${formData.company || 'No Company'}`,
          message: `Phone: ${formData.phone}\n\n${formData.message}`,
        }),
      });

      if (response.ok) {
        setSubmitStatus('success');
        // Redirect to thank you page
        router.push('/contact/thank-you');
      } else {
        setSubmitStatus('error');
      }
    } catch (error) {
      console.error('Failed to submit form:', error);
      setSubmitStatus('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="name" className="text-white">Name *</Label>
          <Input
            id="name"
            type="text"
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Your full name"
            className="bg-white/5 border-white/10 text-white placeholder:text-[var(--text-muted)]"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email" className="text-white">Email *</Label>
          <Input
            id="email"
            type="email"
            required
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            placeholder="your@email.com"
            className="bg-white/5 border-white/10 text-white placeholder:text-[var(--text-muted)]"
          />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="phone" className="text-white">Phone</Label>
          <Input
            id="phone"
            type="tel"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            placeholder="+1 (555) 123-4567"
            className="bg-white/5 border-white/10 text-white placeholder:text-[var(--text-muted)]"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="company" className="text-white">Company</Label>
          <Input
            id="company"
            type="text"
            value={formData.company}
            onChange={(e) => setFormData({ ...formData, company: e.target.value })}
            placeholder="Your company name"
            className="bg-white/5 border-white/10 text-white placeholder:text-[var(--text-muted)]"
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="message" className="text-white">Message *</Label>
        <Textarea
          id="message"
          required
          value={formData.message}
          onChange={(e) => setFormData({ ...formData, message: e.target.value })}
          placeholder="Tell us about your requirements..."
          rows={4}
          className="bg-white/5 border-white/10 text-white placeholder:text-[var(--text-muted)] min-h-[100px]"
        />
      </div>
      {submitStatus === 'error' && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-400">
          Failed to submit. Please try again or email us directly at rainking6693@gmail.com
        </div>
      )}
      <Button
        type="submit"
        className="w-full bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/90 text-white font-semibold py-6"
        disabled={isSubmitting}
      >
        {isSubmitting ? 'Submitting...' : 'Submit Inquiry'}
      </Button>
    </form>
  );
}
