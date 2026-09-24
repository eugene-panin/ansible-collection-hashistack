# Changelog

All notable changes to this collection are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.3.2] - 2026-09-24

### Fixed

- `vault`: a three-node cluster never came up. Every node was unsealed at
  once, but a node joining over `vault_retry_join` is not initialised until
  it reaches an unsealed leader, so unsealing it failed, or was skipped with
  a threshold of 0. The first node is now unsealed first, and the others
  once they have reached it. Found by the new `cluster` scenario.
- `nomad`: rotating the gossip key restarted the agent, although a running
  server ignores the key in its configuration once its keyring file exists.
  A restart is now queued only when the configuration changed beyond that key.
- The collection README said Vault registers itself in Consul; the `vault`
  role does not configure that.

### Added

- `cluster` scenario: Consul, Vault and Nomad on three nodes, joined with
  `retry_join`; checks three servers for each, every Vault node unsealed, and
  a rotation of the Consul and Nomad gossip keys across all three.

## [0.3.1] - 2026-09-24

### Fixed

- `nomad`: `--check` failed on a host already running Nomad when CNI was
  turned on or its version changed: the release directory is only simulated
  in check mode, and the download into it failed. Download and unpack are now
  skipped in check mode until the release directory exists; the link and the
  restart are still reported. Found by `--check` on a live host. The new `cni`
  scenario turns CNI on for a running Nomad, so its `check` step covers it.

## [0.3.0] - 2026-09-24

### Breaking changes

- `nomad`: `nomad_gossip_key`, a string, is replaced by `nomad_gossip_keys`,
  a list, primary first, as `consul_gossip_keys` already was. A single key
  becomes a one-item list.
- `ansible.posix` is a new dependency, for sysctl.

### Added

- `nomad_keyring` module and gossip key rotation in the `nomad` role. The
  keyring is converged to `nomad_gossip_keys` through the agent API; a
  rotation is two runs, `[new, old]` then `[new]`. Nomad's API does not
  report the primary key, so the module reads it from the server's keyring
  file. Tested by the new `rotation` scenario.
- `nomad`: `nomad_cni` installs the CNI reference plugins, checked against
  the published checksum, behind a versioned `/opt/cni/bin` link, and makes
  bridged traffic pass through iptables. Needed for bridge networking.
- `nomad`: Consul service mesh. The role sets `grpc_ca_file` to the Consul
  CA, which Nomad does not take from `ca_file`; Nomad finds the gRPC port on
  its own, and clients need `nomad_cni: true`.
  The scenario runs two groups in bridge mode with Envoy sidecars and checks
  one reaches the other through the mesh.

### Changed

- `consul_keyring` shares its planning code with `nomad_keyring`; its
  behaviour is unchanged, and the consul `rotation` scenario still passes.
- The Molecule scenarios are no longer shipped in the Galaxy artifact.
- CI actions moved off Node 20: checkout v5, setup-python v6, upload-artifact v6.

## [0.2.0] - 2026-09-24

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
