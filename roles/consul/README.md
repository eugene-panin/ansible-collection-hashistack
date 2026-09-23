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

## Secrets: given or minted

Every secret the role needs can be handed to it as a value, read from wherever
your inventory keeps secrets: `ansible-vault`, SOPS, HashiCorp Vault through
`community.hashi_vault`, a password manager lookup. The role has no opinion on
the store.

| Secret | Given as | Minted into, when not given |
|---|---|---|
| CA certificate and key | `consul_pki_ca_cert`, `consul_pki_ca_key` | `consul_pki_dir` |
| Bootstrap token | `consul_acl_bootstrap_token` | `consul_acl_token_path` |
| Agent token, per host | `consul_acl_agent_token` | next to `consul_acl_token_path` |
| Gossip keys | `consul_gossip_keys` | the nodes, see below |

Minting is there so a first deployment works with nothing prepared. Move the
secrets into a store before the cluster matters; nothing in the role changes
when you do.

One constraint on where the store lives: whatever Consul needs to start cannot
come from a Vault that runs on top of that Consul. Keep these outside the
stack they bootstrap.

## What ends up where

On the controller, under `consul_pki_dir`, when the CA is not given:

- the CA certificate and its private key.

Agent keys are generated on the nodes and never leave them. The node sends a
signing request, the controller signs it with the CA and sends the certificate
back.

On the controller, next to `consul_acl_token_path`:

- the bootstrap token, a full management token.
- one agent token per node, `<datacenter>-<node>-agent.token`.

The role mints these as UUIDs on the controller before Consul ever sees them,
then hands them to Consul: the bootstrap token as the bootstrap secret, each
agent token with that node's built-in node identity. Nothing is fished out of
Consul's replies, so a failed run can be repeated without losing a secret.
All of them are plain text. Keep them where you keep private keys, and out of
git.

On each node:

- the CA certificate, the agent certificate and the agent key in
  `/etc/consul.d/tls/`.
- the gossip key in `/etc/consul.d/gossip.key`, only when the role generated
  it (see below).
- `consul.json`, rendered from variables. Anything not modelled by a variable
  goes in `consul_extra_config`, which is merged in last.

## Gossip keys and rotation

`consul_gossip_keys` is the keyring you want, primary first. Each run reads
the cluster's keyring through the operator API and converges it: installs
what is missing, switches the primary, removes what is not listed. The work
is done by the `eugene_panin.hashistack.consul_keyring` module in this
collection, which supports check and diff mode.

Rotating is two runs:

```yaml
consul_gossip_keys:
  - "{{ vault_consul_gossip_key_new }}"
  - "{{ vault_consul_gossip_key_old }}"
```

then, once that has run everywhere:

```yaml
consul_gossip_keys:
  - "{{ vault_consul_gossip_key_new }}"
```

Between the two, every node encrypts with the new key and still accepts the
old one, so no node is ever left without a key in common with the rest.

Left empty, the first host in the play generates a key once and the others
receive it. That is convenient on day one and a trap on the day you need to
rotate, because the key only exists on the nodes. Generate one with
`consul keygen`, put it in a vault, and declare it before that day comes.

## Bootstrapping

The first host in the play bootstraps the ACL system, and in generated-key
mode it also generates the gossip key. On later runs the tokens come from the
controller and the key from the declared list or the nodes, so host order
stops mattering once the cluster exists.

ACL bootstrap works once per cluster. If the bootstrap token file on the
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
| `consul_pki_ca_cert`, `consul_pki_ca_key` | `""` | The CA, as values |
| `consul_pki_dir` | `""` | Where the CA is minted when not given |
| `consul_acl_bootstrap_token` | `""` | Bootstrap token, as a value |
| `consul_acl_agent_token` | `""` | This host's agent token, as a value |
| `consul_acl_token_path` | `""` | Where tokens are minted when not given |
| `consul_gossip_keys` | `[]` | Keyring to converge to, primary first; empty generates one |
| `consul_extra_config` | `{}` | Merged into the rendered config |

## Notes

- `consul_bind_address` has no default on purpose. Binding to a private or
  tunnel address is what keeps the cluster off the internet, and guessing one
  is how clusters end up on it.
- With `consul_acl_default_policy: deny`, an anonymous catalog read returns an
  empty list, not an error. That is Consul filtering by ACL, not the node being
  missing.
- Agent certificates are issued for 825 days. The role reissues one when it
  no longer matches the node's key, the CA or the requested names; otherwise
  it keeps the one the node has. Delete it on the node to force a new one.
