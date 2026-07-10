import { useEffect, useState } from 'react';
import { Button, Flex, Heading, Loader, Text, View } from '@aws-amplify/ui-react';
import { getCurrentUser, signInWithRedirect, signOut } from 'aws-amplify/auth';
import { Hub } from 'aws-amplify/utils';
import '@aws-amplify/ui-react/styles.css';
import { StorageBrowser } from './storage-browser';

// SAML SSO is the only sign-in path: no local accounts, no password form.
// Unauthenticated visitors are redirected straight to the identity provider.
const samlProvider = import.meta.env.VITE_SAML_PROVIDER;

// Set right before signOut so the post-sign-out page load shows a "signed out"
// screen instead of auto-redirecting the user straight back in.
const SIGNED_OUT_FLAG = 'ats-signed-out';

// Module-level so React StrictMode's double-mounted effect can't redirect twice.
let redirectStarted = false;

function startSignIn() {
  sessionStorage.removeItem(SIGNED_OUT_FLAG);
  if (redirectStarted) return;
  redirectStarted = true;
  signInWithRedirect({ provider: { custom: samlProvider } });
}

export default function App() {
  const [user, setUser] = useState(null);
  // checking | redirecting | signedOut | failed | ready
  const [status, setStatus] = useState('checking');

  useEffect(() => {
    // Catches the completion of the redirect flow after returning from the IdP.
    const unsubscribe = Hub.listen('auth', ({ payload }) => {
      if (payload.event === 'signedIn') {
        setUser(payload.data);
        setStatus('ready');
      }
      if (payload.event === 'signInWithRedirect_failure') {
        redirectStarted = false; // allow a manual retry
        setStatus('failed');
      }
    });

    // ?code / ?error mean we just came back from the IdP: don't redirect again,
    // let the pending token exchange finish and report through Hub above.
    const params = new URLSearchParams(window.location.search);
    const returningFromIdp = params.has('code') || params.has('error');

    getCurrentUser()
      .then((u) => {
        setUser(u);
        setStatus('ready');
      })
      .catch(() => {
        if (returningFromIdp) return;
        if (sessionStorage.getItem(SIGNED_OUT_FLAG)) {
          setStatus('signedOut');
          return;
        }
        setStatus('redirecting');
        startSignIn();
      });

    return unsubscribe;
  }, []);

  const handleSignOut = () => {
    sessionStorage.setItem(SIGNED_OUT_FLAG, '1');
    signOut();
  };

  if (status === 'checking' || status === 'redirecting') {
    return (
      <Flex direction="column" alignItems="center" gap="1rem" padding="4rem">
        <Loader size="large" />
        <Text>Redirecting to sign-in…</Text>
      </Flex>
    );
  }

  if (status !== 'ready' || !user) {
    return (
      <Flex direction="column" alignItems="center" gap="1rem" padding="4rem">
        <Heading level={3}>Automated Transcription Service — Files</Heading>
        <Text>
          {status === 'failed'
            ? 'Sign-in did not complete. Please try again.'
            : 'You have been signed out.'}
        </Text>
        <Button variation="primary" onClick={startSignIn}>
          Sign in
        </Button>
      </Flex>
    );
  }

  return (
    <View padding="1rem">
      <Flex justifyContent="space-between" alignItems="center" marginBottom="1rem">
        <Heading level={3}>Automated Transcription Service — Files</Heading>
        <Flex alignItems="center" gap="0.75rem">
          <Text fontSize="0.9rem">{user.signInDetails?.loginId ?? user.username}</Text>
          <Button size="small" onClick={handleSignOut}>
            Sign out
          </Button>
        </Flex>
      </Flex>
      <StorageBrowser />
    </View>
  );
}
