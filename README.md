# eugene_panin.hashistack

Consul, Nomad and Vault, each with encryption, TLS and ACLs on from the first
run. They live in one collection because they are configured against each
other: Nomad registers its workloads in Consul and gets secrets from Vault,
and all three share how certificates and tokens are handled.

The roles are written for a cluster. One node is the case where
`bootstrap_expect` is 1 and there is no one to join; going to three nodes is
an inventory change, not a rewrite. The `cluster` scenario of the `nomad`
role runs Consul, Vault and Nomad on three nodes, checks that each has three
servers and every Vault node is unsealed, and rotates the Consul and Nomad
gossip keys across all three.

## Roles

| Role | Status | Purpose |
|---|---|---|
| [`consul`](roles/consul/README.md) | done | Agent with gossip encryption, TLS, ACLs |
| [`consul_dns`](roles/consul_dns/README.md) | done | Consul names through systemd-resolved, on the host and on extra addresses |
| [`vault`](roles/vault/README.md) | done | Server on raft storage, TLS only, initialised once, unsealed on every run |
| [`nomad`](roles/nomad/README.md) | done | Agent, server and client, with gossip encryption, TLS, ACLs |
| [`hashicorp_release`](roles/hashicorp_release/README.md) | done | Installs a HashiCorp binary, used by the roles above |
| [`tls_certificate`](roles/tls_certificate/README.md) | done | Node certificate from a controller-side CA; the node's key never leaves it |

| Module | Purpose |
|---|---|
| `consul_keyring` | Converges a Consul gossip keyring to a declared list of keys |

`hashicorp_release` downloads from releases.hashicorp.com and checks the
archive against the SHA256SUMS published for that version. It compares the
installed version rather than trusting that a binary exists, so changing the
version variable upgrades in place.

## Secrets

Every secret a role needs is a variable. Give it a value from whatever your
inventory reads secrets from, ansible-vault, SOPS, HashiCorp Vault, a password
manager, and the role writes nothing to disk on the controller. Leave it empty
and the role mints it once into a file on the controller, so a first run needs
nothing prepared.

Private keys are generated where they are used. An agent's key is created on
its node and only a signing request leaves it; the CA key stays with whoever
runs Ansible.

Whatever a service needs to start cannot come from a Vault that runs on top of
that service. Keep the bootstrap secrets outside the stack they bootstrap.

## Requirements

- ansible-core >= 2.19, with `cryptography` on the controller. CI runs
  2.19 and the latest release
- `community.crypto` >= 2.15.0 and `community.general` >= 10.5.0, pulled in
  automatically
- Debian or Ubuntu with systemd on the nodes

## Boundary

Nothing here depends on `eugene_panin.base` or any other collection. The
address each service binds to is a role variable set by the inventory. Run
it on WireGuard, a VLAN or a private network; the roles do not know or care.

## Development

Everything runs locally in Docker, the same way CI runs it:

```bash
make deps                                  # community.crypto, community.general
make lint                                  # yamllint and ansible-lint, production profile
make sanity                                # ansible-test sanity
make test ROLE=consul                      # every scenario of one role, Ubuntu 24.04
make test ROLE=vault SCENARIO='-s guard'   # one scenario
make matrix ROLE=nomad                     # one role on Ubuntu 24.04, 22.04 and Debian 12
make test-all                              # every role
```

CI runs the full matrix, every role on three distributions and on the oldest
supported ansible-core, plus sanity. A release goes out only from a green run.

Every scenario runs `--check` against a fresh host before converging, and
again against the converged one. Each behaviour a README or argument spec
claims has a test, and each test has been seen failing with the code it
covers removed.

## License

MIT — see [LICENSE](LICENSE).
