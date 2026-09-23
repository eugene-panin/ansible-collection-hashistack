# tls_certificate

Gives a node a TLS certificate signed by a CA that stays with whoever runs
Ansible. The `consul`, `vault` and `nomad` roles use it; it has nothing
specific to any of them.

```yaml
- ansible.builtin.include_role:
    name: eugene_panin.hashistack.tls_certificate
  vars:
    tls_certificate_ca_cert: "{{ vault_internal_ca_cert }}"
    tls_certificate_ca_key: "{{ vault_internal_ca_key }}"
    tls_certificate_dir: /etc/myservice/tls
    tls_certificate_owner: myservice
    tls_certificate_group: myservice
    tls_certificate_common_name: myservice.internal
    tls_certificate_subject_alt_names:
      - DNS:myservice.internal
      - IP:10.0.0.5
```

## How the certificate is made

1. The private key is generated on the node and stays there.
2. A signing request is built from it on the node.
3. The controller signs it with the CA.
4. The certificate and the CA certificate are installed on the node.

The node's current certificate is passed back into the signing step, so a
certificate that still matches the key, the CA and the requested names is
kept as is and the run reports no change.

## Where the CA comes from

Give `tls_certificate_ca_cert` and `tls_certificate_ca_key` from any secret
store, and nothing is written on the controller. Leave them empty and set
`tls_certificate_ca_dir`, and a CA is generated there once and reused.

## What the calling role gets back

- `tls_certificate_changed` is true when the key or an installed certificate
  changed. Restart the service on it.
- `tls_certificate_paths` holds `ca`, `cert` and `key`, the paths on the node.

## Notes

- Keys are ECDSA P-256.
- `python3-cryptography` is installed on the node; the key and the signing
  request are made there.
- Certificates are not renewed ahead of expiry. Delete the certificate on the
  node to have a new one issued.
