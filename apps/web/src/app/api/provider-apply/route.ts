import { NextResponse } from 'next/server';
import nodemailer from 'nodemailer';
import { randomUUID } from 'crypto';
import { mkdir, readFile, writeFile } from 'fs/promises';
import path from 'path';
import {
  ApplicationStatus,
  NotificationDetails,
  ProviderApplication,
  ProviderLifecycleEvent,
  trendify,
} from '@/lib/provider-application';
import { triggerProviderLifecycleEvent } from '@/lib/trigger/provider';

const STORAGE_DIR = path.join(process.cwd(), 'data');
const STORAGE_FILE = path.join(STORAGE_DIR, 'provider-applications.json');
const SMTP_HOST = process.env.SMTP_HOST;
const SMTP_PORT = process.env.SMTP_PORT ? Number(process.env.SMTP_PORT) : undefined;
const SMTP_USER = process.env.SMTP_USER;
const SMTP_PASS = process.env.SMTP_PASS;
const SMTP_FROM = process.env.SMTP_FROM ?? 'no-reply@swarmsync.ai';
const RECIPIENT = process.env.PROVIDER_APPLICATION_RECIPIENT ?? 'rainking6693@gmail.com';
const MONITORING_EMAIL = process.env.PROVIDER_NOTIFICATION_MONITOR ?? RECIPIENT;

type ProviderLifecycleEventWithoutSubmission = Exclude<ProviderLifecycleEvent, 'agentSubmitted'>;

const STATUS_BY_EVENT: Record<ProviderLifecycleEventWithoutSubmission, ApplicationStatus> = {
  agentApproved: 'approved',
  agentRejected: 'rejected',
  agentFirstHire: 'live',
  agentPayout: 'paid',
};

const createTransporter = () => {
  if (!SMTP_HOST || !SMTP_PORT || !SMTP_USER || !SMTP_PASS) {
    return null;
  }

  return nodemailer.createTransport({
    host: SMTP_HOST,
    port: SMTP_PORT,
    secure: SMTP_PORT === 465,
    auth: {
      user: SMTP_USER,
      pass: SMTP_PASS,
    },
  });
};

function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function sanitize(str: unknown, maxLength = 2000): string {
  if (typeof str !== 'string') return '';
  return str.trim().slice(0, maxLength);
}

async function ensureStorage() {
  try {
    await mkdir(STORAGE_DIR, { recursive: true });
    await writeFile(STORAGE_FILE, '[]', { flag: 'wx' });
  } catch (error) {
    // ignore file already exists
  }
}

async function readApplications(): Promise<ProviderApplication[]> {
  await ensureStorage();
  const content = await readFile(STORAGE_FILE, 'utf-8');
  return JSON.parse(content);
}

async function writeApplications(apps: ProviderApplication[]) {
  await ensureStorage();
  await writeFile(STORAGE_FILE, JSON.stringify(apps, null, 2));
}

async function sendProviderNotification(
  event: ProviderLifecycleEvent,
  application: ProviderApplication,
  details: NotificationDetails = {}
) {
  const transporter = createTransporter();
  const sentAt = new Date().toLocaleString();
  const subjectMap: Record<ProviderLifecycleEvent, string> = {
    agentSubmitted: `[SwarmSync] We received your agent submission`,
    agentApproved: `[SwarmSync] ${application.agentName} is live`,
    agentRejected: `[SwarmSync] Update needed for ${application.agentName}`,
    agentFirstHire: `[SwarmSync] ${application.agentName} just got hired`,
    agentPayout: `[SwarmSync] ${application.agentName} payout is pending`,
  };

  const subject = subjectMap[event];
  const baseMessage = [
    `Hi ${application.name},`,
    '',
    (() => {
      const jobNote = details.jobName ? ` (${details.jobName})` : '';
      switch (event) {
        case 'agentSubmitted':
          return `We received ${application.agentName} for review. Expect a response within 48 hours.`;
        case 'agentApproved':
          return `Congratulations! ${application.agentName} is now live in the SwarmSync marketplace.`;
        case 'agentRejected':
          return `Thanks for your submission. ${application.agentName} needs a few adjustments before it can go live.${
            details.feedback ? ` Feedback: ${details.feedback}` : ''
          }`;
        case 'agentFirstHire':
          return `Great news! ${application.agentName}${jobNote} just completed a job and earned its first hire.`;
        case 'agentPayout':
          return `You earned ${details.amount ?? '$0'} for ${application.agentName}. Funds will be available in 48 hours.`;
      }
    })(),
    '',
    `Agent: ${application.agentName}`,
    `Status: ${application.status}`,
    `Submitted: ${new Date(application.createdAt).toLocaleString()}`,
    `Updated: ${application.updatedAt ?? sentAt}`,
    '',
    'Thanks,',
    'SwarmSync Team',
  ];

  if (!transporter) {
    console.info('[Provider Notification] transporter not configured. Skipping email send.');
    console.info('[Provider Notification] intended subject:', subject);
    console.info('[Provider Notification] intended body:', baseMessage.join('\n'));
    return;
  }

  await transporter.sendMail({
    from: SMTP_FROM,
    to: application.email,
    bcc: MONITORING_EMAIL,
    subject,
    text: baseMessage.join('\n'),
  });
}

export async function GET() {
  try {
    const applications = await readApplications();
    return NextResponse.json({ applications });
  } catch (error) {
    console.error('[Provider Application] GET failed', error);
    return NextResponse.json({ applications: [] }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const payload = await request.json();
    const name = sanitize(payload.name);
    const email = sanitize(payload.email);
    const agentName = sanitize(payload.agentName);
    const agentDescription = sanitize(payload.agentDescription || payload.whatItDoes);
    const rawCategory = sanitize(payload.category);
    const rawPricingModel = sanitize(payload.pricingModel);
    const docsLink = sanitize(payload.docsLink);
    const apiEndpoint = sanitize(payload.apiEndpoint);
    const twitter = sanitize(payload.twitter);
    const notes = sanitize(payload.notes);
    const capabilities = Array.isArray(payload.capabilityTags)
      ? payload.capabilityTags.map((tag: string) => sanitize(tag))
      : [];
    const pricingTiers = Array.isArray(payload.pricingTiers)
      ? payload.pricingTiers.map((tier: any) => ({
          title: sanitize(tier.title),
          price: sanitize(tier.price),
          description: sanitize(tier.description),
        }))
      : [];
    const sampleOutputs = Array.isArray(payload.sampleOutputs)
      ? payload.sampleOutputs.map((filename: string) => sanitize(filename))
      : [];
    let endpointType = sanitize(payload.endpointType) || 'public';
    if (!['public', 'private', 'config'].includes(endpointType)) {
      endpointType = 'public';
    }
    const category = rawCategory || 'Other';
    const pricingModel = rawPricingModel || 'Custom';

    if (!name || name.length < 2) {
      return NextResponse.json({ error: 'Name is required and must be at least 2 characters' }, { status: 400 });
    }

    if (!email || !isValidEmail(email)) {
      return NextResponse.json({ error: 'A valid email address is required' }, { status: 400 });
    }

    if (!agentName || agentName.length < 2) {
      return NextResponse.json({ error: 'Agent name is required and must be at least 2 characters' }, { status: 400 });
    }

    if (!agentDescription || agentDescription.length < 10) {
      return NextResponse.json({ error: 'Agent description is required and must be at least 10 characters' }, { status: 400 });
    }

    const application: ProviderApplication = {
      id: randomUUID(),
      name,
      email,
      agentName,
      agentDescription,
      category,
      pricingModel,
      endpointType,
      docsLink,
      apiEndpoint,
      capabilityTags: capabilities.length ? capabilities : [],
      pricingTiers: pricingTiers.length
        ? pricingTiers
        : [{ title: trendify(pricingModel), price: '$0', description: 'TBD' }],
      sampleOutputs,
      status: 'submitted',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      twitter: twitter || undefined,
      notes: notes || undefined,
    };

    const applications = await readApplications();
    applications.push(application);
    await writeApplications(applications);

    await sendProviderNotification('agentSubmitted', application);
    await triggerProviderLifecycleEvent(application, 'agentSubmitted');

    const transporter = createTransporter();
    if (!transporter) {
      console.warn('Mail transport not configured - logging provider application payload.');
      console.info('[Provider Application]', JSON.stringify(application, null, 2));
      return NextResponse.json({ status: 'received', applicationId: application.id });
    }

    const subject = `Provider Application: ${application.agentName} (${application.name})`;
    const body = `
      Name: ${application.name}
      Email: ${application.email}
      Agent name: ${application.agentName}
      What it does: ${application.agentDescription}
      Category: ${application.category}
      Pricing Model: ${application.pricingModel}
      Pricing tiers: ${application.pricingTiers.map((tier) => `${tier.title} (${tier.price})`).join('; ') || '-'}
      Capabilities: ${application.capabilityTags.join(', ') || '-'}
      Endpoint type: ${application.endpointType}
      API/Docs: ${application.apiEndpoint || application.docsLink || '-'}
      Sample outputs: ${application.sampleOutputs.join(', ') || 'None'}
    `;

    await transporter.sendMail({
      from: SMTP_FROM,
      to: RECIPIENT,
      replyTo: application.email,
      subject,
      text: body,
    });

    return NextResponse.json({ status: 'sent', applicationId: application.id });
  } catch (error) {
    console.error('[Provider Application] failed', error);
    return NextResponse.json({ error: 'Unable to capture application' }, { status: 500 });
  }
}

export async function PATCH(request: Request) {
  try {
    const payload = await request.json();
    const applicationId = sanitize(payload.applicationId);
    const event = payload.event as ProviderLifecycleEvent;

    const allowedEvents: ProviderLifecycleEventWithoutSubmission[] = [
      'agentApproved',
      'agentRejected',
      'agentFirstHire',
      'agentPayout',
    ];

    if (!applicationId) {
      return NextResponse.json({ error: 'applicationId is required' }, { status: 400 });
    }

    if (!event || !allowedEvents.includes(event as ProviderLifecycleEventWithoutSubmission)) {
      return NextResponse.json({ error: 'Unsupported event' }, { status: 400 });
    }

    const applications = await readApplications();
    const application = applications.find((app) => app.id === applicationId);

    if (!application) {
      return NextResponse.json({ error: 'Application not found' }, { status: 404 });
    }

    const lifecycleEvent = event as ProviderLifecycleEventWithoutSubmission;
    application.status = STATUS_BY_EVENT[lifecycleEvent];
    application.updatedAt = new Date().toISOString();

    await writeApplications(applications);

    const eventDetails: NotificationDetails = {
      feedback: sanitize(payload.feedback),
      jobName: sanitize(payload.jobName),
      amount: sanitize(payload.amount),
    };

    await sendProviderNotification(event, application, eventDetails);
    await triggerProviderLifecycleEvent(application, event, eventDetails);

    return NextResponse.json({
      status: 'notified',
      event,
      applicationId: application.id,
    });
  } catch (error) {
    console.error('[Provider Application] PATCH failed', error);
    return NextResponse.json({ error: 'Unable to dispatch notification' }, { status: 500 });
  }
}
