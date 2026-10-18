import * as React from 'react';
import { View } from 'react-native';
import { cva, type VariantProps } from 'class-variance-authority';
import { TextClassContext } from '@/components/ui/text';
import { cn } from '@/lib/utils';

const badgeVariants = cva('flex-row items-center gap-1 rounded-full border px-2', {
  variants: {
    variant: {
      default: 'border-transparent bg-primary',
      outline: 'border-fg-subtle',
    },
  },
  defaultVariants: { variant: 'outline' },
});

const badgeTextVariants = cva('font-native-sans-medium text-xs', {
  variants: {
    variant: { default: 'text-primary-foreground', outline: 'text-fg' },
  },
  defaultVariants: { variant: 'outline' },
});

type BadgeProps = React.ComponentProps<typeof View> & VariantProps<typeof badgeVariants>;

/** Children: an optional icon and a `Text` label. */
function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <TextClassContext.Provider value={badgeTextVariants({ variant })}>
      <View className={cn(badgeVariants({ variant }), className)} {...props} />
    </TextClassContext.Provider>
  );
}

export { Badge, badgeTextVariants, badgeVariants };
