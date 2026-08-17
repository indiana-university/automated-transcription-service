// Amplify configuration, assembled from build-time environment variables.
// Importing this module CONFIGURES Amplify as a side effect — it must be
// imported before anything that reads Amplify config (see storage-browser.js,
// whose createStorageBrowser call runs at import time).
//
// All values come from `terraform output` and are injected via Vite env vars
// (see ../.env.template). Nothing here is environment- or institution-specific,
// so this file is safe to commit.
//
// Sign-in is OIDC SSO only: the oauth block points at the Cognito hosted
// domain, which brokers the redirect to the institution's identity provider.

import { Amplify } from 'aws-amplify';

const env = import.meta.env;

// Works for both the deployed site and local dev, as long as the origin is in
// the user pool client's callback list (Terraform: local.webapp_origins).
const origin = window.location.origin;

const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: env.VITE_USER_POOL_ID,
      userPoolClientId: env.VITE_USER_POOL_CLIENT_ID,
      identityPoolId: env.VITE_IDENTITY_POOL_ID,
      loginWith: {
        oauth: {
          domain: env.VITE_COGNITO_DOMAIN,
          scopes: ['openid', 'email', 'profile'],
          redirectSignIn: [origin],
          redirectSignOut: [origin],
          responseType: 'code',
        },
      },
    },
  },
  Storage: {
    S3: {
      // Default bucket plus the named buckets shown in the browser.
      bucket: env.VITE_UPLOAD_BUCKET,
      region: env.VITE_AWS_REGION,
      buckets: {
        [env.VITE_UPLOAD_BUCKET]: {
          bucketName: env.VITE_UPLOAD_BUCKET,
          region: env.VITE_AWS_REGION,
          // Storage Browser derives its visible "locations" from these path
          // rules — a bucket without `paths` is not shown at all. "*" exposes
          // the whole bucket. Keep permissions in sync with the IAM role in
          // aws/terraform/cognito.tf (the role is what actually enforces them).
          paths: {
            '*': { authenticated: ['get', 'list', 'write', 'delete'] },
          },
        },
        [env.VITE_DOWNLOAD_BUCKET]: {
          bucketName: env.VITE_DOWNLOAD_BUCKET,
          region: env.VITE_AWS_REGION,
          paths: {
            '*': { authenticated: ['get', 'list'] },
          },
        },
      },
    },
  },
};

Amplify.configure(amplifyConfig);
