# Changelog

All notable changes to this collection are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `hashicorp_release` role: installs a HashiCorp binary from
  releases.hashicorp.com, verified against the published SHA256SUMS. Compares
  the installed version, so a version bump upgrades in place.
- `consul` role: server or client agent with gossip encryption, TLS from a CA
  kept on the controller, and ACLs with `default_policy: deny`. The bootstrap
  token and a per-node agent token are minted on the controller and handed to
  Consul; agent tokens use the node's built-in identity. The plain HTTP port is
  off; the API is HTTPS only.
- `consul_keyring` module: converges the gossip keyring to a declared list,
  primary first. Rotation is two runs, `[new, old]` then `[new]`. Supports
  check and diff mode; the diff names keys by a hash prefix, never the key.
