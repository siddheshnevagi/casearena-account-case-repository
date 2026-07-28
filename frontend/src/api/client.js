/**
 * Single axios instance for the whole app. Handles attaching the bearer
 * token and transparently refreshing it once on a 401 — everywhere else in
 * the app just calls `api.get/post/...` without thinking about tokens.
 */
import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEYS = {
  access: "casearena_access_token",
  refresh: "casearena_refresh_token",
};

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEYS.access);
}

export function getRefreshToken() {
  return localStorage.getItem(TOKEN_KEYS.refresh);
}

export function setTokens({ access_token, refresh_token }) {
  if (access_token) localStorage.setItem(TOKEN_KEYS.access, access_token);
  if (refresh_token) localStorage.setItem(TOKEN_KEYS.refresh, refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEYS.access);
  localStorage.removeItem(TOKEN_KEYS.refresh);
}

export const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshInFlight = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    const isAuthEndpoint = config?.url?.startsWith("/auth/");

    if (response?.status !== 401 || isAuthEndpoint || config._retried) {
      return Promise.reject(error);
    }

    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearTokens();
      return Promise.reject(error);
    }

    config._retried = true;

    // Multiple requests can 401 at once (e.g. dashboard loads several
    // resources in parallel) — share one in-flight refresh instead of
    // firing a refresh call per failed request.
    refreshInFlight =
      refreshInFlight ||
      api
        .post("/auth/refresh", { refresh_token: refreshToken })
        .then(({ data }) => {
          setTokens({ access_token: data.access_token });
          return data.access_token;
        })
        .catch((refreshError) => {
          clearTokens();
          throw refreshError;
        })
        .finally(() => {
          refreshInFlight = null;
        });

    try {
      const newAccessToken = await refreshInFlight;
      config.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(config);
    } catch (refreshError) {
      return Promise.reject(refreshError);
    }
  }
);

export default api;
