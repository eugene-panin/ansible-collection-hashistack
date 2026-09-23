# hashicorp_release

Installs one HashiCorp binary from releases.hashicorp.com. The `consul`,
`nomad` and `vault` roles call it; it works the same for any product that
ships as `<product>_<version>_linux_<arch>.zip` next to a `SHA256SUMS` file.

```yaml
- ansible.builtin.include_role:
    name: eugene_panin.hashistack.hashicorp_release
  vars:
    hashicorp_release_product: consul
    hashicorp_release_version: 1.20.2
```

## What it checks

- The archive is verified against the `SHA256SUMS` published for that exact
  version, over HTTPS, before it is unpacked.
- The installed version is read from `<product> version` and compared with
  the one asked for. A binary that merely exists is not taken as proof, so
  changing `hashicorp_release_version` upgrades or downgrades in place, and a
  converged host costs one command per run.

It does not verify the GPG signature on `SHA256SUMS`. The checksum file is
trusted because it comes from releases.hashicorp.com over TLS. If you mirror
releases, the trust moves to your mirror.

## Variables

| Variable | Default | Purpose |
|---|---|---|
| `hashicorp_release_product` | required | Product name as it appears in the release URL |
| `hashicorp_release_version` | required | Exact version, no leading `v` |
| `hashicorp_release_bin_dir` | `/usr/local/bin` | Where the binary is unpacked |
| `hashicorp_release_download_dir` | `/var/cache/hashicorp` | Where the archive is kept |
| `hashicorp_release_base_url` | `https://releases.hashicorp.com` | Mirror, for hosts that cannot reach HashiCorp |

Supported architectures: `x86_64`, `aarch64`, `armv7l`. `unzip` must be on
the host; the product roles install it.

## Notes

- It only replaces the binary. It sets `hashicorp_release_changed` to true
  when the installed version differs from the one asked for, before it
  downloads anything, so the calling role can restart its service on it and
  `--check` reports that restart too.
- In check mode on a host without the product, nothing is downloaded; the
  run reports the download directory it would create.
