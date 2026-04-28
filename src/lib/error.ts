import { isAxiosError } from 'axios';

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) {
      return detail;
    }
  }
  return fallback;
}