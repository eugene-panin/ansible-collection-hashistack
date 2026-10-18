# Changelog

All notable changes to this collection are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.9.1] - 2026-10-18

### Fixed

- `consul_dns`: Consul names resolve on a host whose provider adds a global
  DNS server to resolved, as GCE does. resolved keeps one current server for
  all its global ones, and once on the provider's sent `.consul` there, to an
  NXDOMAIN. The Consul domains now go to Consul on a dummy interface of their
  own, `consul-dns`, set by a unit of the same name that starts with resolved;
  the drop-in keeps only the extra listen addresses. The scenario adds a
  global server, as GCE does, and restarts resolved before it checks again.

## [0.9.0] - 2026-10-18

### Added

- `consul`, `nomad`: a server's certificate also names its Consul service,
  `consul.service.consul` and `nomad.service.consul` (or the
  `consul.server_service_name` given in `nomad_extra_config`), so their UIs
  open there without a warning, as Vault's already did. A node with a
  certificate from an earlier release gets a new one on the next run and its
  agent restarts once; the run after changes nothing. No address is added to
  any certificate. The `names` scenarios cover it.

## [0.8.2] - 2026-10-12

### Fixed

- `hashicorp_release`: the download tries five times, five seconds apart. One
  connection reset by releases.hashicorp.com failed the whole run.

## [0.8.1] - 2026-10-12

### Fixed

- `consul`: a new `consul_acl_agent_token` or `consul_acl_dns_token` takes
  the place of the old one. Consul refuses to change a token's secret, so a
  rotated token failed the run; now the token with the old secret is deleted
  and made again with the new one. The `rotation` scenario covers it.

## [0.8.0] - 2026-10-07

### Added

- `vault`: `vault_restore_snapshot` restores a raft snapshot into a Vault
  that is not initialised yet, such as on a new server that replaces a lost
  one, and unseals it with the keys of the cluster the snapshot is of. The
  `restore` scenario covers it.

## [0.7.1] - 2026-10-06

### Fixed

- `tls_certificate`: certificates begin an hour back (`tls_certificate_backdate`).
  They are signed on the controller, and a node whose clock was behind by
  seconds refused its own new certificate until it caught up, failing the
  run right after a CA rotation.

## [0.7.0] - 2026-09-29

### Added

- `vault`: `vault_auto_unseal` keeps the unseal keys on each node, readable by
  root only, and a unit unseals Vault whenever it starts, so a reboot no
  longer leaves the platform down until the next run. Off by default; turning
  it off removes the keys. Scenario `auto_unseal`.

## [0.6.0] - 2026-09-25

### Added

- `nomad`: `nomad_network_interface`, the interface job ports land on by
  default, and `nomad_host_networks`, named networks a job asks for by name,
  such as a public one for a reverse proxy. The new `networks` scenario checks
  each job gets its port on the address it should.
- `single_node`: the playbook turns on ufw through the `firewall` role of
  `eugene_panin.base`, denying incoming but SSH, WireGuard and whatever
  `firewall_allow` lists; the example sets `nomad_network_interface` rather
  than passing it through `nomad_extra_config`. The scenario runs a job in
  bridge mode behind the firewall and checks it answers on its mapped port
  and reaches both the internet and the host's API from inside its bridge.

### Changed

- Depends on `eugene_panin.base` >= 0.4.0, for the `firewall` role.

## [0.5.0] - 2026-09-25

### Added

- `playbooks/single_node.yml` and `examples/single_node/`: one server, managed
  and used only through WireGuard, with Consul under a domain of your own,
  Vault, Docker and Nomad wired together. Secrets are minted next to the
  inventory on the first run. The new `single_node` scenario runs the playbook
  against the example inventory itself.

### Fixed

- `consul_dns` broke every name outside the Consul domains on a host where
  systemd-resolved was not already the resolver, such as a stock Debian 12:
  it installed resolved, whose NSS module then asked it, and its drop-in
  replaced the upstream servers resolved had copied from `/etc/resolv.conf`
  with Consul. The role no longer installs resolved; it checks that resolved
  runs and knows the upstream servers on an interface, and stops otherwise.
  The 0.4.0 test gave the interface a DNS server itself before checking a
  public name and missed it; the `single_node` playbook found it on Debian.

### Changed

- Depends on `eugene_panin.base` >= 0.3.4, for WireGuard and Docker.
- CI lint installs the collection itself, as the example playbook's import
  needs it.

## [0.4.0] - 2026-09-25

### Added

- `consul_dns` role: Consul names through systemd-resolved, on the host and on
  extra addresses such as the WireGuard one, with every other name resolved
  as before.
- `consul`: `consul_alt_domain`, a second DNS domain next to `consul`, and a
  DNS token, without which Consul answers no DNS query under
  `default_policy` deny. The token is minted when `consul_acl_token_path` is
  set, or given as `consul_acl_dns_token`. Its `dns-read` policy has the rules
  of the `builtin/dns` template; `consul_token` reports a token with a
  templated policy as changed on every run.

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
