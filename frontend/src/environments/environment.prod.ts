import { resolveApiUrl, resolvePhase2ApiUrl } from './api-url';

export const environment = {
  production: true,
  name: 'prod',
  apiUrl: resolveApiUrl(),
  API_URL: resolvePhase2ApiUrl(),
};
