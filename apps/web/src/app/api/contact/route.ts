import { NextResponse } from 'next/server';

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const { name, email, framework, message } = body;

        // Validate required fields
        if (!name || !email || !framework) {
            return NextResponse.json(
                { error: 'Missing required fields' },
                { status: 400 }
            );
        }

        // Create email content
        const emailContent = `
New Framework Integration Request

Name: ${name}
Email: ${email}
Framework: ${framework}

Message:
${message || 'No additional details provided.'}

---
Submitted at: ${new Date().toISOString()}
    `.trim();

        // Send email using the backend API
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

        const response = await fetch(`${apiUrl}/notifications/email`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                to: 'rainking6693@gmail.com',
                subject: `Framework Integration Request: ${framework}`,
                text: emailContent,
                html: `
          <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #8b5cf6;">New Framework Integration Request</h2>
            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
              <p><strong>Name:</strong> ${name}</p>
              <p><strong>Email:</strong> <a href="mailto:${email}">${email}</a></p>
              <p><strong>Framework:</strong> ${framework}</p>
            </div>
            ${message ? `
              <div style="margin: 20px 0;">
                <h3>Additional Details:</h3>
                <p style="white-space: pre-wrap;">${message}</p>
              </div>
            ` : ''}
            <p style="color: #6b7280; font-size: 12px; margin-top: 30px;">
              Submitted at: ${new Date().toLocaleString()}
            </p>
          </div>
        `,
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to send email');
        }

        return NextResponse.json({ success: true });
    } catch (error) {
        console.error('Contact form error:', error);
        return NextResponse.json(
            { error: 'Failed to send message' },
            { status: 500 }
        );
    }
}
