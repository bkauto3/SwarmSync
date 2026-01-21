import { NextResponse } from 'next/server';
import nodemailer from 'nodemailer';
import { randomUUID } from 'crypto';

const SMTP_HOST = process.env.SMTP_HOST;
const SMTP_PORT = process.env.SMTP_PORT ? Number(process.env.SMTP_PORT) : undefined;
const SMTP_USER = process.env.SMTP_USER;
const SMTP_PASS = process.env.SMTP_PASS;
const SMTP_FROM = process.env.SMTP_FROM ?? 'no-reply@swarmsync.ai';
const RECIPIENT = 'Rainking6693@gmail.com';

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

export async function POST(request: Request) {
  try {
    const payload = await request.json();
    const email = sanitize(payload.email);
    const role = sanitize(payload.role);
    const building = sanitize(payload.building);
    const interests = Array.isArray(payload.interests)
      ? payload.interests.map((i: string) => sanitize(i))
      : [];
    const testGoals = Array.isArray(payload.testGoals)
      ? payload.testGoals.map((g: string) => sanitize(g))
      : [];
    const timeCommitment = sanitize(payload.timeCommitment);
    const feedbackConsent = sanitize(payload.feedbackConsent);

    // Validation
    if (!email || !isValidEmail(email)) {
      return NextResponse.json({ error: 'A valid email address is required' }, { status: 400 });
    }

    if (!role || role.length < 1) {
      return NextResponse.json({ error: 'Role is required' }, { status: 400 });
    }

    if (!building || building.length < 10) {
      return NextResponse.json({ error: 'Please tell us more about what you are building (at least 10 characters)' }, { status: 400 });
    }

    if (!interests || interests.length === 0) {
      return NextResponse.json({ error: 'Please select at least one description' }, { status: 400 });
    }

    if (!testGoals || testGoals.length === 0) {
      return NextResponse.json({ error: 'Please select what you want to test' }, { status: 400 });
    }

    if (!timeCommitment) {
      return NextResponse.json({ error: 'Please select a time commitment' }, { status: 400 });
    }

    if (!feedbackConsent) {
      return NextResponse.json({ error: 'Please indicate if you can provide feedback' }, { status: 400 });
    }

    const applicationId = randomUUID();
    const transporter = createTransporter();

    if (!transporter) {
      console.warn('Mail transport not configured - logging beta application payload.');
      console.info('[Beta Application]', JSON.stringify({
        applicationId,
        email,
        role,
        building,
        interests,
        testGoals,
        timeCommitment,
        feedbackConsent,
        submittedAt: new Date().toISOString(),
      }, null, 2));
      return NextResponse.json({
        status: 'received',
        applicationId,
        message: 'Application received successfully. You will be contacted shortly.'
      });
    }

    const subject = `Beta Application: ${role} - ${email}`;
    const body = `
New Beta Application Received
==============================

Applicant Details:
------------------
Email: ${email}
Role: ${role}
Time Commitment: ${timeCommitment}/week
Can Provide Feedback: ${feedbackConsent}

What They're Building:
----------------------
${building}

Interests:
----------
${interests.join(', ')}

What They Want to Test:
-----------------------
${testGoals.join(', ')}

Application ID: ${applicationId}
Submitted: ${new Date().toISOString()}
    `.trim();

    await transporter.sendMail({
      from: SMTP_FROM,
      to: RECIPIENT,
      replyTo: email,
      subject,
      text: body,
    });

    return NextResponse.json({
      status: 'sent',
      applicationId,
      message: 'Application submitted successfully! We will reach out to you shortly.'
    });
  } catch (error) {
    console.error('[Beta Application] failed', error);
    return NextResponse.json({ error: 'Unable to submit application. Please try again.' }, { status: 500 });
  }
}
