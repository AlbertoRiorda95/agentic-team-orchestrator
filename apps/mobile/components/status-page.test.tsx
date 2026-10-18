import { act, fireEvent, render, screen } from '@testing-library/react-native';
import { AppState } from 'react-native';
import { createApiClient } from '@devorchestrator/api-client';
import { StatusView } from '@/components/status-view';
import { StatusPage } from '@/components/status-page';

const BASE = 'http://localhost:8000/api/v1';

type Answer = () => Response | Promise<Response>;

function clientAnswering(...answers: Answer[]) {
  const queue = [...answers];
  const fetch = jest.fn(async () => {
    const next = queue.length > 1 ? queue.shift() : queue[0];
    if (!next) throw new TypeError('no answer prepared');
    return next();
  });
  return { client: createApiClient({ baseUrl: BASE, fetch }), fetch };
}

const ok: Answer = () =>
  Response.json({ status: 'ok', checks: { database: 'ok' }, version: '0.1.0+abc1234' });
const down: Answer = () =>
  Response.json(
    { status: 'down', checks: { database: 'failed' }, version: '0.1.0+abc1234' },
    { status: 503 },
  );
const unreachable: Answer = () => {
  throw new TypeError('Network request failed');
};

describe('StatusPage', () => {
  it('shows the loading state first, with a disabled button and no checks', async () => {
    // Never answers, but gives up when the page unmounts (aborted request).
    const client = createApiClient({
      baseUrl: BASE,
      fetch: (input) =>
        new Promise<Response>((_resolve, reject) => {
          (input as Request).signal.addEventListener('abort', () => reject(new Error('aborted')));
        }),
    });
    await render(<StatusPage client={client} baseUrl={BASE} />);

    expect(await screen.findByText('Checking the API…')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Check again' })).toBeDisabled();
    expect(screen.queryByText('Database')).toBeNull();
  });

  it('shows success with the checks and the versions', async () => {
    const { client } = clientAnswering(ok);
    await render(<StatusPage client={client} baseUrl={BASE} />);

    expect(await screen.findByText('All systems operational')).toBeTruthy();
    expect(screen.getByText('Database')).toBeTruthy();
    expect(screen.getByText('OK')).toBeTruthy();
    expect(screen.getByText('API 0.1.0+abc1234 · Mobile 0.1.0')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Check again' })).toBeEnabled();
  });

  it('shows the failed check when the API answers 503', async () => {
    const { client } = clientAnswering(down);
    await render(<StatusPage client={client} baseUrl={BASE} />);

    expect(await screen.findByText('API is up, but not ready')).toBeTruthy();
    expect(screen.getByText('Failed')).toBeTruthy();
  });

  it('shows unreachable with the URL tried and no checks on a network error', async () => {
    const { client } = clientAnswering(unreachable);
    await render(<StatusPage client={client} baseUrl={BASE} />);

    expect(await screen.findByText('API unreachable')).toBeTruthy();
    expect(screen.getByText(`${BASE}/health/ready`)).toBeTruthy();
    expect(screen.queryByText('Database')).toBeNull();
    expect(screen.getByText('API — · Mobile 0.1.0')).toBeTruthy();
  });

  it('checks again on the button', async () => {
    const { client, fetch } = clientAnswering(unreachable, ok);
    await render(<StatusPage client={client} baseUrl={BASE} />);
    await screen.findByText('API unreachable');

    await fireEvent.press(screen.getByRole('button', { name: 'Check again' }));

    expect(await screen.findByText('All systems operational')).toBeTruthy();
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('checks again when the app comes back to the foreground', async () => {
    let listener: (state: string) => void = () => {};
    const spy = jest.spyOn(AppState, 'addEventListener').mockImplementation(((
      _type: string,
      handler: (state: string) => void,
    ) => {
      listener = handler;
      return { remove: jest.fn() };
    }) as never);
    const { client, fetch } = clientAnswering(unreachable, ok);
    await render(<StatusPage client={client} baseUrl={BASE} />);
    await screen.findByText('API unreachable');

    await act(async () => listener('active'));

    expect(await screen.findByText('All systems operational')).toBeTruthy();
    expect(fetch).toHaveBeenCalledTimes(2);
    spy.mockRestore();
  });
});

describe('StatusView', () => {
  it('shows the degraded state with the warning label', async () => {
    await render(
      <StatusView
        loading={false}
        appVersion="0.1.0"
        onRetry={() => {}}
        result={{
          kind: 'degraded',
          version: undefined,
          checks: [{ name: 'database', label: 'Database', ok: true }],
        }}
      />,
    );

    expect(screen.getByText('Degraded')).toBeTruthy();
  });

  it('labels the logo and exposes the title as a header', async () => {
    await render(
      <StatusView
        loading={false}
        appVersion="0.1.0"
        onRetry={() => {}}
        result={{ kind: 'unreachable', url: `${BASE}/health/ready` }}
      />,
    );

    expect(screen.getByRole('header', { name: 'DevOrchestrator' })).toBeTruthy();
    expect(screen.getByLabelText('DevOrchestrator logo')).toBeTruthy();
  });
});
