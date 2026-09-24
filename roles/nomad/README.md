# nomad

Runs a Nomad agent with gossip encryption, TLS and ACLs on from the first run.
Server, client or both on one node; a single node running both is the
degenerate case of a cluster, and growing it is an inventory change.

```yaml
- name: Nomad
  hosts: nomad_servers
  become: true
  roles:
    - role: eugene_panin.hashistack.nomad
      vars:
        nomad_bind_address: 10.77.0.1
        nomad_pki_ca_cert: "{{ lookup('ansible.builtin.file', 'files/ca.pem') }}"
        nomad_pki_ca_key: "{{ vault_internal_ca_key }}"
        nomad_acl_bootstrap_token: "{{ vault_nomad_bootstrap_token }}"
        nomad_gossip_key: "{{ vault_nomad_gossip_key }}"
```

## Secrets

| Secret | Given as | Minted when not given |
|---|---|---|
| CA certificate and key | `nomad_pki_ca_cert`, `nomad_pki_ca_key` | into `nomad_pki_dir` on the controller |
| Bootstrap token | `nomad_acl_bootstrap_token` | into `nomad_acl_token_path` on the controller |
| Gossip key | `nomad_gossip_key` | on the first server, shared with the rest |

The bootstrap token is minted before Nomad sees it and passed as the bootstrap
secret, so no secret depends on parsing a reply. Each run checks that the
token it holds is the cluster's management token and fails if it is not.

## What it listens on

API and UI on 4646, HTTPS only. RPC between agents is TLS with server
hostname verification; the HTTP API does not ask for a client certificate, so
a browser can open the UI. Every request needs an ACL token: an anonymous one
gets 403.

The certificate names `server.<region>.nomad` and `client.<region>.nomad` as
the node's roles require, and is issued by the `tls_certificate` role: the key
is generated on the node, the controller signs it.

## Consul and Vault

Both are off until given an address, and each is independent of the other.
The role only configures the Nomad side. It does not depend on the `consul`
or `vault` roles; the playbook passes the addresses, the CA and the token.

```yaml
nomad_consul_address: 127.0.0.1:8501
nomad_consul_ca_cert: "{{ lookup('ansible.builtin.file', 'files/ca.pem') }}"
nomad_consul_token: "{{ vault_nomad_consul_token }}"
nomad_vault_address: https://10.77.0.1:8200
nomad_vault_ca_cert: "{{ lookup('ansible.builtin.file', 'files/ca.pem') }}"
```

With no `nomad_consul_address` there is no `consul` block. Nomad still
probes 127.0.0.1:8500 at startup and logs a warning when nothing answers;
that is Nomad's default.

Servers sign workload identities: for Consul with audience `consul.io`, for
Vault with audience `vault.io`. Jobs then log in with their own identity.
What has to exist on the other side is not configuration of this node, so the
role leaves it to Terraform or to `nomad setup consul` / `nomad setup vault`:

- in Consul, the JWT auth method `nomad-workloads` pointed at Nomad's JWKS,
  with binding rules;
- in Vault, the JWT auth method at `nomad_vault_jwt_auth_path`, its roles and
  the policies they grant.

The agent's own Consul token has to exist before Nomad starts. Consul objects
are not this role's to create, so the playbook creates it, between the Consul
and Nomad roles, with `community.general.consul_policy` and
`community.general.consul_token`. The policy Nomad documents for agents:

```hcl
agent_prefix "" { policy = "read" }
node_prefix "" { policy = "write" }
service_prefix "" { policy = "write" }
```

### Tested

The `stack` scenario runs Consul, Vault and Nomad from this collection on one
node, wired the way a playbook would. It checks that Nomad registers itself in
Consul with that token, then sets up the Consul and Vault side as Terraform
would and runs a job whose service lands in Consul and whose template reads a
Consul key and a Vault secret with the job's own identity.

Consul service mesh is not covered. It needs the gRPC TLS port and the
`mesh` and `acl` permissions for servers, and there is no test for it.

## Variables

The full list is in `meta/argument_specs.yml`. The ones you will touch:

| Variable | Default | Purpose |
|---|---|---|
| `nomad_bind_address` | required | Address to bind and advertise |
| `nomad_server`, `nomad_client` | `true`, `true` | What this node runs |
| `nomad_bootstrap_expect` | `1` | Servers needed before a leader is elected |
| `nomad_retry_join` | `[]` | Servers to join |
| `nomad_region`, `nomad_datacenter` | `global`, `dc1` | Placement |
| `nomad_version` | `2.0.7` | Exact version |
| `nomad_consul_address` | `""` | Consul agent, `host:port`; empty is off |
| `nomad_consul_ca_cert`, `nomad_consul_token` | `""` | Consul CA and agent token |
| `nomad_consul_workload_identity` | `true` | Sign identities for Consul; off for a Consul without ACLs |
| `nomad_vault_address` | `""` | Vault URL; empty is off |
| `nomad_vault_ca_cert` | `""` | Vault CA |
| `nomad_vault_jwt_auth_path` | `jwt-nomad` | Where Vault accepts Nomad's identities |
| `nomad_extra_config` | `{}` | Merged into the rendered config |

## Not in this role yet

- Consul service mesh, see above.
- Task drivers beyond what ships in the binary. The client runs as root and
  fingerprints whatever the host has; installing Docker is not this role's
  job.
- Gossip key rotation.

## Notes

- Changing `nomad_version` replaces the binary and restarts the agent.
- The agent runs as root, as a Nomad client must.
