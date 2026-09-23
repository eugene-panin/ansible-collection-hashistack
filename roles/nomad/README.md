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
| `nomad_extra_config` | `{}` | Merged into the rendered config |

## Not in this role yet

- Consul and Vault integration. Both need workload identity configured on
  the Consul and Vault side, and there is no test for it yet. Until there is,
  it is not claimed; `nomad_extra_config` takes a `consul` or `vault` block if
  you wire it yourself.
- Task drivers beyond what ships in the binary. The client runs as root and
  fingerprints whatever the host has; installing Docker is not this role's
  job.
- Gossip key rotation.

## Notes

- Changing `nomad_version` replaces the binary and restarts the agent.
- The agent runs as root, as a Nomad client must.
