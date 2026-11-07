# Ghostty ReleaseSafe builds

Unofficial macOS builds of [Ghostty](https://ghostty.org) tagged releases,
compiled with `-Doptimize=ReleaseSafe` instead of `ReleaseFast`. Safety checks
stay enabled, so memory safety bugs like several past Ghostty advisories crash
the app instead of causing undefined behavior.

A scheduled workflow builds every new upstream `vX.Y.Z` tag, signs it, publishes
it as a GitHub release, and adds it to a Sparkle appcast on GitHub Pages, which
the app's built-in updater uses.

## Installing

Download with `gh`, which doesn't set the quarantine attribute, so Gatekeeper
doesn't block the unnotarized app:

    gh release download -R filippo-agent/ghostty-releasesafe -p '*.zip'
    ditto -x -k Ghostty-*-ReleaseSafe.zip /Applications

Later versions arrive through Ghostty's updater, configured with the
[`auto-update`](https://ghostty.org/docs/config/reference#auto-update) option.

## How the builds differ from upstream

- The Zig core is built with `-Doptimize=ReleaseSafe`, and without
  translations (`-Di18n=false`), which would need gettext on the runner.
- The build uses no binary caches: Zig is the official release, checked
  against its minisign signature, instead of Ghostty's Nix environment.
- The updater feed URL is patched to point at this repository's appcast.
- Updates are signed with this repository's Sparkle EdDSA key.
- The app is signed with a self-signed certificate instead of a Developer ID,
  and isn't notarized. The certificate is the same for every build, so macOS
  privacy permissions (like Accessibility for global keybinds) persist across
  updates. Without a Team ID, the hardened runtime's library validation would
  refuse to load Sparkle, so the app has the
  `com.apple.security.cs.disable-library-validation` entitlement.

The bundle identifier is unchanged, so these builds share configuration and
preferences with official Ghostty builds. Don't install both.

## Setup

Repository secrets:

- `SPARKLE_PRIVATE_KEY`: base64 Ed25519 seed, as produced by Sparkle's
  `generate_keys -x`. The public key embedded in the app is derived from it.
- `MACOS_CERTIFICATE`: base64 PKCS#12 with the code signing certificate and
  key, exported with legacy encryption (`openssl pkcs12 -export -legacy`).
- `MACOS_CERTIFICATE_PWD`: the PKCS#12 password.

The certificate's common name must match `CERT_NAME` in the workflow.

GitHub Pages serves the `gh-pages` branch.

The build job runs upstream's build with no access to secrets. Signing and
publishing happen in a separate job that only receives the built app bundle,
extracts it away from its own code, and rejects symlinks that point outside it.
