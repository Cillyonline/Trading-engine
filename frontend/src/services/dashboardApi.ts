export type DashboardStatus = {
  status: 'not-implemented';
};

export async function fetchDashboardStatus(): Promise<DashboardStatus> {
  return Promise.resolve({ status: 'not-implemented' });
}
