import { resolveApiUrl, resolvePhase2ApiUrl, resolveHullApiUrl } from './api-url';

export const environment = {
  production: false,
  name: 'dev',
  apiUrl: resolveApiUrl(),
  // sonarjs/no-clear-text-protocols - Development environment uses http for local testing
  // eslint-disable-next-line sonarjs/no-clear-text-protocols
  API_URL: resolvePhase2ApiUrl(),
  HULL_API_URL: resolveHullApiUrl(),
};
