# Integration tier

Use this reference only when the skill depends on authentication, a third-party
CLI/API, provider/model identity, capacity, or device-specific setup.

## Device contract

Commit a placeholder-only example and an exact ignore rule for the live device
file. The live file may record adapter names, executable paths, auth kinds,
models, profiles, and last-observed state; it never stores credential values.
Fetch secrets from the user's configured secret manager or native OAuth flow.

On a new device:

1. Discover only adapters the skill explicitly supports.
2. Compare installed adapters with the ignored device config.
3. Prompt for setup of a known adapter that is installed but unconfigured.
4. Record the exact executable, auth kind, provider, model, and requested effort.
5. Run identity smoke, then one bounded representative operation.
6. Keep smoke and representative readiness separate.

Seats may enter or leave the device config over time. Profiles deliberately
bind the currently configured seats before a run. A runtime failure never
reassigns work to another seat or model.

## Qualification states

Record `ready` only when observed provider/model exactly match the declaration
and no substitution occurred. Otherwise record `blocked` with one failure class
and a concrete recovery action:

- `auth` — complete or refresh the declared auth flow;
- `model` — select an exact supported model and requalify;
- `capacity` — retry the same declared seat later;
- `timeout` — bound and rerun the same representative operation later;
- `adapter` — repair the supported direct adapter or CLI contract.

Smoke proves reachability and identity only. Representative qualification uses
a realistic operation at the selected effort and timeout. A later smoke success
does not overwrite a representative failure.

## Example hygiene

Every committed string value in the config example is empty or an environment
placeholder such as `${MODEL}` or `${EXECUTABLE}`. This fail-closed rule avoids
provider-specific secret-name denylists.

The ignored device file is intentionally absent from a clean checkout.
Deterministic tests and receipt checks must still run; refreshing live readiness
requires one-time device setup.
