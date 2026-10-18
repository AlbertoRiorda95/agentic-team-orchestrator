import {
  CircleCheck,
  CircleX,
  Clock,
  LoaderCircle,
  TriangleAlert,
  Unplug,
  type LucideIcon,
} from 'lucide-react';
import { formatVersions, type ReadinessResult } from '@devorchestrator/shared';
import logo from '@devorchestrator/tokens/assets/app-icon.png';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export interface StatusViewProps {
  /** A check is running (first load or re-check). */
  loading: boolean;
  /** Last answer, null before the first one. */
  result: ReadinessResult | null;
  onRetry: () => void;
  appVersion: string;
}

const STATUS_LINES = {
  success: { Icon: CircleCheck, color: 'text-success', label: 'All systems operational' },
  degraded: { Icon: TriangleAlert, color: 'text-warning', label: 'Degraded' },
  error: { Icon: CircleX, color: 'text-danger', label: 'API is up, but not ready' },
  unreachable: { Icon: Unplug, color: 'text-danger', label: 'API unreachable' },
} as const;

function StateIcon({ Icon, className }: { Icon: LucideIcon; className: string }) {
  return <Icon aria-hidden="true" className={`size-6 shrink-0 ${className}`} />;
}

function StatusLine({ loading, result }: Pick<StatusViewProps, 'loading' | 'result'>) {
  if (loading) {
    return (
      <p className="flex items-center gap-2 text-base font-medium text-fg">
        {/* The spinner is replaced by a static clock with reduced motion. */}
        <LoaderCircle
          aria-hidden="true"
          className="size-6 shrink-0 animate-spin text-fg-subtle motion-reduce:hidden"
        />
        <Clock
          aria-hidden="true"
          className="hidden size-6 shrink-0 text-fg-subtle motion-reduce:block"
        />
        Checking the API…
      </p>
    );
  }
  if (!result) return null;
  const { Icon, color, label } = STATUS_LINES[result.kind];
  return (
    <p className="flex items-center gap-2 text-base font-medium text-fg">
      <StateIcon Icon={Icon} className={color} />
      {label}
    </p>
  );
}

function Checks({ result }: { result: ReadinessResult | null }) {
  if (!result || result.kind === 'unreachable' || result.checks.length === 0) return null;
  return (
    <ul className="m-0 flex w-full list-none flex-col gap-2 p-0">
      {result.checks.map((check) => (
        <li key={check.name} className="flex min-h-8 items-center justify-between gap-4 text-sm">
          <span className="text-fg-muted">{check.label}</span>
          <Badge>
            {check.ok ? (
              <CircleCheck aria-hidden="true" className="size-4 text-success" />
            ) : (
              <CircleX aria-hidden="true" className="size-4 text-danger" />
            )}
            {check.ok ? 'OK' : 'Failed'}
          </Badge>
        </li>
      ))}
    </ul>
  );
}

/** Presentational status page: no network calls, everything comes from props. */
export function StatusView({ loading, result, onRetry, appVersion }: StatusViewProps) {
  const apiVersion = result && result.kind !== 'unreachable' ? result.version : undefined;
  // Keep the variant of the last result while re-checking, so the button does not flicker.
  const primary = result?.kind === 'error' || result?.kind === 'unreachable';

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-narrow flex-col items-center gap-6 px-4 pt-8 pb-8 md:justify-center md:pt-0">
      <div className="size-12 shrink-0 overflow-hidden rounded-md">
        <img src={logo} alt="DevOrchestrator logo" className="size-12 scale-150 object-cover" />
      </div>
      <div className="flex flex-col items-center gap-1 text-center">
        <h1 className="m-0 text-2xl leading-heading font-semibold text-fg">DevOrchestrator</h1>
        <p className="m-0 text-sm text-fg-muted">AI agents. Real software.</p>
      </div>

      <div role="status" aria-live="polite" className="flex w-full flex-col items-center gap-4">
        <StatusLine loading={loading} result={result} />
        <Checks result={result} />
        {result?.kind === 'unreachable' ? (
          <p className="m-0 font-mono text-xs break-all text-fg-muted">{result.url}</p>
        ) : null}
      </div>

      <p className="m-0 font-mono text-xs text-fg-subtle">
        {formatVersions(apiVersion, { name: 'Web', version: appVersion })}
      </p>

      <Button
        size="lg"
        variant={primary ? 'default' : 'secondary'}
        aria-disabled={loading}
        onClick={loading ? undefined : onRetry}
      >
        Check again
      </Button>
    </main>
  );
}
