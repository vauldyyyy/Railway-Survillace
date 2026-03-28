import React from 'react';
import { Bell, Settings, User } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
  rightContent?: React.ReactNode;
  onNavigate?: (page: string) => void;
}

export function Header({ title, subtitle, children, rightContent, onNavigate }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-8 py-5 border-b border-slate-800/60 bg-[#0B0F19]/80 backdrop-blur-sm sticky top-0 z-20">
      <div>
        <h2 className="text-xl font-semibold text-slate-100 tracking-wide uppercase">{title}</h2>
        {subtitle && <p className="text-sm text-slate-400 mt-1">{subtitle}</p>}
      </div>
      
      <div className="flex items-center gap-6">
        {children}
        {rightContent}
        
        <div className="flex items-center gap-4 border-l border-slate-700 pl-6 ml-2">
          <button 
            onClick={() => onNavigate?.('notifications')}
            className="text-slate-400 hover:text-cyan-400 transition-colors relative"
          >
            <Bell size={18} />
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
          <button 
            onClick={() => onNavigate?.('system-config')}
            className="text-slate-400 hover:text-cyan-400 transition-colors"
          >
            <Settings size={18} />
          </button>
          <button 
            onClick={() => onNavigate?.('profile')}
            className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center border border-slate-600 overflow-hidden hover:border-cyan-400 transition-colors"
          >
            <img src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&q=80&w=100" alt="User" className="w-full h-full object-cover" />
          </button>
        </div>
      </div>
    </header>
  );
}
