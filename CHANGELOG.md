# Changelog

All notable changes to this collection are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `nomad` role: optional Consul and Vault integration, each on when given an
  address. Installs the CA each one's certificate is signed by, passes the
  agent's Consul token, and has servers sign workload identities for Consul
  (`consul.io`) and Vault (`vault.io`). The Consul token and the Consul and
  Vault auth methods are created outside the role. The new `stack` scenario
  runs Consul, Vault and Nomad from this collection on one node and checks,
  end to end, that a job registers its service in Consul and reads a Consul
  key and a Vault secret with its own identity.

### Changed

- `community.general` >= 10.5.0. Earlier releases have a typo in
  `consul_token` that makes a token with policies given by name report a
  change on every run.

## [0.1.1] - 2026-09-23

### Fixed

- `--check` did not report a version change. The download and unpack are
  skipped in check mode, and the restart hung off the unpack result, so a
  dry run said nothing about a binary that a real run would replace and a
  service it would restart. `hashicorp_release` now sets
  `hashicorp_release_changed` from the version it finds, before downloading,
  and `consul`, `vault` and `nomad` restart on that. Found by `--check` on a
  live host moving Consul from 1.20.2 to 2.0.4.

## [0.1.0] - 2026-09-23

### Added

- `hashicorp_release` role: installs a HashiCorp binary from
  releases.hashicorp.com, verified against the published SHA256SUMS. Compares
  the installed version, so a version bump upgrades in place.
- `consul` role: server or client agent with gossip encryption, TLS and ACLs
  with `default_policy: deny`. Agent keys are generated on the node and only
  a signing request reaches the controller. Every secret (CA, bootstrap token,
  agent tokens, gossip keys) can be given as a value from any store; what is
  not given is minted once into files on the controller. Agent tokens use the
  node's built-in identity. The plain HTTP port is off; the API is HTTPS only.
- `vault` role: Vault on integrated raft storage, TLS only, bound to one
  address. Initialises once, writing the unseal keys and root token to a file
  on the controller, and refuses to initialise when that file already exists.
  Unseals a sealed Vault on every run. Restarts on a new binary.
- `nomad` role: server, client or both, with gossip encryption, TLS and ACLs.
  Bootstraps ACLs with a token minted on the controller or given as a value,
  and checks on every run that it is the cluster's management token.
  Restarts on a new binary. Consul and Vault integration are not included yet.
- `tls_certificate` role: a node certificate signed by a CA held on the
  controller, with the key generated on the node. Used by `consul`,
  `vault` and `nomad`.
- `consul_keyring` module: converges the gossip keyring to a declared list,
  primary first. Rotation is two runs, `[new, old]` then `[new]`. Supports
  check and diff mode; the diff names keys by a hash prefix, never the key.
