# Huron Knowledge Assistant - React Frontend

Modern React frontend for the Huron Enterprise Knowledge Assistant.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui + Radix UI
- **Icons**: Lucide React
- **State**: Zustand
- **Animations**: Framer Motion
- **Charts**: Recharts

## Quick Start

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the app.

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js 14 app router
│   │   ├── (auth)/             # Auth routes (login, register)
│   │   ├── (dashboard)/        # Dashboard routes
│   │   │   ├── page.tsx        # Main dashboard
│   │   │   ├── chat/           # Chat assistant
│   │   │   ├── ingest/         # Document upload
│   │   │   ├── search/         # Search interface
│   │   │   ├── analytics/      # Analytics dashboard
│   │   │   └── admin/          # Admin pages
│   │   ├── layout.tsx          # Root layout
│   │   └── globals.css         # Global styles
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── sidebar.tsx         # App sidebar
│   │   ├── header.tsx          # App header
│   │   └── theme-provider.tsx  # Dark mode provider
│   └── utils/
│       └── cn.ts               # Class name utility
├── tailwind.config.ts          # Tailwind configuration
├── next.config.js              # Next.js configuration
└── package.json                # Dependencies
```

## Design System

### Colors (Dark Mode)

| Role | Color | Hex |
|------|-------|-----|
| Primary | Deep Purple | `#440154` |
| Secondary | Teal | `#21918C` |
| Background | Dark Navy | `#1A1A2E` |
| Text | Light Gray | `#F5F5F5` |
| CTA | Bright Yellow | `#FDE725` |

### Department Colors

| Department | Color |
|------------|-------|
| HR | Green `#10B981` |
| Finance | Blue `#3B82F6` |
| Legal | Indigo `#6366F1` |
| Clinical | Red `#EF4444` |
| IT | Purple `#8B5CF6` |
| Operations | Orange `#F59E0B` |
| Marketing | Pink `#EC4899` |

## Features

- **Dashboard**: KPI cards, recent queries, quick actions
- **Chat Assistant**: AI-powered Q&A with department context
- **Document Ingest**: Upload and process documents
- **Search**: Full-text and semantic search
- **Admin Panel**: Department management, user management

## API Integration

The frontend proxies API requests to the FastAPI backend:

```javascript
// next.config.js
async rewrites() {
  return [
    {
      source: '/api/v1/:path*',
      destination: 'http://localhost:8000/api/v1/:path*',
    },
  ];
}
```

## Development

```bash
# Run with hot reload
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint
```

## Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=Huron Knowledge Assistant
```
