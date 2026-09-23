# vault

Runs Vault on its integrated raft storage, TLS only, bound to one address.
Initialises it once, and unseals it whenever a run finds it sealed.

```yaml
- name: Vault
  hosts: vault_servers
  become: true
  roles:
    - role: eugene_panin.hashistack.vault
      vars:
        vault_bind_address: 10.77.0.1
        vault_pki_ca_cert: "{{ lookup('ansible.builtin.file', 'files/ca.pem') }}"
        vault_pki_ca_key: "{{ vault_internal_ca_key }}"
        vault_init_output_path: "{{ playbook_dir }}/../secrets/vault-init.json"
```

## Initialising

The first run that finds Vault uninitialised initialises it and writes the
result, the unseal keys and the root token, to `vault_init_output_path` on the
controller, mode 0600. Vault generates these; they cannot be prepared ahead.

Move them into your secret store after that first run, give the keys back as
`vault_unseal_keys`, and delete the file. Anyone holding the file holds the
cluster.

If Vault is uninitialised but the file already exists, the role stops instead
of initialising. The file would belong to another cluster, and overwriting it
would lose that cluster's keys.

## Sealing

Vault seals itself every time it starts: after a restart, an upgrade, a
reboot. The role treats unsealed as the desired state, so any run unseals it
with the keys it has. Nothing unseals it between runs. A reboot leaves Vault
sealed until someone runs the play again, or until you configure auto-unseal
with a KMS or another Vault through `vault_extra_config`.

The keys the role unseals with are the ones in the controller file or in
`vault_unseal_keys`, as many as the threshold asks for. Keeping them in the
same place as the playbook is convenient and trades away the point of
splitting them into shares. Decide whether that is acceptable for your
cluster.

## Where it listens

One listener on `vault_bind_address`, API on 8200 and cluster traffic on 8201,
both TLS. There is no loopback listener and no plain HTTP. Point the CLI at
it with `VAULT_ADDR=https://<bind address>:8200` and
`VAULT_CACERT=/etc/vault.d/tls/ca.pem`.

The certificate is issued by the `tls_certificate` role: the key is generated
on the node, the controller signs it. It carries
`vault.service.consul` and `active.vault.service.consul`, so registering Vault
in Consul needs no new certificate.

## Variables

The full list is in `meta/argument_specs.yml`. The ones you will touch:

| Variable | Default | Purpose |
|---|---|---|
| `vault_bind_address` | required | Address to bind and advertise |
| `vault_version` | `2.1.1` | Exact version |
| `vault_retry_join` | `[]` | Other nodes' API addresses, for a cluster |
| `vault_pki_ca_cert`, `vault_pki_ca_key` | `""` | The CA, as values |
| `vault_pki_dir` | `""` | Where a CA is generated when not given |
| `vault_init_output_path` | `""` | Where the init result is written |
| `vault_unseal_keys` | `[]` | Unseal keys, as values |
| `vault_init_key_shares`, `vault_init_key_threshold` | `5`, `3` | Shamir split |
| `vault_extra_config` | `{}` | Merged into the rendered config |

## Notes

- `disable_mlock` is on, as HashiCorp recommends for integrated storage.
- Changing `vault_version` replaces the binary and restarts Vault, which
  seals it; the same run unseals it again.
- Registering in Consul, audit devices, auth methods and secret engines are
  configuration of a running Vault, not of the server, and are not in this
  role.
