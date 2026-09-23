# Changelog

All notable changes to this collection are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `hashicorp_release` role: installs a HashiCorp binary from
  releases.hashicorp.com, verified against the published SHA256SUMS. Compares
  the installed version, so a version bump upgrades in place.
- `consul` role: server or client agent with gossip encryption, TLS from a CA
  kept on the controller, and ACLs with `default_policy: deny`. Bootstraps the
  ACL system once, creates an agent policy and token and hands the token to
  every agent. The plain HTTP port is off; the API is HTTPS only.
