import React from 'react';
import { Search } from 'lucide-react';

/**
 * SearchInput — Styled search input with icon.
 */
export default function SearchInput({ value, onChange, placeholder = 'Search...', className = '' }) {
  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-10 pr-4 py-2.5 bg-bg-secondary/50 border border-border-subtle rounded-lg
          text-sm text-text-primary placeholder:text-text-muted
          focus:outline-none focus:border-cyber/40 focus:shadow-glow-cyan
          transition-all duration-200"
      />
    </div>
  );
}
