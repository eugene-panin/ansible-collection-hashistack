# consul_dns

Makes Consul names resolve on the host, and optionally for the clients behind
an extra address such as the WireGuard one, through systemd-resolved. Queries
for the Consul domains go to Consul's DNS interface; everything else goes
where it went before.

```yaml
- name: Consul DNS
  hosts: all
  become: true
  roles:
    - role: eugene_panin.hashistack.consul
      vars:
        consul_alt_domain: int.example.com
    - role: eugene_panin.hashistack.consul_dns
      vars:
        consul_dns_domains:
          - consul
          - int.example.com
        consul_dns_listen_addresses:
          - 10.77.0.1
```

`web.service.consul` and `web.service.int.example.com` then resolve on the
host and for anyone who uses 10.77.0.1 as their DNS server, such as WireGuard
clients given it through `wireguard_client_dns`.

## How

A drop-in in `/etc/systemd/resolved.conf.d` names Consul as a DNS server and
the Consul domains as routing-only domains (`~consul`). Names outside them
keep going to the servers the interfaces have. Each extra address becomes a
`DNSStubListenerExtra`; the address does not have to exist when resolved
starts, so a WireGuard interface that comes up later is fine.

## What the host needs

systemd-resolved has to be the host's resolver already, and know the upstream
servers on an interface, as on a stock Ubuntu server, where netplan hands them
over. The role checks this first and stops without changing anything if it
does not hold: it does not install resolved or take DNS over. On a host where
resolved only mirrors `/etc/resolv.conf`, as on a stock Debian with ifupdown,
the Consul server would replace the upstream ones and every other name would
stop resolving. On Debian, move the network to systemd-networkd or
NetworkManager first.

With ACLs on and `default_policy` deny, Consul answers DNS only with a DNS
token; the `consul` role creates one when it can mint it or is given one.

## Tested

The scenario prepares a host whose resolved gets its upstream server on the
interface, as networkd would. It runs the `consul` role with ACLs and an
`alt_domain`, then this role with an extra address that is brought up only
after resolved has started. After the idempotence and check runs, it takes
the upstream server away from resolved and checks that the role refuses and
leaves its drop-in untouched. It resolves Consul by both domains on the stub address and on the
extra one, checks that resolved holds the Consul domains as routing-only, and
that a public name still resolves through the interface's own DNS server.
Without the routing-only domains names still resolve, since resolved asks
Consul and the interface's server alike, but every query of the host then
reaches Consul; that is what the routing check catches.

## What it does not do

- Containers. Docker gives containers the host's upstream servers, not
  resolved's stub on 127.0.0.53, so a container does not see Consul names
  through this role.
- No firewall. Port 53 on an extra address is reachable by anyone who can
  reach that address.

## Variables

| Variable | Default | Purpose |
|---|---|---|
| `consul_dns_server` | `127.0.0.1:8600` | Consul DNS interface |
| `consul_dns_domains` | `[consul]` | Domains routed to Consul |
| `consul_dns_listen_addresses` | `[]` | Extra addresses resolved answers on, port 53 |
