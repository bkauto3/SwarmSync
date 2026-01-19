#!/bin/bash
# Script to set environment variables in Netlify
# Run this after doing: netlify login

cd "$(dirname "$0")/apps/web"

echo "Setting environment variables in Netlify..."

# Set private secrets (not exposed to browser)
netlify env:set GOOGLE_CLIENT_SECRET "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" --context production
netlify env:set GITHUB_CLIENT_SECRET "9970089f7d6588f60ed8c47b4251840137c6eb73" --context production
netlify env:set GOOGLE_CLIENT_ID "1056389438638-qjhk5vkfspi742rjg74661crsfeamkOr.apps.googleusercontent.com" --context production
netlify env:set GITHUB_CLIENT_ID "Ov23lijhlbg5GGBJZyqp" --context production
netlify env:set NEXTAUTH_SECRET "HNT0jWSyAGYkf3DAaUgpIUgfJdY7jwMW" --context production
netlify env:set NEXTAUTH_URL "https://swarmsync.ai" --context production

# Set public variables (exposed to browser via NEXT_PUBLIC_ prefix)
netlify env:set NEXT_PUBLIC_GOOGLE_CLIENT_ID "1056389438638-qjhk5vkfspi742rjg74661crsfeamkOr.apps.googleusercontent.com" --context production
netlify env:set NEXT_PUBLIC_GITHUB_CLIENT_ID "Ov23lijhlbg5GGBJZyqp" --context production
netlify env:set NEXT_PUBLIC_APP_URL "https://swarmsync.ai" --context production
netlify env:set NEXT_PUBLIC_API_URL "https://swarmsync-api.up.railway.app" --context production
netlify env:set NEXT_PUBLIC_DEFAULT_ORG_SLUG "swarmsync" --context production

echo "Environment variables set successfully!"
echo "Now triggering a redeploy..."

netlify deploy --prod --build

echo "Done! Check https://app.netlify.com for deployment status."
