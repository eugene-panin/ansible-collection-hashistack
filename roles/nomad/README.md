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
        nomad_gossip_keys:
          - "{{ vault_nomad_gossip_key }}"
```

## Secrets

| Secret | Given as | Minted when not given |
|---|---|---|
| CA certificate and key | `nomad_pki_ca_cert`, `nomad_pki_ca_key` | into `nomad_pki_dir` on the controller |
| Bootstrap token | `nomad_acl_bootstrap_token` | into `nomad_acl_token_path` on the controller |
| Gossip keys | `nomad_network_interface` | `""` | Interface job ports land on by default |
| `nomad_host_networks` | `[]` | Named networks a job can ask for, such as a public one |
| `nomad_gossip_keys` | one, on the first server, shared with the rest |

The bootstrap token is minted before Nomad sees it and passed as the bootstrap
secret, so no secret depends on parsing a reply. Each run checks that the
token it holds is the cluster's management token and fails if it is not.

## Rotating the gossip key

`nomad_gossip_keys` is the whole keyring, primary first, and every run
converges the servers to it through the agent API with the `nomad_keyring`
module. A rotation is two runs:

1. `[new, old]`: `new` is installed on every server and becomes the primary,
   `old` is still accepted.
2. `[new]`: `old` is removed.

Nomad's API does not say which key is primary, so the module reads it from
`server/serf.keyring` in the data directory, where the primary comes first.
Once that file exists, Nomad ignores the key in its configuration; the role
still renders the primary there, for a server joining later, but does not
restart the agent when that key is all that changed. The `rotation` scenario
checks the agent was not restarted.

The `rotation` scenario runs both halves, checks the keyring and the primary
after the first, and after the second restarts the agent and checks that only
the new key is left.

## What it listens on

API and UI on 4646, HTTPS only. RPC between agents is TLS with server
hostname verification; the HTTP API does not ask for a client certificate, so
a browser can open the UI. Every request needs an ACL token: an anonymous one
gets 403.

The certificate names `server.<region>.nomad` and `client.<region>.nomad` as
the node's roles require, and is issued by the `tls_certificate` role: the key
is generated on the node, the controller signs it.

## Which address job ports land on

Left alone, a Nomad client gives job ports the address of the interface with
the default route, which on a server is the public one, and Docker publishes
them there past ufw. `nomad_network_interface` moves that default to a
private interface, such as WireGuard's. A job that should be public, such as
a reverse proxy or a mail server, asks for a named host network instead:

```yaml
nomad_network_interface: wg0
nomad_host_networks:
  - public:
      interface: eth0
```

```hcl
network {
  port "https" {
    static       = 443
    host_network = "public"
  }
}
```

Only a job that names `public` gets a port on eth0. The `networks` scenario
gives the node a private interface next to eth0, runs one group without a
host network and one with `public`, checks each got its port on the address
it should, and reaches the public one there.

## Bridge networking

`nomad_cni: true` installs the CNI reference plugins on a client, from their
GitHub release checked against its published checksum, into
`/opt/cni/<version>` behind a `/opt/cni/bin` link, and makes bridged traffic
pass through iptables. Jobs with `network { mode = "bridge" }` need it, and
so does Consul service mesh. Changing `nomad_cni_version` switches the link
and restarts the agent; the `default` scenario upgrades it and checks the
version Nomad itself reports.

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

### Service mesh

Envoy sidecars take their configuration from Consul over gRPC. Nomad finds
Consul's gRPC TLS port by itself, on the host of `nomad_consul_address`, but
does not fall back to `ca_file` to verify it, so the role sets `grpc_ca_file`
to the same CA from `nomad_consul_ca_cert`. What is left to add is bridge
networking on clients: `nomad_cni: true`. The `mesh` scenario fails without
`grpc_ca_file`, and passes without any `grpc_address`.

The `consul` role in this collection already has Connect and the gRPC TLS
port on, and the agent policy above is enough for sidecars; what a mesh also
needs inside Consul, intentions and the auth method, is Terraform's.

Nomad pulls Envoy from Docker Hub by default. To take it from elsewhere, set
the client's `meta.connect.sidecar_image` through `nomad_extra_config`.

The `mesh` scenario runs Consul, Docker from `eugene_panin.base` and Nomad
with CNI on one node, starts two groups in bridge mode with sidecars, and
checks that one reaches the other through the mesh, and that the port the
bridge publishes answers on the node.

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
| `nomad_gossip_keys` | `[]` | Gossip keyring, primary first; empty generates one |
| `nomad_cni`, `nomad_cni_version` | `false`, `1.9.1` | CNI plugins for bridge networking |
| `nomad_consul_address` | `""` | Consul agent, `host:port`; empty is off |
| `nomad_consul_ca_cert`, `nomad_consul_token` | `""` | Consul CA and agent token |
| `nomad_consul_workload_identity` | `true` | Sign identities for Consul; off for a Consul without ACLs |
| `nomad_vault_address` | `""` | Vault URL; empty is off |
| `nomad_vault_ca_cert` | `""` | Vault CA |
| `nomad_vault_jwt_auth_path` | `jwt-nomad` | Where Vault accepts Nomad's identities |
| `nomad_extra_config` | `{}` | Merged into the rendered config |

## Not in this role yet

- Task drivers beyond what ships in the binary. The client runs as root and
  fingerprints whatever the host has; installing Docker is not this role's
  job, `eugene_panin.base.docker` does it.

## Notes

- Changing `nomad_version` replaces the binary and restarts the agent.
- The agent runs as root, as a Nomad client must.
