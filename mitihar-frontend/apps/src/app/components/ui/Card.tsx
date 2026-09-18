import React from 'react';
import { motion, useReducedMotion } from 'motion/react';
import { cn } from './utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'interactive';
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    const prefersReducedMotion = useReducedMotion();

    if (variant === 'interactive') {
      return (
        <motion.div
          ref={ref}
          className={cn(
            'rounded-lg border border-border bg-card shadow-[var(--shadow-card)] transition-shadow hover:shadow-[var(--shadow-card-hover)]',
            className
          )}
          whileHover={prefersReducedMotion ? undefined : { y: -2 }}
          transition={{ duration: 0.15 }}
          {...(props as React.ComponentProps<typeof motion.div>)}
        >
          {children}
        </motion.div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn('rounded-lg border border-border bg-card shadow-[var(--shadow-card)]', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Card.displayName = 'Card';
