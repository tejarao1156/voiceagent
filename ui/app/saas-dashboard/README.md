# SaaS Voice Agent Dashboard

A professional SaaS-style dashboard for managing Voice AI Agents, inspired by HighLevel/GHL AI Agents interface.

## Features

- **Left Sidebar Navigation** - Dark theme (#0F172A) with navigation items
- **Top Navigation Bar** - Clean white bar with section tabs
- **Agent List Table** - Professional table view with actions dropdown
- **Create Agent Modal** - Form to create new voice agents
- **Smooth Animations** - Framer Motion transitions throughout
- **Responsive Design** - Built with TailwindCSS

## Access

The dashboard is accessible at:
- **Next.js Route**: `/saas-dashboard`
- **Full URL**: `http://localhost:9000/saas-dashboard` (when Next.js dev server is running)

## Components

- `Sidebar.tsx` - Left navigation sidebar
- `TopNav.tsx` - Top navigation bar with tabs
- `AgentTable.tsx` - Main agent list table component
- `CreateAgentModal.tsx` - Modal for creating new agents
- `page.tsx` - Main dashboard page

## Tech Stack

- React + TypeScript
- Next.js (App Router)
- TailwindCSS
- ShadCN UI components
- Lucide Icons
- Framer Motion
- React Table (@tanstack/react-table)

## Usage

1. Start the Next.js dev server:
   ```bash
   cd ui
   npm run dev
   ```

2. Navigate to `http://localhost:9000/saas-dashboard`

3. Use the sidebar to navigate between sections
4. Click "Create Agent" to add new agents
5. Use the dropdown menu (⋮) on each agent row for actions

## Future Enhancements

- Connect to backend API
- Real-time call monitoring
- Analytics and reporting
- Agent configuration pages
- Voice customization interface
- Activity logs viewer

