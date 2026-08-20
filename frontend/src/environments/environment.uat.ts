import { resolveApiUrl, resolvePhase2ApiUrl } from './api-url';

export const environment = {
  production: false,
  name: 'uat',
  apiUrl: resolveApiUrl(),
  API_URL: resolvePhase2ApiUrl(),
};
