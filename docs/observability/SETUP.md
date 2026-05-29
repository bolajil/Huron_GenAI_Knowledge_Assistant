# Observability Setup Guide
## Huron GenAI Knowledge Assistant

This guide covers the full observability stack for this platform. Each tool has a specific job —
they do not overlap and are not interchangeable. Sections 1–3 are active and ready to configure.
Sections 4–5 (LangSmith and Langfuse) are reserved for LLM-specific tracing and will be added
once the general observability layer is stable.

Complete in order. Each layer depends on the one before it being trustworthy.

---

## Table of Contents

| # | Tool | Layer | Time |
|---|------|-------|------|
| 1 | [Better Stack](#1-better-stack--uptime-monitoring) | Is the app running at all? | ~20 min |
| 2 | [Sentry](#2-sentry--error-tracking) | What is breaking and where? | ~2–3 hrs |
| 3 | [PostHog](#3-posthog--product-analytics) | How are people using it? | ~3–4 hrs |
| 4 | [LangSmith](#4-langsmith--llm-chain-tracing-coming-soon) | What is happening inside each LLM call? | *(coming soon)* |
| 5 | [Langfuse](#5-langfuse--llm-evaluation--prompt-management-coming-soon) | Are the prompts improving? Are the answers correct? | *(coming soon)* |
| 6 | [Verification Checklist](#6-verification-checklist) | Confirm everything is live | — |
| 7 | [File Map](#7-file-map--what-was-created) | What code was added | — |

---

## 1. Better Stack — Uptime Monitoring

**Time:** ~20 minutes  
**No code changes required — configured entirely from the Better Stack dashboard.**

**Why this tool first:**  
Before you can debug errors or analyse usage, you need to know whether the app is alive.
The Huron backend has crashed silently multiple times during development — each time the only
way to know was when someone noticed it was broken. Better Stack ends that. It pings the
`/health` endpoint from multiple locations every 30–60 seconds and calls or texts you within
one minute of a failure. It is the smoke alarm — everything else is the fire investigation.

---

### 1.1 Create Your Account

1. Go to **https://betterstack.com** and sign up. The free tier supports 10 monitors.
2. After signup you land on the dashboard — confirm you are in the **Uptime** section (not Logs).

> **Why sign up before doing anything else:** All monitoring is external. Better Stack cannot
> see your localhost. You need a public URL (your deployment domain, a VPS IP, or an ngrok
> tunnel) before adding the first monitor — having the account ready means you can add
> monitors the moment the app is deployed.

---

### 1.2 Add the Backend Monitor

1. Click **New monitor** (top-right).
2. Fill in:
   - **Monitor type:** `HTTP`
   - **URL:** `http://<your-server-ip>:8004/health`  
     *(during local dev, use ngrok to expose localhost: `ngrok http 8004` then use the ngrok URL)*
   - **Name:** `Huron Backend — /health`
   - **Check frequency:** `30 seconds` (paid) or `3 minutes` (free tier)
   - **Regions:** select at least **2** (e.g. US East + EU West)
3. Scroll to **Recovery confirmation** → set to `2 consecutive successes`.
4. Click **Create monitor**.

> **Why the `/health` endpoint:** It already exists in `main.py`. It returns `{"status":"ok"}`
> and exercises the process without hitting the database or Pinecone — a fast, cheap check.
> If this endpoint fails, the entire backend is unreachable regardless of the reason.
>
> **Why 2 regions:** A single-region check can false-alarm when that region has a momentary
> network blip. Requiring 2 regions to both see the failure before alerting prevents waking
> you up at 3am for a 10-second internet hiccup that self-resolved.
>
> **Why 2 consecutive successes for recovery:** Without this, a flapping server (fails,
> briefly recovers, fails again within seconds) closes and reopens the incident repeatedly,
> making it look like two separate incidents instead of one ongoing event.

---

### 1.3 Add the Frontend Monitor

1. Click **New monitor** again.
2. Fill in:
   - **Monitor type:** `HTTP`
   - **URL:** `https://<your-domain>` (the deployed Next.js app URL)
   - **Name:** `Huron Frontend`
   - **Expected status code:** `200`
3. Click **Create monitor**.

> **Why monitor the frontend separately from the backend:** They run as independent processes.
> The backend can be up while Next.js has crashed or stalled during a hot-reload. A user who
> cannot load the login page has the same experience whether the problem is the API or the UI —
> you need to know which one is the culprit immediately.

---

### 1.4 Set Up Alerting

1. Left sidebar → **On-call** → **Alert policies**.
2. Click **New alert policy** → name it `Huron Production`.
3. Add escalations:
   - Immediately → **Email**
   - After 5 minutes → **SMS** (add your phone under Team → your profile)
4. Back on each monitor → **Edit** → **Alert policy** → select `Huron Production`.

> **Why the 5-minute SMS escalation:** Email may not be seen immediately. If the backend is
> still down 5 minutes after you received the email and you have not acknowledged it, there is
> a good chance you missed the email. The SMS is the fallback to make sure the alert actually
> reaches you. Acknowledging the alert in the Better Stack dashboard stops the escalation.

---

### 1.5 Add a Status Page *(Optional but recommended)*

1. Left sidebar → **Status pages** → **New status page**.
2. Name it `Huron System Status`.
3. Add both monitors to it.
4. Share the public URL with your team.

> **Why a status page:** When something is wrong, the first thing users do is message you —
> "is the app down?" A public status page lets them check for themselves. It also builds
> trust because it shows you have visibility into your own systems.

---

### 1.6 Monitor Pinecone Reachability *(Optional)*

1. **New monitor** → **HTTP**
2. URL: `https://api.pinecone.io`
3. **Expected status:** `401`
4. Name it `Pinecone API Reachability`.

> **Why expect a 401:** Pinecone's API is auth-guarded. A `401 Unauthorized` response means
> Pinecone is up and responding correctly — it just rejected the unauthenticated ping. A
> connection timeout or `5xx` means Pinecone itself is having an outage, which would silently
> break every query in the app. Knowing Pinecone is down before users report empty results
> tells you immediately that the problem is external and not in your code.

---

## 2. Sentry — Error Tracking

**Time:** ~2–3 hours

**Why this tool second:**  
Better Stack tells you the app is down. Sentry tells you *why* it went down and everything
else that broke before it did. The Huron query pipeline has at least 5 network calls per
request — auth validation, RBAC check, Pinecone vector search, LLM call, database write.
Any of them can fail silently and the user just sees "No results" or a blank screen. Without
Sentry you are guessing. With Sentry you get the exact file, line number, input values that
triggered the failure, and the full stack trace — all within 30 seconds of the error occurring.

---

### 2.1 Create Your Account and Projects

1. Go to **https://sentry.io** and sign up.
2. Create an **organisation** — use your company or project name (e.g. `huron-consulting`).

> **Why a separate organisation (not just a project):** An organisation in Sentry groups
> multiple projects under one billing and team structure. You will have at least two projects
> (backend + frontend) and potentially more as the platform grows. Creating an organisation
> now means you do not have to restructure later.

#### Backend Project (Python)
3. Click **Create Project** → **Python** → **FastAPI**.
4. Name it `huron-backend`.
5. Sentry shows a DSN (Data Source Name) — it looks like:
   ```
   https://abc123def456@o1234567.ingest.sentry.io/7654321
   ```
6. Copy it. This goes into `backend/.env` as `SENTRY_DSN`.

> **Why a separate backend project:** Errors in the FastAPI backend and errors in the Next.js
> frontend have completely different shapes — Python tracebacks vs JavaScript stack traces,
> different error categories, different alert volumes. Keeping them in separate projects lets
> you set different alert thresholds, assign different team members, and see backend vs
> frontend error rates independently.

#### Frontend Project (Next.js)
7. Click **Create Project** → **JavaScript** → **Next.js**.
8. Name it `huron-frontend`.
9. Copy the DSN. This goes into `frontend/.env.local` as `NEXT_PUBLIC_SENTRY_DSN`.

---

### 2.2 Get a Sentry Auth Token

1. Top-left **org name** → **Settings** → **Auth Tokens**.
2. Click **Create New Token**.
3. Required scopes — select exactly these two:
   - `project:releases`
   - `org:read`
4. Click **Create Token** and copy the value immediately (it is only shown once).
5. Paste it into `frontend/.env.local` as `SENTRY_AUTH_TOKEN`.

> **Why source maps and why this token:** When Next.js builds for production it minifies
> and bundles all TypeScript into a single compressed JavaScript file. Without source maps,
> a Sentry error appears on line 1, column 94832 of `_app.js` — completely useless. With
> source maps uploaded, Sentry translates that back to the exact TypeScript file and line
> number in your codebase. The token gives the build process just enough permission to
> upload those maps during `npm run build`, nothing more.
>
> **Why only those 2 scopes:** The principle of least privilege. The token does one job —
> upload release artifacts. It does not need read or write access to issues, teams, or
> organisation members. If the token is ever leaked, the blast radius is limited to
> someone being able to upload source maps — not read your error data.

---

### 2.3 Fill In Your `.env` Files

Open `backend/.env` and add:
```
SENTRY_DSN=https://your-dsn@sentry.io/your-project-id
APP_ENV=development    # change to "production" when deployed
```

Open `frontend/.env.local` and add:
```
NEXT_PUBLIC_SENTRY_DSN=https://your-frontend-dsn@sentry.io/your-project-id
SENTRY_ORG=huron-consulting          # the slug shown in your Sentry URL
SENTRY_PROJECT=huron-frontend        # the project name you created
SENTRY_AUTH_TOKEN=sntrys_your_token_here
```

> **Why `APP_ENV`:** Sentry separates errors by environment. Errors from your local machine
> tagged as `development` are filtered out of the production alert feed. You will not be woken
> up because you threw a test exception at your desk. When you deploy to a server, setting
> `APP_ENV=production` ensures those errors go to the live production alert channel.
>
> **Why `NEXT_PUBLIC_` prefix on the DSN:** Next.js environment variables are only available
> in the browser if they are prefixed with `NEXT_PUBLIC_`. The Sentry DSN must be available
> at runtime in the browser so the client-side SDK can send error reports directly to Sentry.
> The DSN is safe to be public — it is designed to be embedded in client-side code and only
> allows error ingestion (nothing can be read or deleted with it).

---

### 2.4 Install the Packages

**Backend:**
```bash
cd "GenAI Knowledge Assistant Huron"
pip install sentry-sdk[fastapi]
```

**Frontend:**
```bash
cd frontend
npm install @sentry/nextjs
```

> **Why `sentry-sdk[fastapi]` (with the bracket):** The `[fastapi]` extra installs the
> FastAPI-specific integration alongside the base SDK. Without it, Sentry would not
> automatically instrument your FastAPI request lifecycle, meaning you would miss request
> context (the URL, method, and user agent) in error reports — they would just show a
> traceback with no HTTP context around it.

---

### 2.5 Verify Sentry Is Working

**Backend test:**
```bash
# Terminal 1 — start the backend
cd backend && python main.py

# Terminal 2 — trigger a request (any error during it reaches Sentry)
curl -X POST http://localhost:8004/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "sentry-test-trigger"}'
```
→ Sentry → `huron-backend` → **Issues**. Errors appear within 30 seconds.

**Frontend test:**
1. `npm run dev`, then open the app in a browser.
2. Open DevTools console and run:
   ```javascript
   throw new Error("Sentry frontend test");
   ```
3. Sentry → `huron-frontend` → **Issues**. Error appears within 30 seconds.

> **Why test with a real request rather than a mock:** The integration between Sentry and
> FastAPI only activates inside a real request context. A standalone `python -c "raise Error"`
> would confirm the SDK is installed but would not confirm the FastAPI integration is working
> correctly (it would miss HTTP context, user data, and endpoint labelling).

---

### 2.6 Configure Alerts in Sentry

1. Open `huron-backend` → **Alerts** → **Create Alert Rule**.
2. **Alert type:** `Issue`
3. **Condition:** `An issue is first seen`
4. **Action:** Send email to your address.
5. Repeat for `huron-frontend`.

> **Why "first seen" and not "every occurrence":** Some errors are noisy — a flaky network
> call might throw the same error 200 times in a minute. Alerting on every occurrence would
> bury your inbox. "First seen" alerts you once when a new problem type appears, which is
> when your attention is actually needed. You can review occurrence frequency in the Sentry
> dashboard separately.

> **What Sentry now covers automatically, with no further code changes:**
> - Every unhandled exception in every FastAPI endpoint
> - Silent failures inside the Pinecone and LLM call chain (if they throw)
> - React component crashes on any page
> - All Python `logging.error()` and `logging.exception()` calls
> - Frontend JavaScript errors including unhandled promise rejections

---

## 3. PostHog — Product Analytics

**Time:** ~3–4 hours

**Why this tool third:**  
Sentry tells you what is broken. PostHog tells you what is not being used — which is a
different kind of broken. You have 5 tabs in this application. PostHog will tell you within
two weeks which ones users actually open and which ones they never touch. It will tell you
which department submits the most queries, which users give negative feedback, and whether
anyone clicks the document version notification bell you just built. Without this data you
are making product decisions by guessing.

---

### 3.1 Create Your Account and Project

1. Go to **https://app.posthog.com** and sign up.
2. Create a new **project** — name it `Huron GenAI`.
3. PostHog shows a **Project API Key** starting with `ph_live_` or `phc_`.
4. Copy it into `frontend/.env.local` as `NEXT_PUBLIC_POSTHOG_KEY`.

> **Why one project (not one per environment):** PostHog's free tier gives you 1 million
> events per month per project. Splitting into dev/prod projects halves that allowance.
> Instead, the PostHog SDK is configured to only initialise when `NEXT_PUBLIC_POSTHOG_KEY`
> is set — leaving the key blank in development means no events are sent from your local
> machine without splitting the project.

---

### 3.2 Fill In Your `.env.local`

```
NEXT_PUBLIC_POSTHOG_KEY=phc_your_key_here
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
```

> **Why a `HOST` variable instead of hardcoding it:** PostHog offers EU data residency at
> `https://eu.posthog.com`. If your users are in Europe or you have GDPR obligations that
> require data to stay in the EU, you change one environment variable and no code changes.
> Hardcoding the US host now would require a code change and redeployment later.

---

### 3.3 Install the Package

```bash
cd frontend
npm install posthog-js
```

---

### 3.4 Add Event Calls to Key Pages

The analytics helper at `src/lib/analytics.ts` is already written with typed event functions.
Import and call them at the moments listed below. Every function is a no-op when no key is
configured, so adding them now is safe even before you have a PostHog account.

> **Why typed helper functions instead of calling `posthog.capture()` directly everywhere:**
> Raw `posthog.capture()` calls scattered across 10 files mean that renaming an event
> (`query_submitted` → `rag_query_submitted`) requires a grep across the entire codebase and
> risks missing one. The helper file is the single source of truth for every event name and
> its property shape. It also enforces that sensitive fields (query text, message content)
> are never accidentally passed — the function signatures only accept non-sensitive metadata.

#### Query Assistant — `src/components/Query/QueryAssistant.tsx`
After the query response is received:
```typescript
import { trackQuerySubmitted } from "../../lib/analytics";

trackQuerySubmitted({
  dept: user?.department ?? "general",
  responseTimeMs: result.response_time_ms,
  source: result.source ?? "rag",
  topK: 10,
});
```
> **Why track here:** This is the core action of the entire platform. Tracking it lets you
> measure query volume by department, compare RAG vs general-knowledge usage rates, and
> correlate response time with satisfaction feedback.

#### Ingest Page — `src/app/dashboard/ingest/page.tsx`
After a successful document upload response:
```typescript
import { trackDocUploaded } from "../../../lib/analytics";

trackDocUploaded({
  dept: selectedDept,
  fileType: file.name.split(".").pop() ?? "unknown",
  chunkCount: response.child_chunks,
  isNewVersion: !!docId,
});
```
> **Why track here:** Document ingestion is how the knowledge base grows. Tracking it shows
> you which departments are actively contributing content and which are only consuming it —
> useful for identifying where to focus onboarding effort.

#### Research Page — `src/app/dashboard/research/page.tsx`
After a successful research response:
```typescript
import { trackResearchSubmitted } from "../../../lib/analytics";

trackResearchSubmitted({
  dept: user?.department ?? "general",
  usedWeb: options.use_web,
  usedCrossDept: options.use_cross_dept,
  internalResultCount: result.internal_results.length,
  webResultCount: result.web_results.length,
});
```
> **Why track `internalResultCount` and `webResultCount`:** If web results are consistently
> high and internal results are consistently zero for a given department, that department's
> knowledge base is empty and their queries are leaking to the public internet. This is both
> a product quality issue and a potential confidentiality concern.

#### Agent Page — `src/app/dashboard/agent/page.tsx`
On run start and on completion:
```typescript
import { trackAgentRunStarted, trackAgentRunCompleted } from "../../../lib/analytics";

// When run begins:
trackAgentRunStarted({ dept: user?.department ?? "general", model: selectedModel });

// When status changes to complete or error (in the status watcher useEffect):
trackAgentRunCompleted({
  dept: user?.department ?? "general",
  durationMs: Date.now() - startTime,
  stepCount: steps.length,
  success: status === "complete",
});
```
> **Why both start and complete events:** The completion rate (starts ÷ completes) tells you
> whether users are abandoning agent runs mid-way, which would indicate the agent is too
> slow or the UI is confusing. Tracking only completions would make abandoned runs invisible.

#### Header Bell — `src/components/header.tsx`
Add one line inside the `openBell()` function:
```typescript
import { trackNotificationBellClicked } from "../lib/analytics";

const openBell = () => {
  trackNotificationBellClicked(unreadCount);  // ← add this
  setBellOpen((prev) => !prev);
  // ... rest of function
};
```
> **Why track bell clicks:** You built the document version notification feature specifically
> to help users know when new document versions are available. If nobody clicks the bell,
> the feature is not working as intended — either the notifications are not appearing at the
> right time, or users have not noticed the bell exists. This is the only way to know.

#### Feedback Submissions — wherever the thumbs-up/down is handled
```typescript
import { trackFeedbackSubmitted } from "../../lib/analytics";

trackFeedbackSubmitted({
  dept: user?.department ?? "general",
  rating: thumbsUp ? 1 : -1,
  source: result.source ?? "rag",
});
```
> **Why track this separately from the query:** The feedback table already stores ratings in
> the database. PostHog adds a layer on top: it lets you build a funnel from `query_submitted`
> → `feedback_submitted (rating=-1)` filtered by department. That funnel shows you which
> department's knowledge base is producing the worst answers, which the database alone cannot.

---

### 3.5 Verify PostHog Is Working

1. Run `npm run dev`.
2. Log in with any account.
3. PostHog dashboard → your project → **Live events** (left sidebar).
4. Perform any action in the app (open a tab, submit a query).
5. Events should appear in the Live events feed within 5 seconds.

> **Why check Live events and not the main dashboard:** The main PostHog dashboard aggregates
> data and can be empty for hours on a fresh project. Live events shows a real-time stream
> of every event as it arrives. It is the fastest confirmation that the SDK is initialised,
> the key is correct, and events are being received.

---

### 3.6 PostHog Dashboards to Create After 1–2 Weeks

**Tab Adoption**
- Insight type: Bar chart
- Event: `tab_opened` grouped by property `tab`
- Purpose: Shows which of the 5 tabs have real adoption vs which were built but never used.

**Query Quality by Department**
- Insight type: Funnel
- Steps: `query_submitted` → `feedback_submitted` (filter: `rating = -1`)
- Purpose: Identifies which department's knowledge base is producing the worst answers.

**Document Growth**
- Insight type: Line chart over time
- Event: `doc_uploaded` grouped by property `dept`
- Purpose: Shows which departments are actively growing their knowledge base.

**Agent Completion Rate**
- Insight type: Funnel
- Steps: `agent_run_started` → `agent_run_completed` (filter: `success = true`)
- Purpose: A low completion rate means users are abandoning agent runs — points to
  performance issues or confusing UX in the agent tab.

---

## 4. LangSmith — LLM Chain Tracing *(coming soon)*

**Why this tool is needed:**  
Better Stack, Sentry, and PostHog cover the infrastructure and product layers. None of them
can see *inside* an LLM call. LangSmith is built specifically to trace what happens at the
prompt level: what text was sent to the model, what the model returned, how long each step
in the chain took, and what the token cost was. This project uses LangChain for several
pipelines — LangSmith integrates with zero code changes for any code that uses LangChain's
standard interfaces.

**What it will answer once set up:**
- Which chain step (retrieval, reranking, synthesis) is the slowest?
- How many tokens does an average query consume? What is the monthly cost projection?
- When the model gives a wrong answer, what context chunks was it given?
- Which prompt version performs better — the current one or the candidate?

**What will be configured here:**
- `LANGCHAIN_TRACING_V2=true` environment variable
- `LANGCHAIN_API_KEY` from smith.langchain.com
- `LANGCHAIN_PROJECT` name
- Optional: automatic feedback logging from the existing `/api/v1/feedback` endpoint into LangSmith traces

*This section will be completed and filled in when you are ready to set up LangSmith.*

---

## 5. Langfuse — LLM Evaluation & Prompt Management *(coming soon)*

**Why this tool is needed and how it differs from LangSmith:**  
LangSmith is best for tracing chains built with LangChain. Langfuse is framework-agnostic
and focuses on two things LangSmith does not cover as deeply: **prompt versioning** and
**offline evaluation**. In this project, the system prompts for the RAG pipeline, the agent,
and the research synthesis are currently hardcoded strings in `main.py`. Langfuse moves those
prompts into a managed registry where you can version them, A/B test them, and roll back to
a previous version without a code deploy. The evaluation layer then lets you score model
outputs against a dataset of known good answers — a prerequisite for systematically improving
response quality.

**What it will answer once set up:**
- Did the prompt change I deployed yesterday improve or worsen answer quality?
- Which version of the system prompt produces the most faithful RAG answers?
- What is the false-positive rate of the source_guard (the hallucination detector)?

**What will be configured here:**
- Langfuse project API keys (public + secret)
- Python SDK integration in `backend/main.py` and `backend/utils/ingestion_service.py`
- Prompt registry entries for: RAG system prompt, agent instructions, research synthesis prompt
- Scoring integration with the existing thumbs-up/down feedback endpoint

*This section will be completed and filled in when you are ready to set up Langfuse.*

---

## 6. Verification Checklist

Run through this after each tool is configured. Do not mark an item done until you have
seen the evidence with your own eyes — not just "the config looks right."

### Better Stack
- [ ] Backend monitor shows a green **UP** badge in the dashboard
- [ ] Frontend monitor shows a green **UP** badge
- [ ] Both monitors have the `Huron Production` alert policy attached
- [ ] Kill the backend process and confirm an email arrives within 2 minutes
- [ ] Restart the backend and confirm the monitor returns to UP

### Sentry
- [ ] Backend starts with the log line: `Sentry initialised (env=development)`
- [ ] A test error appears in `huron-backend` → Issues within 30 seconds of triggering it
- [ ] A test error appears in `huron-frontend` → Issues within 30 seconds
- [ ] Alert rule on `huron-backend` is set to email on first-seen issue
- [ ] Alert rule on `huron-frontend` is set to email on first-seen issue
- [ ] `npm run build` output contains lines referencing Sentry source map upload

### PostHog
- [ ] `npm run dev` starts with no PostHog errors in the browser console
- [ ] After login, an `identify` call is visible in PostHog Live events (with `department` and `role` properties)
- [ ] Submitting a query generates a `query_submitted` event in Live events
- [ ] PostHog → Settings → Session replay → recording is enabled

---

## 7. File Map — What Was Created

```
GenAI Knowledge Assistant Huron/
│
├── backend/
│   ├── .env                              ← NEW: env variable template (fill in your keys)
│   └── main.py                           ← MODIFIED: Sentry init block before app creation
│
├── frontend/
│   ├── .env.local                        ← MODIFIED: Sentry + PostHog env vars added
│   ├── next.config.js                    ← MODIFIED: withSentryConfig wrapper (graceful no-op if package absent)
│   ├── sentry.client.config.ts           ← NEW: Sentry browser runtime — scrubs query text
│   ├── sentry.server.config.ts           ← NEW: Sentry Node.js runtime — strips auth headers
│   ├── sentry.edge.config.ts             ← NEW: Sentry Edge/middleware runtime
│   └── src/
│       ├── lib/
│       │   └── analytics.ts              ← NEW: typed PostHog helpers — no raw text ever passes through
│       ├── components/
│       │   └── providers/
│       │       └── PostHogProvider.tsx   ← NEW: PostHog context + auto-identifies users by ID
│       └── app/
│           └── layout.tsx                ← MODIFIED: PostHogProvider wraps entire app tree
│
├── requirements.txt                      ← MODIFIED: sentry-sdk[fastapi] added
└── docs/
    └── observability/
        └── SETUP.md                      ← this document
```

### One-time Install Commands

```bash
# Backend
pip install sentry-sdk[fastapi]

# Frontend
cd frontend
npm install @sentry/nextjs posthog-js
```

---

## Quick-Reference: All Environment Variables

| File | Variable | What it is | Where to get it |
|------|----------|------------|-----------------|
| `backend/.env` | `SENTRY_DSN` | Backend error ingest URL | Sentry → huron-backend → Settings → Client Keys |
| `backend/.env` | `APP_ENV` | Separates dev/prod errors in Sentry | Set to `development` locally, `production` on server |
| `frontend/.env.local` | `NEXT_PUBLIC_SENTRY_DSN` | Frontend error ingest URL | Sentry → huron-frontend → Settings → Client Keys |
| `frontend/.env.local` | `SENTRY_ORG` | Your org slug for source map uploads | Visible in your Sentry URL: `sentry.io/organizations/<slug>/` |
| `frontend/.env.local` | `SENTRY_PROJECT` | Project name for source map uploads | The name you typed when creating the Next.js project |
| `frontend/.env.local` | `SENTRY_AUTH_TOKEN` | Auth token to upload source maps at build time | Sentry → Settings → Auth Tokens → Create (scopes: `project:releases`, `org:read`) |
| `frontend/.env.local` | `NEXT_PUBLIC_POSTHOG_KEY` | PostHog project API key | PostHog → Project Settings → Project API Key |
| `frontend/.env.local` | `NEXT_PUBLIC_POSTHOG_HOST` | PostHog ingestion endpoint | `https://app.posthog.com` (US) or `https://eu.posthog.com` (EU) |
