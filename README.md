# eugene_panin.hashistack

Consul, Nomad and Vault, each with encryption, TLS and ACLs on from the first
run. They live in one collection because they are configured against each
other: Nomad registers its workloads in Consul, Vault registers itself there
too, and all three share how certificates and tokens are handled.

The roles are written for a cluster. One node is the case where
`bootstrap_expect` is 1 and there is no one to join; going to three nodes is
an inventory change, not a rewrite.

## Roles

| Role | Status | Purpose |
|---|---|---|
| [`consul`](roles/consul/README.md) | done | Agent with gossip encryption, TLS, ACLs |
| `nomad` | not yet | Workload orchestration, registers into Consul |
| `vault` | not yet | Secrets, integrated raft storage |
| [`hashicorp_release`](roles/hashicorp_release/meta/argument_specs.yml) | done | Installs a HashiCorp binary, used by the three above |

`hashicorp_release` downloads from releases.hashicorp.com and checks the
archive against the SHA256SUMS published for that version. It compares the
installed version rather than trusting that a binary exists, so changing the
version variable upgrades in place.

## Secrets on the controller

Each role keeps two kinds of secret on the machine running Ansible, not on the
nodes:

- the CA private key, so nodes only ever receive certificates, never the
  means to issue them;
- the bootstrap tokens, which can only be obtained once per cluster.

Where they go is a required variable on each role. Nothing defaults into your
repository, and nothing should end up in git.

## Requirements

- ansible-core >= 2.15, with `cryptography` on the controller
- `community.crypto`, `community.general`, `ansible.posix`, pulled in
  automatically
- Debian or Ubuntu with systemd on the nodes

## Boundary

Nothing here depends on `eugene_panin.base` or any other collection. The
address each service binds to is a role variable set by the inventory. Run
it on WireGuard, a VLAN or a private network; the roles do not know or care.

## Development

```bash
yamllint .
ansible-lint --profile production
cd roles/<role> && molecule test
```

Every scenario runs `--check` against a fresh host before converging, and
again against the converged one. A role that cannot dry-run on a host where it
has never run is not finished.

## License

MIT — see [LICENSE](LICENSE).
