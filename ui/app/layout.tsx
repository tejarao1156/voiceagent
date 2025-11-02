import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'OpenAI Realtime Voice Chat',
  description: 'Talk to OpenAI Realtime API with your microphone',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

