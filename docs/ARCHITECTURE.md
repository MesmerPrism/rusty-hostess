# Architecture

Rusty Hostess T is an install and test shell for Manifold package development.
It is not a new authority layer. It consumes Manifold and package contracts,
executes named validation slots on target hosts, and exports evidence bundles.

## Authority

Manifold owns command descriptors, leases, package/runtime state, stream
registries, audit records, and scorecards.

Hostess T owns platform packaging, permission probes, launch/install routes,
small app UI surfaces, command bridging, and evidence export.

## Current Slice

The first implementation supports one live package slot:

- `live-smoke`: bounded HR/RR, ECG, or ACC capture for the Polar H10 package.

The Android app embeds selected package manifests as assets, opens the platform
sensor route itself, and writes evidence that includes the package manifest
hash. The desktop script follows the same evidence shape. Both desktop and
Android captures are accepted only after the shared evidence validator compares
the reported manifest hash against the supplied package root.

After a raw capture validates, `hostessctl` writes a
`rusty.manifold.hostess.run_evidence.v1` wrapper with a scorecard so the live
run is tied back to the Manifold Hostess contract spine.

## Non-Scope

This repo does not define package semantics, dynamic loading, product UI, or a
long-lived runtime daemon.
