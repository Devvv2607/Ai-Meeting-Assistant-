/**
 * Client-side session state, in one place.
 *
 * Auth is a backend-issued JWT in localStorage plus a cached profile blob —
 * no cookies, and no persistent Supabase session (the OAuth callback trades
 * the Supabase token for our JWT immediately and discards it), so clearing
 * these keys IS the complete sign-out.
 */

const AUTH_KEYS = ['access_token', 'mg-user'];

export function clearSession(): void {
  for (const key of AUTH_KEYS) {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  }
}

/** Clear all auth state and hard-navigate to the login page. `replace`
 *  drops the authenticated page from history and resets in-memory state. */
export function logout(): void {
  clearSession();
  window.location.replace('/login');
}
