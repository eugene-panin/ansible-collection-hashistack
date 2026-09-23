#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: consul_keyring
short_description: Converge a Consul gossip keyring to a declared list of keys
version_added: "0.1.0"
description:
  - Reads the gossip keyring through the Consul operator API and brings it to
    the declared state. Keys in O(keys) that are missing, or present on only
    some nodes, are installed. The first key becomes the primary. Keys the
    cluster has that are not in O(keys) are removed.
  - Rotation is two runs. Declare C([new, old]) to install the new key and make
    it primary while old traffic is still accepted, then C([new]) to drop the
    old one.
  - The API applies each change to every live member, so the module runs once
    per cluster, against any agent.
options:
  keys:
    description:
      - Gossip keys, base64 as produced by C(consul keygen). The first one is
        the primary.
    type: list
    elements: str
    required: true
    no_log: true
  url:
    description: Address of the Consul HTTP API.
    type: str
    default: https://127.0.0.1:8501
  token:
    description: ACL token with C(keyring:write).
    type: str
    no_log: true
  ca_path:
    description: CA bundle used to verify the agent's certificate.
    type: str
  validate_certs:
    description: Verify the agent's TLS certificate.
    type: bool
    default: true
attributes:
  check_mode:
    support: full
  diff_mode:
    support: full
author:
  - Evgenii Panin (@eugene-panin)
"""

EXAMPLES = r"""
- name: Converge the keyring
  eugene_panin.hashistack.consul_keyring:
    keys:
      - "{{ vault_consul_gossip_key }}"
    token: "{{ consul_management_token }}"
    ca_path: /etc/consul.d/tls/ca.pem

- name: First half of a rotation, new key primary, old still accepted
  eugene_panin.hashistack.consul_keyring:
    keys:
      - "{{ vault_consul_gossip_key_new }}"
      - "{{ vault_consul_gossip_key_old }}"
    token: "{{ consul_management_token }}"
    ca_path: /etc/consul.d/tls/ca.pem
"""

RETURN = r"""
installed:
  description: How many keys were installed or reinstalled.
  type: int
  returned: always
primary_changed:
  description: Whether the primary key was switched.
  type: bool
  returned: always
removed:
  description: How many keys were removed.
  type: int
  returned: always
"""

import hashlib
import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url


class KeyringClient(object):
    def __init__(self, module):
        self.module = module
        self.endpoint = module.params["url"].rstrip("/") + "/v1/operator/keyring"

    def _call(self, method, key=None):
        headers = {"Content-Type": "application/json"}
        if self.module.params["token"]:
            headers["X-Consul-Token"] = self.module.params["token"]
        body = json.dumps({"Key": key}) if key is not None else None
        response, info = fetch_url(
            self.module,
            self.endpoint,
            data=body,
            headers=headers,
            method=method,
            ca_path=self.module.params["ca_path"],
        )
        status = info.get("status", -1)
        if status != 200:
            self.module.fail_json(
                msg="%s %s returned %s: %s" % (method, self.endpoint, status, info.get("body") or info.get("msg")),
            )
        payload = response.read() if response else b""
        return json.loads(payload) if payload else None

    def pools(self):
        return self._call("GET") or []

    def install(self, key):
        self._call("POST", key)

    def use(self, key):
        self._call("PUT", key)

    def remove(self, key):
        self._call("DELETE", key)


def plan(pools, wanted):
    primary = wanted[0]
    everywhere = set(wanted)
    present = set()
    for pool in pools:
        nodes = pool.get("NumNodes", 0)
        keys = pool.get("Keys") or {}
        present.update(keys)
        everywhere &= set(k for k, count in keys.items() if count == nodes)

    to_install = [k for k in wanted if k not in everywhere]
    primary_ok = all(
        (pool.get("PrimaryKeys") or {}).get(primary, 0) == pool.get("NumNodes", 0)
        for pool in pools
    )
    to_remove = sorted(k for k in present if k not in wanted)
    return to_install, not primary_ok, to_remove


def fingerprint(key):
    return "sha256:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            keys=dict(type="list", elements="str", required=True, no_log=True),
            url=dict(type="str", default="https://127.0.0.1:8501"),
            token=dict(type="str", no_log=True),
            ca_path=dict(type="str"),
            validate_certs=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )

    wanted = [k.strip() for k in module.params["keys"] if k and k.strip()]
    if not wanted:
        module.fail_json(msg="keys must contain at least one key")
    if len(set(wanted)) != len(wanted):
        module.fail_json(msg="keys must not repeat")

    client = KeyringClient(module)
    to_install, switch_primary, to_remove = plan(client.pools(), wanted)
    changed = bool(to_install or switch_primary or to_remove)

    result = dict(
        changed=changed,
        installed=len(to_install),
        primary_changed=switch_primary,
        removed=len(to_remove),
    )
    if module._diff:
        result["diff"] = dict(
            before="",
            after="".join(
                ["install %s\n" % fingerprint(k) for k in to_install]
                + (["use %s\n" % fingerprint(wanted[0])] if switch_primary else [])
                + ["remove %s\n" % fingerprint(k) for k in to_remove]
            ),
        )

    if module.check_mode or not changed:
        module.exit_json(**result)

    for key in to_install:
        client.install(key)
    if switch_primary:
        client.use(wanted[0])
    for key in to_remove:
        client.remove(key)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
