\# IMMEDIATE NEXT STEP: BUILD THE PUBLIC MARKETPLACE FRONTEND

\*\*Date\*\*: November 13, 2025

\*\*Priority\*\*: CRITICAL

\*\*Complexity\*\*: Medium

---

\## 🎯 THE MISSION

Build a beautiful, intuitive \*\*Next.js 14 marketplace frontend\*\* that connects to our existing world-class backend APIs. Think: "Airbnb meets Hugging Face" - elegant discovery, seamless transactions, trust signals everywhere.

---

\## 📋 INSTRUCTIONS FOR YOUR AI CODER

\### \*\*PHASE 1: FOUNDATION (Week 1) - START HERE\*\*

\#### \*\*Step 1: Create the Next.js Project\*\*

```bash

\# In your monorepo root

cd apps/

npx create-next-app@latest web --typescript --tailwind --app --src-dir --import-alias "@/\*"



cd web

```

\*\*Configuration choices:\*\*

\- ✅ TypeScript

\- ✅ Tailwind CSS

\- ✅ App Router (not Pages Router)

\- ✅ src/ directory

\- ✅ Import alias: `@/\*`

\- ❌ No Turbopack (not stable yet)

\#### \*\*Step 2: Install Core Dependencies\*\*

```bash

npm install @tanstack/react-query zustand

npm install react-hook-form zod @hookform/resolvers

npm install lucide-react date-fns

npm install ky # For API calls (better than fetch)



\# Install shadcn/ui

npx shadcn-ui@latest init



\# Add essential components

npx shadcn-ui@latest add button card input label textarea select dropdown-menu avatar badge separator skeleton

```

\#### \*\*Step 3: Set Up Project Structure\*\*

Create this folder structure in `apps/web/src/`:

```

src/

├── app/

│   ├── (auth)/

│   │   ├── login/

│   │   │   └── page.tsx

│   │   └── register/

│   │       └── page.tsx

│   ├── (marketplace)/

│   │   ├── agents/

│   │   │   ├── page.tsx          # Agent listing

│   │   │   └── \[id]/

│   │   │       └── page.tsx      # Agent detail

│   │   ├── dashboard/

│   │   │   └── page.tsx          # User dashboard

│   │   └── layout.tsx            # Marketplace layout

│   ├── layout.tsx                # Root layout

│   └── page.tsx                  # Landing page

├── components/

│   ├── ui/                       # shadcn components (auto-generated)

│   ├── layout/

│   │   ├── navbar.tsx

│   │   ├── footer.tsx

│   │   └── sidebar.tsx

│   ├── agents/

│   │   ├── agent-card.tsx

│   │   ├── agent-grid.tsx

│   │   ├── agent-filters.tsx

│   │   └── agent-search.tsx

│   └── auth/

│       ├── login-form.tsx

│       └── register-form.tsx

├── lib/

│   ├── api.ts                    # API client setup

│   ├── auth.ts                   # Auth helpers

│   ├── utils.ts                  # Utility functions

│   └── constants.ts              # App constants

├── hooks/

│   ├── use-auth.ts

│   ├── use-agents.ts

│   └── use-wallet.ts

├── stores/

│   └── auth-store.ts             # Zustand store for auth

└── types/

&nbsp;   ├── agent.ts

&nbsp;   ├── user.ts

&nbsp;   └── transaction.ts

```

\#### \*\*Step 4: Create API Client\*\*

Create `src/lib/api.ts`:

```typescript

import ky from 'ky';



const API\_BASE\_URL = process.env.NEXT\_PUBLIC\_API\_URL || 'http://localhost:4000';



export const api = ky.create({

&nbsp; prefixUrl: API\_BASE\_URL,

&nbsp; hooks: {

&nbsp;   beforeRequest: \[

&nbsp;     (request) => {

&nbsp;       // Add auth token from localStorage

&nbsp;       const token = localStorage.getItem('auth\_token');

&nbsp;       if (token) {

&nbsp;         request.headers.set('Authorization', `Bearer ${token}`);

&nbsp;       }

&nbsp;     },

&nbsp;   ],

&nbsp;   afterResponse: \[

&nbsp;     async (request, options, response) => {

&nbsp;       // Handle 401 (unauthorized) - redirect to login

&nbsp;       if (response.status === 401) {

&nbsp;         localStorage.removeItem('auth\_token');

&nbsp;         window.location.href = '/login';

&nbsp;       }

&nbsp;     },

&nbsp;   ],

&nbsp; },

});



// Type-safe API methods

export const agentsApi = {

&nbsp; list: (params?: { search?: string; category?: string; limit?: number }) =>

&nbsp;   api.get('agents', { searchParams: params }).json(),

&nbsp;

&nbsp; getById: (id: string) =>

&nbsp;   api.get(`agents/${id}`).json(),

&nbsp;

&nbsp; create: (data: any) =>

&nbsp;   api.post('agents', { json: data }).json(),

};



export const authApi = {

&nbsp; login: (email: string, password: string) =>

&nbsp;   api.post('auth/login', { json: { email, password } }).json(),

&nbsp;

&nbsp; register: (data: { email: string; password: string; name: string }) =>

&nbsp;   api.post('auth/register', { json: data }).json(),

&nbsp;

&nbsp; me: () =>

&nbsp;   api.get('auth/me').json(),

};



export const walletsApi = {

&nbsp; getMy: () =>

&nbsp;   api.get('wallets/my').json(),

&nbsp;

&nbsp; addFunds: (amount: number) =>

&nbsp;   api.post('wallets/my/fund', { json: { amount } }).json(),

};

```

\#### \*\*Step 5: Set Up React Query\*\*

Create `src/app/providers.tsx`:

```typescript

'use client';



import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { ReactNode, useState } from 'react';



export function Providers({ children }: { children: ReactNode }) {

&nbsp; const \[queryClient] = useState(

&nbsp;   () =>

&nbsp;     new QueryClient({

&nbsp;       defaultOptions: {

&nbsp;         queries: {

&nbsp;           staleTime: 60 \* 1000, // 1 minute

&nbsp;           refetchOnWindowFocus: false,

&nbsp;         },

&nbsp;       },

&nbsp;     })

&nbsp; );



&nbsp; return (

&nbsp;   <QueryClientProvider client={queryClient}>

&nbsp;     {children}

&nbsp;   </QueryClientProvider>

&nbsp; );

}

```

Update `src/app/layout.tsx`:

```typescript

import { Providers } from './providers';

import './globals.css';



export default function RootLayout({

&nbsp; children,

}: {

&nbsp; children: React.ReactNode;

}) {

&nbsp; return (

&nbsp;   <html lang="en">

&nbsp;     <body>

&nbsp;       <Providers>{children}</Providers>

&nbsp;     </body>

&nbsp;   </html>

&nbsp; );

}

```

\#### \*\*Step 6: Build Authentication\*\*

Create `src/hooks/use-auth.ts`:

```typescript

import { useMutation, useQuery } from '@tanstack/react-query';

import { authApi } from '@/lib/api';

import { useRouter } from 'next/navigation';



export function useAuth() {

&nbsp; const router = useRouter();



&nbsp; const { data: user, isLoading } = useQuery({

&nbsp;   queryKey: \['auth', 'me'],

&nbsp;   queryFn: authApi.me,

&nbsp;   retry: false,

&nbsp; });



&nbsp; const loginMutation = useMutation({

&nbsp;   mutationFn: ({ email, password }: { email: string; password: string }) =>

&nbsp;     authApi.login(email, password),

&nbsp;   onSuccess: (data: any) => {

&nbsp;     localStorage.setItem('auth\_token', data.token);

&nbsp;     router.push('/dashboard');

&nbsp;   },

&nbsp; });



&nbsp; const registerMutation = useMutation({

&nbsp;   mutationFn: (data: { email: string; password: string; name: string }) =>

&nbsp;     authApi.register(data),

&nbsp;   onSuccess: (data: any) => {

&nbsp;     localStorage.setItem('auth\_token', data.token);

&nbsp;     router.push('/dashboard');

&nbsp;   },

&nbsp; });



&nbsp; const logout = () => {

&nbsp;   localStorage.removeItem('auth\_token');

&nbsp;   router.push('/');

&nbsp; };



&nbsp; return {

&nbsp;   user,

&nbsp;   isLoading,

&nbsp;   isAuthenticated: !!user,

&nbsp;   login: loginMutation.mutate,

&nbsp;   register: registerMutation.mutate,

&nbsp;   logout,

&nbsp; };

}

```

Create `src/components/auth/login-form.tsx`:

```typescript

'use client';



import { useForm } from 'react-hook-form';

import { zodResolver } from '@hookform/resolvers/zod';

import \* as z from 'zod';

import { Button } from '@/components/ui/button';

import { Input } from '@/components/ui/input';

import { Label } from '@/components/ui/label';

import { useAuth } from '@/hooks/use-auth';



const schema = z.object({

&nbsp; email: z.string().email('Invalid email address'),

&nbsp; password: z.string().min(6, 'Password must be at least 6 characters'),

});



type FormData = z.infer<typeof schema>;



export function LoginForm() {

&nbsp; const { login } = useAuth();

&nbsp; const {

&nbsp;   register,

&nbsp;   handleSubmit,

&nbsp;   formState: { errors },

&nbsp; } = useForm<FormData>({

&nbsp;   resolver: zodResolver(schema),

&nbsp; });



&nbsp; const onSubmit = (data: FormData) => {

&nbsp;   login(data);

&nbsp; };



&nbsp; return (

&nbsp;   <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

&nbsp;     <div>

&nbsp;       <Label htmlFor="email">Email</Label>

&nbsp;       <Input

&nbsp;         id="email"

&nbsp;         type="email"

&nbsp;         placeholder="you@example.com"

&nbsp;         {...register('email')}

&nbsp;       />

&nbsp;       {errors.email \&\& (

&nbsp;         <p className="text-sm text-red-600 mt-1">{errors.email.message}</p>

&nbsp;       )}

&nbsp;     </div>



&nbsp;     <div>

&nbsp;       <Label htmlFor="password">Password</Label>

&nbsp;       <Input

&nbsp;         id="password"

&nbsp;         type="password"

&nbsp;         placeholder="••••••••"

&nbsp;         {...register('password')}

&nbsp;       />

&nbsp;       {errors.password \&\& (

&nbsp;         <p className="text-sm text-red-600 mt-1">{errors.password.message}</p>

&nbsp;       )}

&nbsp;     </div>



&nbsp;     <Button type="submit" className="w-full">

&nbsp;       Log In

&nbsp;     </Button>

&nbsp;   </form>

&nbsp; );

}

```

Create `src/app/(auth)/login/page.tsx`:

```typescript

import { LoginForm } from '@/components/auth/login-form';

import Link from 'next/link';



export default function LoginPage() {

&nbsp; return (

&nbsp;   <div className="min-h-screen flex items-center justify-center bg-gray-50">

&nbsp;     <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">

&nbsp;       <div className="text-center">

&nbsp;         <h2 className="text-3xl font-bold">Welcome back</h2>

&nbsp;         <p className="mt-2 text-gray-600">Sign in to your account</p>

&nbsp;       </div>



&nbsp;       <LoginForm />



&nbsp;       <p className="text-center text-sm text-gray-600">

&nbsp;         Don't have an account?{' '}

&nbsp;         <Link href="/register" className="text-blue-600 hover:underline">

&nbsp;           Sign up

&nbsp;         </Link>

&nbsp;       </p>

&nbsp;     </div>

&nbsp;   </div>

&nbsp; );

}

```

\#### \*\*Step 7: Build the Landing Page\*\*

Create `src/app/page.tsx`:

```typescript

import Link from 'next/link';

import { Button } from '@/components/ui/button';

import { ArrowRight, Zap, Shield, TrendingUp } from 'lucide-react';



export default function LandingPage() {

&nbsp; return (

&nbsp;   <div className="min-h-screen">

&nbsp;     {/\* Hero Section \*/}

&nbsp;     <section className="py-20 px-4 bg-gradient-to-br from-blue-50 to-indigo-100">

&nbsp;       <div className="max-w-6xl mx-auto text-center">

&nbsp;         <h1 className="text-6xl font-bold text-gray-900 mb-6">

&nbsp;           The AI Agent Marketplace

&nbsp;         </h1>

&nbsp;         <p className="text-xl text-gray-700 mb-8 max-w-2xl mx-auto">

&nbsp;           Discover, deploy, and monetize AI agents. The only platform where

&nbsp;           agents buy from agents.

&nbsp;         </p>

&nbsp;         <div className="flex gap-4 justify-center">

&nbsp;           <Button asChild size="lg">

&nbsp;             <Link href="/agents">

&nbsp;               Browse Agents <ArrowRight className="ml-2 h-4 w-4" />

&nbsp;             </Link>

&nbsp;           </Button>

&nbsp;           <Button asChild variant="outline" size="lg">

&nbsp;             <Link href="/register">Sign Up Free</Link>

&nbsp;           </Button>

&nbsp;         </div>

&nbsp;       </div>

&nbsp;     </section>



&nbsp;     {/\* Features \*/}

&nbsp;     <section className="py-20 px-4">

&nbsp;       <div className="max-w-6xl mx-auto">

&nbsp;         <h2 className="text-4xl font-bold text-center mb-12">

&nbsp;           Why Choose Us?

&nbsp;         </h2>

&nbsp;         <div className="grid md:grid-cols-3 gap-8">

&nbsp;           <FeatureCard

&nbsp;             icon={<Zap className="h-8 w-8 text-blue-600" />}

&nbsp;             title="Lightning Fast"

&nbsp;             description="Deploy agents in seconds. Execute tasks in milliseconds."

&nbsp;           />

&nbsp;           <FeatureCard

&nbsp;             icon={<Shield className="h-8 w-8 text-green-600" />}

&nbsp;             title="Certified Quality"

&nbsp;             description="Every agent is tested, verified, and certified for quality."

&nbsp;           />

&nbsp;           <FeatureCard

&nbsp;             icon={<TrendingUp className="h-8 w-8 text-purple-600" />}

&nbsp;             title="Agent-to-Agent"

&nbsp;             description="Agents autonomously discover and pay other agents."

&nbsp;           />

&nbsp;         </div>

&nbsp;       </div>

&nbsp;     </section>



&nbsp;     {/\* CTA \*/}

&nbsp;     <section className="py-20 px-4 bg-blue-600 text-white">

&nbsp;       <div className="max-w-4xl mx-auto text-center">

&nbsp;         <h2 className="text-4xl font-bold mb-4">Ready to get started?</h2>

&nbsp;         <p className="text-xl mb-8">

&nbsp;           Join thousands of developers building the future of AI.

&nbsp;         </p>

&nbsp;         <Button asChild size="lg" variant="secondary">

&nbsp;           <Link href="/register">Create Free Account</Link>

&nbsp;         </Button>

&nbsp;       </div>

&nbsp;     </section>

&nbsp;   </div>

&nbsp; );

}



function FeatureCard({

&nbsp; icon,

&nbsp; title,

&nbsp; description,

}: {

&nbsp; icon: React.ReactNode;

&nbsp; title: string;

&nbsp; description: string;

}) {

&nbsp; return (

&nbsp;   <div className="p-6 border rounded-lg hover:shadow-lg transition-shadow">

&nbsp;     <div className="mb-4">{icon}</div>

&nbsp;     <h3 className="text-xl font-bold mb-2">{title}</h3>

&nbsp;     <p className="text-gray-600">{description}</p>

&nbsp;   </div>

&nbsp; );

}

```

\#### \*\*Step 8: Build Agent Listing Page\*\*

Create `src/hooks/use-agents.ts`:

```typescript

import { useQuery } from '@tanstack/react-query';

import { agentsApi } from '@/lib/api';



export function useAgents(filters?: {

&nbsp; search?: string;

&nbsp; category?: string;

&nbsp; limit?: number;

}) {

&nbsp; return useQuery({

&nbsp;   queryKey: \['agents', filters],

&nbsp;   queryFn: () => agentsApi.list(filters),

&nbsp; });

}



export function useAgent(id: string) {

&nbsp; return useQuery({

&nbsp;   queryKey: \['agents', id],

&nbsp;   queryFn: () => agentsApi.getById(id),

&nbsp;   enabled: !!id,

&nbsp; });

}

```

Create `src/components/agents/agent-card.tsx`:

```typescript

import Link from 'next/link';

import { Card } from '@/components/ui/card';

import { Badge } from '@/components/ui/badge';

import { Star, DollarSign } from 'lucide-react';



interface AgentCardProps {

&nbsp; agent: {

&nbsp;   id: string;

&nbsp;   name: string;

&nbsp;   description: string;

&nbsp;   category: string\[];

&nbsp;   pricing: {

&nbsp;     amount: number;

&nbsp;     currency: string;

&nbsp;   };

&nbsp;   stats: {

&nbsp;     rating: number;

&nbsp;     runs: number;

&nbsp;   };

&nbsp; };

}



export function AgentCard({ agent }: AgentCardProps) {

&nbsp; return (

&nbsp;   <Link href={`/agents/${agent.id}`}>

&nbsp;     <Card className="p-6 hover:shadow-lg transition-shadow cursor-pointer h-full">

&nbsp;       <div className="flex justify-between items-start mb-3">

&nbsp;         <h3 className="text-xl font-bold">{agent.name}</h3>

&nbsp;         <Badge variant="secondary">{agent.category\[0]}</Badge>

&nbsp;       </div>



&nbsp;       <p className="text-gray-600 mb-4 line-clamp-2">{agent.description}</p>



&nbsp;       <div className="flex justify-between items-center text-sm">

&nbsp;         <div className="flex items-center gap-1">

&nbsp;           <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />

&nbsp;           <span className="font-medium">{agent.stats.rating}</span>

&nbsp;           <span className="text-gray-500">({agent.stats.runs} runs)</span>

&nbsp;         </div>



&nbsp;         <div className="flex items-center gap-1 font-medium">

&nbsp;           <DollarSign className="h-4 w-4" />

&nbsp;           {agent.pricing.amount}

&nbsp;         </div>

&nbsp;       </div>

&nbsp;     </Card>

&nbsp;   </Link>

&nbsp; );

}

```

Create `src/app/(marketplace)/agents/page.tsx`:

```typescript

'use client';



import { useAgents } from '@/hooks/use-agents';

import { AgentCard } from '@/components/agents/agent-card';

import { Input } from '@/components/ui/input';

import { useState } from 'react';



export default function AgentsPage() {

&nbsp; const \[search, setSearch] = useState('');

&nbsp; const { data: agents, isLoading } = useAgents({ search });



&nbsp; return (

&nbsp;   <div className="min-h-screen bg-gray-50 py-12 px-4">

&nbsp;     <div className="max-w-7xl mx-auto">

&nbsp;       <div className="mb-8">

&nbsp;         <h1 className="text-4xl font-bold mb-4">Discover AI Agents</h1>

&nbsp;         <Input

&nbsp;           type="search"

&nbsp;           placeholder="Search agents..."

&nbsp;           value={search}

&nbsp;           onChange={(e) => setSearch(e.target.value)}

&nbsp;           className="max-w-md"

&nbsp;         />

&nbsp;       </div>



&nbsp;       {isLoading ? (

&nbsp;         <div>Loading...</div>

&nbsp;       ) : (

&nbsp;         <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">

&nbsp;           {agents?.map((agent: any) => (

&nbsp;             <AgentCard key={agent.id} agent={agent} />

&nbsp;           ))}

&nbsp;         </div>

&nbsp;       )}

&nbsp;     </div>

&nbsp;   </div>

&nbsp; );

}

```

---

\## 🎨 DESIGN GUIDELINES

\### \*\*Color Palette\*\*

```css

Primary: #3B82F6 (Blue)

Secondary: #8B5CF6 (Purple)

Success: #10B981 (Green)

Warning: #F59E0B (Orange)

Error: #EF4444 (Red)

Neutral: #6B7280 (Gray)

```

\### \*\*Typography\*\*

\- Headings: Bold, large (text-4xl to text-6xl)

\- Body: Regular, readable (text-base to text-lg)

\- Captions: Small, gray (text-sm text-gray-600)

\### \*\*Spacing\*\*

\- Generous padding (p-6, p-8)

\- Consistent gaps (gap-4, gap-6, gap-8)

\- Use Tailwind's spacing scale

\### \*\*Components\*\*

\- Cards: White background, subtle shadow, rounded corners

\- Buttons: Primary (filled), Secondary (outline), sizes (sm, default, lg)

\- Badges: Small pills for categories, status

\- Icons: Lucide React (consistent style)

---

\## ✅ ACCEPTANCE CRITERIA (Week 1)

By the end of Week 1, you should have:

\- \[ ] Next.js project created and running (`npm run dev`)

\- \[ ] Authentication pages (login, register) working

\- \[ ] Landing page with hero, features, CTA

\- \[ ] Agent listing page connected to backend API

\- \[ ] Agent card component displaying agent data

\- \[ ] Search functionality (basic)

\- \[ ] Responsive design (mobile-friendly)

\- \[ ] TypeScript with no errors

\- \[ ] Clean, organized code structure

\*\*Test it:\*\*

```bash

cd apps/web

npm run dev

\# Visit http://localhost:3000

\# Try registering, logging in, browsing agents

```

---

\## 📝 WHAT TO TELL YOUR AI CODER

Copy-paste this exact message:

---

\*\*TASK: Build Public Marketplace Frontend (Week 1 - Foundation)\*\*

We have a production-grade backend API for an AI agent marketplace. Your job is to build the Next.js frontend that connects to it.

\*\*What to build:\*\*

1\. Next.js 14 project (App Router, TypeScript, Tailwind)

2\. Authentication flow (login, register)

3\. Landing page (hero, features, CTA)

4\. Agent listing page (grid of agents)

5\. Agent card component

6\. API client setup with React Query

\*\*Backend API:\*\*

\- Base URL: `http://localhost:4000`

\- Endpoints documented in existing SDK (`packages/sdk/src/index.ts`)

\- Use the SDK types for TypeScript interfaces

\*\*Design Requirements:\*\*

\- Modern, clean UI (think Airbnb meets Hugging Face)

\- Tailwind CSS + shadcn/ui components

\- Mobile responsive

\- Fast loading (use React Query for caching)

\- Accessible (proper labels, keyboard navigation)

\*\*Follow the detailed instructions in `NEXT\_STEP\_INSTRUCTIONS.md` for:\*\*

\- Exact folder structure

\- Code examples for each component

\- API client setup

\- Authentication flow

\- Agent listing page

\*\*Deliverables:\*\*

\- Working Next.js app at `apps/web/`

\- Users can register, login, and browse agents

\- All pages are responsive and polished

\- Code is clean, typed, and well-organized

\*\*Timeline:\*\* Complete by end of Week 1 (Nov 20, 2025)

\*\*Questions?\*\* Check the backend code in `apps/api/` and the SDK in `packages/sdk/` for API details.

---

\## 🚨 CRITICAL REMINDERS

1\. \*\*Use existing backend\*\* - Don't rebuild APIs, just connect to them

2\. \*\*Type safety\*\* - Import types from SDK: `import type { Agent } from '@/types/agent'`

3\. \*\*Error handling\*\* - Always handle loading states and errors

4\. \*\*Mobile first\*\* - Design for mobile, enhance for desktop

5\. \*\*Performance\*\* - Use React Query caching, lazy load images

6\. \*\*Accessibility\*\* - Proper labels, keyboard navigation, ARIA attributes

---

\## 📞 SUPPORT

If you get stuck:

1\. Check the backend API code: `apps/api/src/`

2\. Check the SDK: `packages/sdk/src/index.ts`

3\. Check existing types: `apps/api/prisma/schema.prisma`

4\. Test backend endpoints with curl or Postman first

---

\## 🎯 SUCCESS = A BEAUTIFUL MARKETPLACE

By the end of Week 1, you should be able to:

\- Open http://localhost:3000

\- See a gorgeous landing page

\- Click "Browse Agents"

\- See real agents from your backend

\- Click an agent to see details (coming Week 2)

\- Register a new account

\- Log in

\*\*The backend is world-class. Make the frontend match it.\*\* 🚀
