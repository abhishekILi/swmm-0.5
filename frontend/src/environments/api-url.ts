// Main API (Port 8000) - Default for most API calls
export const resolveApiUrl = (): string => {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000/';
  }

  const { protocol, hostname, host } = window.location;

  // Local development
  if (hostname === '127.0.0.1') {
    return 'http://127.0.0.1:8000/';
  }

  if (hostname === 'localhost') {
    return 'http://localhost:8000/';
  }

  return `${protocol}//${host}/`;
};

// Phase 2 API (Port 8080) - Fixed backend service URL for all environments
// sonarjs/no-clear-text-protocols - Development environment uses http for external service
// eslint-disable-next-line sonarjs/no-clear-text-protocols
export const resolvePhase2ApiUrl = (): string => {
  // Phase 2 API always points to the fixed external service
  return 'https://itttm-phase2-api.ilizien-projects-cdf.in/';
};
