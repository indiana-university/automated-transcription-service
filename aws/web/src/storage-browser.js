// Amplify MUST be configured before createStorageBrowser below reads the
// Storage config at import time — importing amplify-config does that.
import './amplify-config';
import {
  createAmplifyAuthAdapter,
  createStorageBrowser,
} from '@aws-amplify/ui-react-storage/browser';
import '@aws-amplify/ui-react-storage/styles.css';

// Drives the browser from the signed-in Cognito session's temporary credentials.
// The locations a user sees are governed entirely by the IAM role vended via
// their Cognito group, so the UI shows only what they're permitted to touch.
export const { StorageBrowser } = createStorageBrowser({
  config: createAmplifyAuthAdapter(),
});
