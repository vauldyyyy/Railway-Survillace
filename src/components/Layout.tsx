import React from 'react';
import { Sidebar } from './Sidebar';

interface LayoutProps {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: any) => void;
}

export function Layout({ children, currentPage, onNavigate }: LayoutProps) {
  return (
    <div className="flex h-screen w-full bg-[#05080F] text-slate-300 font-sans overflow-hidden">
      <Sidebar currentPage={currentPage} onNavigate={onNavigate} />
      <main className="flex-1 flex flex-col h-full overflow-hidden relative min-w-0">
        {/* Subtle dot-grid background */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(#1e293b 1px, transparent 1px)',
            backgroundSize: '24px 24px',
            opacity: 0.2,
          }}
        />
        <div className="flex-1 overflow-y-auto relative z-10 h-full">
          {children}
        </div>
      </main>
    </div>
  );
}