import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { describe, expect, it, vi } from 'vitest';
import { StatusView } from '@/components/status-view';
import { StatusPage } from '@/status-page';

const BASE = 'http://localhost:3000/api/v1';

type Answer = () => Response | Promise<Response>;

function fakeFetch(...answers: Answer[]) {
  const queue = [...answers];
  return vi.fn(async () => {
    const next = queue.length > 1 ? queue.shift() : queue[0];
    if (!next) throw new TypeError('no answer prepared');
    return next();
  });
}

const ok: Answer = () =>
  Response.json({ status: 'ok', checks: { database: 'ok' }, version: '0.1.0+abc1234' });
const down: Answer = () =>
  Response.json(
    { status: 'down', checks: { database: 'failed' }, version: '0.1.0+abc1234' },
    { status: 503 },
  );
const unreachable: Answer = () => {
  throw new TypeError('Failed to fetch');
};

describe('StatusPage', () => {
  it('shows the loading state first, with a disabled button and no checks', async () => {
    const pending = fakeFetch(() => new Promise<Response>(() => {}));
    render(<StatusPage baseUrl={BASE} fetch={pending} />);

    expect(screen.getByText('Checking the API…')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Check again' })).toBeDisabled();
    expect(screen.queryByText('Database')).not.toBeInTheDocument();
  });

  it('shows success with the checks and the versions', async () => {
    render(<StatusPage baseUrl={BASE} fetch={fakeFetch(ok)} />);

    expect(await screen.findByText('All systems operational')).toBeInTheDocument();
    expect(screen.getByText('Database')).toBeInTheDocument();
    expect(screen.getByText('OK')).toBeInTheDocument();
    expect(screen.getByText('API 0.1.0+abc1234 · Web 0.1.0')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Check again' })).toBeEnabled();
  });

  it('shows the failed check when the API answers 503', async () => {
    render(<StatusPage baseUrl={BASE} fetch={fakeFetch(down)} />);

    expect(await screen.findByText('API is up, but not ready')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Database')).toBeInTheDocument();
  });

  it('shows unreachable with the URL tried and no checks on a network error', async () => {
    render(<StatusPage baseUrl={BASE} fetch={fakeFetch(unreachable)} />);

    expect(await screen.findByText('API unreachable')).toBeInTheDocument();
    expect(screen.getByText(`${BASE}/health/ready`)).toBeInTheDocument();
    expect(screen.queryByText('Database')).not.toBeInTheDocument();
    expect(screen.getByText('API — · Web 0.1.0')).toBeInTheDocument();
  });

  it('treats an unexpected response as unreachable', async () => {
    const html: Answer = () => new Response('<html>Bad gateway</html>', { status: 502 });
    render(<StatusPage baseUrl={BASE} fetch={fakeFetch(html)} />);

    expect(await screen.findByText('API unreachable')).toBeInTheDocument();
  });

  it('checks again on the button and keeps the previous result while it runs', async () => {
    let release: (response: Response) => void = () => {};
    const slow: Answer = () => new Promise<Response>((resolve) => (release = resolve));
    const fetchMock = fakeFetch(unreachable, slow);
    render(<StatusPage baseUrl={BASE} fetch={fetchMock} />);
    await screen.findByText('API unreachable');

    await userEvent.click(screen.getByRole('button', { name: 'Check again' }));

    expect(screen.getByText('Checking the API…')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Check again' })).toBeDisabled();
    release(await ok());
    expect(await screen.findByText('All systems operational')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('checks again when the window gets focus', async () => {
    const fetchMock = fakeFetch(unreachable, ok);
    render(<StatusPage baseUrl={BASE} fetch={fetchMock} />);
    await screen.findByText('API unreachable');

    window.dispatchEvent(new Event('focus'));

    expect(await screen.findByText('All systems operational')).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });
});

describe('StatusView', () => {
  const noop = () => {};

  it('shows the degraded state with the warning label', () => {
    render(
      <StatusView
        loading={false}
        appVersion="0.1.0"
        onRetry={noop}
        result={{
          kind: 'degraded',
          version: undefined,
          checks: [{ name: 'database', label: 'Database', ok: true }],
        }}
      />,
    );

    expect(screen.getByText('Degraded')).toBeInTheDocument();
    expect(screen.getByText('API — · Web 0.1.0')).toBeInTheDocument();
  });

  it('lists the failed rows first', () => {
    render(
      <StatusView
        loading={false}
        appVersion="0.1.0"
        onRetry={noop}
        result={{
          kind: 'error',
          version: undefined,
          checks: [
            { name: 'database', label: 'Database', ok: false },
            { name: 'cache', label: 'Cache', ok: true },
          ],
        }}
      />,
    );

    const rows = screen.getAllByRole('listitem').map((row) => row.textContent);
    expect(rows).toEqual(['DatabaseFailed', 'CacheOK']);
  });

  it('has one h1, a labelled logo, a live region and one focusable element', async () => {
    render(
      <StatusView
        loading={false}
        appVersion="0.1.0"
        onRetry={noop}
        result={{ kind: 'unreachable', url: `${BASE}/health/ready` }}
      />,
    );

    expect(screen.getByRole('heading', { level: 1, name: 'DevOrchestrator' })).toBeInTheDocument();
    expect(screen.getByAltText('DevOrchestrator logo')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
    await userEvent.tab();
    expect(screen.getByRole('button', { name: 'Check again' })).toHaveFocus();
  });

  it.each([
    ['loading', { loading: true, result: null }],
    ['success', { loading: false, result: { kind: 'success', version: '0.1.0', checks: [] } }],
    [
      'error',
      {
        loading: false,
        result: {
          kind: 'error',
          version: '0.1.0',
          checks: [{ name: 'database', label: 'Database', ok: false }],
        },
      },
    ],
    [
      'unreachable',
      { loading: false, result: { kind: 'unreachable', url: `${BASE}/health/ready` } },
    ],
  ] as const)('has no axe violations in the %s state', async (_name, props) => {
    const { container } = render(
      <StatusView
        loading={props.loading}
        result={props.result as never}
        appVersion="0.1.0"
        onRetry={noop}
      />,
    );

    expect(await axe(container)).toHaveNoViolations();
  });
});
