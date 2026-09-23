# consul

Runs a Consul agent, server or client, with gossip encryption, TLS and ACLs
on from the first run. A single server is the degenerate case of a cluster:
the same variables describe both, and adding nodes later means extending the
inventory rather than rewriting the role.

```yaml
- name: Consul
  hosts: consul_servers
  become: true
  roles:
    - role: eugene_panin.hashistack.consul
      vars:
        consul_server: true
        consul_bootstrap_expect: 1
        consul_bind_address: 10.77.0.1
        consul_pki_dir: "{{ playbook_dir }}/../pki/consul"
        consul_acl_token_path: "{{ playbook_dir }}/../secrets/consul/bootstrap.token"
```

## What ends up where

On the controller, under `consul_pki_dir`:

- the CA certificate and its private key. The CA key never leaves the
  controller; nodes only ever receive certificates it signed.
- one key and certificate per agent.

On the controller, next to `consul_acl_token_path`:

- the bootstrap token, which is a full management token.
- the agent token, which every agent in the datacenter is given.

Both token files are plain text. Keep them wherever you keep private keys, and
out of git.

On each node:

- the CA, the agent certificate and key in `/etc/consul.d/tls/`.
- the gossip key in `/etc/consul.d/gossip.key`.
- `consul.json`, rendered from variables. Anything not modelled by a variable
  goes in `consul_extra_config`, which is merged in last.

## Bootstrapping

The first host in the play is special for two things, and only on the first
run: it generates the gossip key, and it bootstraps the ACL system. Both
results are shared with the other hosts in the same play. On later runs the
key is read from that host and the token from the controller, so the order of
hosts stops mattering once the cluster exists.

ACL bootstrap works exactly once per cluster. If the token file on the
controller is lost, the role cannot recover it; Consul's reset procedure is
manual by design.

## What the agent is exposed on

- The HTTP API is HTTPS only, on 8501. Plain 8500 is switched off.
- `client_addr` defaults to loopback plus the bind address, so the UI and API
  are reachable over whatever network the bind address is on and nowhere else.
- Incoming TLS is verified for RPC between agents, not for the HTTP API, so a
  browser can open the UI without a client certificate. The API still needs a
  token.

## Variables

The full list with types is in `meta/argument_specs.yml`. The ones you will
touch:

| Variable | Default | Purpose |
|---|---|---|
| `consul_server` | `false` | Server or client |
| `consul_bootstrap_expect` | `1` | Servers needed before a leader is elected |
| `consul_bind_address` | required | Address to bind and advertise |
| `consul_retry_join` | `[]` | Other agents to join |
| `consul_datacenter` | `dc1` | Datacenter name |
| `consul_version` | `1.20.2` | Exact version |
| `consul_pki_dir` | required with TLS | CA and certificates, on the controller |
| `consul_acl_token_path` | required with ACLs | Bootstrap token file, on the controller |
| `consul_extra_config` | `{}` | Merged into the rendered config |

## Notes

- `consul_bind_address` has no default on purpose. Binding to a private or
  tunnel address is what keeps the cluster off the internet, and guessing one
  is how clusters end up on it.
- With `consul_acl_default_policy: deny`, an anonymous catalog read returns an
  empty list, not an error. That is Consul filtering by ACL, not the node being
  missing.
- Certificates are issued for 825 days and are not rotated by the role.
  Delete the agent certificate on the controller and re-run to reissue.
