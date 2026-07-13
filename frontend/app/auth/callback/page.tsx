'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/services/api';

/**
 * OAuth landing page. Supabase redirects here after Google sign-in with
 * tokens in the URL fragment (#access_token=...). We trade that Supabase
 * token for this app's own JWT via the backend, then continue to the
 * dashboard — the rest of the app never knows Google was involved.
 */
export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    const oauthError = params.get('error_description') || params.get('error');
    const accessToken = params.get('access_token');

    if (oauthError) {
      setError(oauthError);
      return;
    }
    if (!accessToken) {
      setError('No sign-in token was returned. Please try again.');
      return;
    }

    api
      .googleExchange(accessToken)
      .then((res) => {
        localStorage.setItem('access_token', res.data.access_token);
        localStorage.setItem(
          'mg-user',
          JSON.stringify({
            email: res.data.email,
            full_name: res.data.full_name || res.data.email.split('@')[0],
          })
        );
        router.replace('/dashboard');
      })
      .catch((err) => {
        setError(
          err.response?.data?.detail || 'Google sign-in failed. Please try again.'
        );
      });
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-8">
      <div className="max-w-md text-center">
        {error ? (
          <>
            <h1 className="font-display text-[24px] font-semibold text-ink">
              Sign-in didn&apos;t complete
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink2">{error}</p>
            <Link
              href="/login"
              className="mt-6 inline-block rounded-md bg-accent px-5 py-3 text-[15px] font-semibold text-on-accent"
            >
              Back to sign in
            </Link>
          </>
        ) : (
          <p className="text-[15px] text-ink2">Finishing sign-in…</p>
        )}
      </div>
    </div>
  );
}
