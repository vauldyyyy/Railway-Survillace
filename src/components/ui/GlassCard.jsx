import React from 'react';

/**
 * GlassCard — Reusable glassmorphism container.
 * @param {string} className - Additional classes
 * @param {string} glowColor - 'cyan' | 'red' | 'orange' | 'none'
 * @param {boolean} hoverable - Enable hover glow effect
 */
export default function GlassCard({ children, className = '', glowColor = 'none', hoverable = true, onClick }) {
  const glowClasses = {
    cyan: 'glow-border-cyan',
    red: 'glow-border-red',
    orange: 'glow-border-orange',
    none: '',
  };

  return (
    <div
      onClick={onClick}
      className={`
        glass-card p-4
        ${glowClasses[glowColor]}
        ${hoverable ? 'hover:border-cyber/30 hover:shadow-glow-cyan cursor-pointer' : ''}
        ${onClick ? 'cursor-pointer' : ''}
        ${className}
      `}
    >
      {children}
    </div>
  );
}
