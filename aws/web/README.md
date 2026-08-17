# Storage Browser web app

A static [AWS Storage Browser for S3](https://aws.amazon.com/s3/features/storage-browser/)
app that lets an **authorized group of users** upload audio to, and download
transcripts from, the project's S3 buckets — without needing the AWS Console.

There is no server: signing in vends temporary, scoped AWS credentials to the
browser, and the app is hosted as static files on S3 behind CloudFront.

> **OpenID Connect single sign-on is required.** Sign-in federates to your
> institution's OIDC identity provider via Cognito; there are no local accounts,
> passwords, or email invitations. Deploying this feature therefore requires an
> IdP that speaks OIDC (e.g. Shibboleth with the OIDC plugin, Entra ID, Okta,
> Keycloak). Cognito-managed sign-in (native accounts with emailed invitations)
> is possible but deliberately not implemented.

## What users can do

- Browse the upload and download buckets.
- Upload audio files (single or multiple) to the upload bucket.
- Download multiple files at once: multi-select (or Select All) in a folder;
  batch downloads are delivered as a zip. Copy and delete also support
  multi-select (delete is permitted only on the upload bucket).
- The download bucket is read-only from the app; users cannot modify or delete
  transcripts.

## How access control works

1. Visiting the app redirects straight to the institution's identity provider
   (via the Cognito hosted domain) — no intermediate login page. After signing
   out, or after a failed attempt, a manual Sign in button is shown instead to
   avoid a redirect loop. **Who may sign in is controlled at the IdP** —
   register the relying party so only the authorized group can authenticate.
   There is no self sign-up and no local credential to attack.
2. On first successful login the user is provisioned just-in-time in the user
   pool; Cognito's Identity Pool then exchanges the session for **temporary AWS
   credentials**.
3. Those credentials come from a single IAM role scoped to exactly two buckets:
   read/write on the upload bucket, read-only on the download bucket.
4. Both buckets remain fully private (public access blocked); CORS allows only
   the app's own origin(s).

## Enabling the feature (it is off by default)

Everything (Cognito, OIDC provider, IAM role, web bucket, CloudFront, bucket
CORS) is gated behind one Terraform variable. In `ats.auto.tfvars`:

```hcl
enable_storage_browser = true
oidc_issuer_url        = "https://idp.example.edu"  # discovery doc at <issuer>/.well-known/openid-configuration
oidc_client_id         = "..."                      # issued by the IdP when the app is registered
oidc_client_secret     = "..."                      # issued by the IdP; see note below
```

Then `terraform apply` (see [`../terraform`](../terraform)). With the flag left
`false` (the default), none of these resources are created and the existing
pipeline is completely unchanged. Setting it back to `false` and re-applying
tears the feature down.

The client secret never reaches the browser — it is used only between Cognito
and the IdP. It lives in the git-ignored `ats.auto.tfvars` and in Terraform
state, so protect the state file accordingly.

### Registering with your identity provider

Registration happens **before** the first apply (the apply needs the client ID
and secret it produces). The IdP team needs:

- **Redirect URI**:
  `https://<domain prefix>.auth.<region>.amazoncognito.com/oauth2/idpresponse`,
  where the domain prefix is `cognito_domain_prefix` from `ats.auto.tfvars`
  (default: `<prefix>-storage-browser`, i.e. `ats-storage-browser`). After
  apply, the `oidc_redirect_uri` output shows the live value to double-check.
- **Scopes**: `openid email profile` (the email claim must be released)
- **Access policy**: restrict the relying party to the authorized group —
  this is where "only these users may use the app" is enforced

They return a **client ID and client secret**, which go into `ats.auto.tfvars`
as shown above.

## Build and deploy the app

Prerequisites: a current Node.js LTS release and the AWS CLI configured with the
same profile used for Terraform. The deploy script reads every value from `terraform output`, so
nothing is filled in by hand:

```bash
cd aws/web
AWS_PROFILE=<your-profile> ./deploy.sh
```

It generates `.env`, builds the bundle, syncs it to the web bucket, and
invalidates the CloudFront cache. The final line prints the app URL
(`storage_browser_url` — a `*.cloudfront.net` address by default).

### Optional custom domain

Not required — the default CloudFront URL works with zero extra configuration.
To use a custom domain instead, set `webapp_domain` and `acm_certificate_arn`
(an ACM certificate **in us-east-1**) in `ats.auto.tfvars`, re-apply, and point
a DNS CNAME at the CloudFront distribution.

## Local development

```bash
cp .env.template .env     # then fill from `terraform output` in ../terraform
npm install
npm run dev
```

To let the dev server (default `http://localhost:5173`) talk to the buckets and
complete the sign-in redirect, add that origin to `webapp_dev_origins` in
`ats.auto.tfvars` and re-apply — it is included in both the bucket CORS rules
and the sign-in callback URLs.

## Notes

- `.env` and `dist/` are git-ignored. Only generic, committable source lives
  here — no account-, bucket-, or institution-specific values.
- The committed `.npmrc` pins installs to the public npm registry so
  `package-lock.json` never picks up machine-specific registry URLs.
- Dependency versions live in `package.json` (pinned exactly by
  `package-lock.json`); the build is verified against the lockfile. After a
  major upgrade of the Amplify packages, check `src/amplify-config.js` and
  `src/storage-browser.js` against the
  [Storage Browser docs](https://ui.docs.amplify.aws/react/connected-components/storage/storage-browser).
