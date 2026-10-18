import * as React from 'react';
import { Pressable } from 'react-native';
import { cva, type VariantProps } from 'class-variance-authority';
import { TextClassContext } from '@/components/ui/text';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  [
    'min-h-touch min-w-touch flex-row items-center justify-center gap-2 rounded-md px-6',
    'focus:outline-2 focus:outline-offset-2 focus:outline-accent-cyan',
  ].join(' '),
  {
    variants: {
      variant: {
        default: 'bg-primary active:opacity-90',
        secondary: 'border border-fg-subtle bg-surface active:bg-bg-deep',
      },
      disabled: { true: 'opacity-60', false: '' },
    },
    defaultVariants: { variant: 'default', disabled: false },
  },
);

const buttonTextVariants = cva('font-native-sans-medium text-base', {
  variants: {
    variant: { default: 'text-primary-foreground', secondary: 'text-fg' },
  },
  defaultVariants: { variant: 'default' },
});

type ButtonProps = React.ComponentProps<typeof Pressable> &
  Pick<VariantProps<typeof buttonVariants>, 'variant'>;

/** Children are the label: wrap it in `Text` (it picks up the button's text style). */
function Button({ className, variant, disabled, ...props }: ButtonProps) {
  return (
    <TextClassContext.Provider value={buttonTextVariants({ variant })}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ disabled: Boolean(disabled) }}
        disabled={disabled}
        className={cn(buttonVariants({ variant, disabled: Boolean(disabled) }), className)}
        {...props}
      />
    </TextClassContext.Provider>
  );
}

export { Button, buttonTextVariants, buttonVariants };
