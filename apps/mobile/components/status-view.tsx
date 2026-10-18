import { ActivityIndicator, Image, ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  CircleCheck,
  CircleX,
  Clock,
  TriangleAlert,
  Unplug,
  type LucideIcon,
} from 'lucide-react-native';
import { formatVersions, type ReadinessResult } from '@devorchestrator/shared';
import { colors } from '@devorchestrator/tokens';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Text } from '@/components/ui/text';
import { useReduceMotion } from '@/hooks/use-reduce-motion';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const logo = require('@devorchestrator/tokens/assets/app-icon.png') as number;

export interface StatusViewProps {
  /** A check is running (first load or re-check). */
  loading: boolean;
  /** Last answer, null before the first one. */
  result: ReadinessResult | null;
  onRetry: () => void;
  appVersion: string;
}

const ICON_SIZE = 24;

const STATUS_LINES = {
  success: { Icon: CircleCheck, color: colors.success, label: 'All systems operational' },
  degraded: { Icon: TriangleAlert, color: colors.warning, label: 'Degraded' },
  error: { Icon: CircleX, color: colors.danger, label: 'API is up, but not ready' },
  unreachable: { Icon: Unplug, color: colors.danger, label: 'API unreachable' },
} as const;

function StateIcon({ Icon, color }: { Icon: LucideIcon; color: string }) {
  return (
    <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <Icon size={ICON_SIZE} color={color} />
    </View>
  );
}

function StatusLine({ loading, result }: Pick<StatusViewProps, 'loading' | 'result'>) {
  const reduceMotion = useReduceMotion();
  let content: React.ReactNode = null;
  if (loading) {
    content = (
      <>
        <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
          {/* The spinner is replaced by a static clock with reduced motion. */}
          {reduceMotion ? (
            <Clock size={ICON_SIZE} color={colors['fg-subtle']} />
          ) : (
            <ActivityIndicator size={ICON_SIZE} color={colors['fg-subtle']} />
          )}
        </View>
        <Text className="font-native-sans-medium">Checking the API…</Text>
      </>
    );
  } else if (result) {
    const { Icon, color, label } = STATUS_LINES[result.kind];
    content = (
      <>
        <StateIcon Icon={Icon} color={color} />
        <Text className="font-native-sans-medium">{label}</Text>
      </>
    );
  }
  if (!content) return null;
  return (
    <View accessibilityRole="summary" className="flex-row items-center gap-2">
      {content}
    </View>
  );
}

function Checks({ result }: { result: ReadinessResult | null }) {
  if (!result || result.kind === 'unreachable' || result.checks.length === 0) return null;
  return (
    <View className="w-full gap-2">
      {result.checks.map((check) => (
        <View key={check.name} className="min-h-touch flex-row items-center justify-between gap-4">
          <Text className="text-sm text-fg-muted">{check.label}</Text>
          <Badge>
            <StateIcon
              Icon={check.ok ? CircleCheck : CircleX}
              color={check.ok ? colors.success : colors.danger}
            />
            <Text>{check.ok ? 'OK' : 'Failed'}</Text>
          </Badge>
        </View>
      ))}
    </View>
  );
}

/** Presentational status page: no network calls, everything comes from props. */
export function StatusView({ loading, result, onRetry, appVersion }: StatusViewProps) {
  const apiVersion = result && result.kind !== 'unreachable' ? result.version : undefined;
  // Keep the variant of the last result while re-checking, so the button does not flicker.
  const primary = result?.kind === 'error' || result?.kind === 'unreachable';

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <ScrollView
        className="flex-1"
        contentContainerClassName="flex-grow items-center justify-center gap-6 px-4 py-8"
      >
        <View className="size-12 overflow-hidden rounded-md">
          <Image
            source={logo}
            accessibilityLabel="DevOrchestrator logo"
            resizeMode="cover"
            className="size-12 scale-150"
          />
        </View>
        <View className="items-center gap-1">
          <Text
            accessibilityRole="header"
            className="font-native-sans-semibold text-2xl leading-heading"
          >
            DevOrchestrator
          </Text>
          <Text className="text-sm text-fg-muted">AI agents. Real software.</Text>
        </View>

        <View accessibilityLiveRegion="polite" className="w-full items-center gap-4">
          <StatusLine loading={loading} result={result} />
          <Checks result={result} />
          {result?.kind === 'unreachable' ? (
            <Text className="text-center font-native-mono text-xs text-fg-muted">{result.url}</Text>
          ) : null}
        </View>

        <Text className="font-native-mono text-xs text-fg-subtle">
          {formatVersions(apiVersion, { name: 'Mobile', version: appVersion })}
        </Text>

        <Button
          className={loading ? 'w-full opacity-60' : 'w-full'}
          variant={primary ? 'default' : 'secondary'}
          // Not `disabled`: the button stays focusable for screen readers while checking.
          accessibilityState={{ disabled: loading, busy: loading }}
          onPress={loading ? undefined : onRetry}
        >
          <Text>Check again</Text>
        </Button>
      </ScrollView>
    </SafeAreaView>
  );
}
