#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: nomad_keyring
short_description: Converge a Nomad server gossip keyring to a declared list of keys
version_added: "0.3.0"
description:
  - Reads the server gossip keyring through the Nomad agent API and brings it
    to the declared state. Keys in O(keys) that are missing, or present on only
    some servers, are installed. The first key becomes the primary. Keys the
    servers have that are not in O(keys) are removed.
  - The Nomad API does not report which key is primary. The module reads it
    from the keyring file of the server it runs on, O(keyring_file), where the
    primary key is always the first entry.
  - Rotation is two runs. Declare C([new, old]) to install the new key and make
    it primary while old traffic is still accepted, then C([new]) to drop the
    old one.
  - The API applies each change to every live server, so the module runs once
    per region, on any server.
options:
  keys:
    description:
      - Gossip keys, base64 as produced by C(nomad operator gossip keyring generate).
        The first one is the primary.
    type: list
    elements: str
    required: true
  url:
    description: Address of the Nomad HTTP API of a server.
    type: str
    default: https://127.0.0.1:4646
  token:
    description: ACL token with C(agent:write).
    type: str
  ca_path:
    description: CA bundle used to verify the agent's certificate.
    type: str
  validate_certs:
    description: Verify the agent's TLS certificate.
    type: bool
    default: true
  keyring_file:
    description: The server's keyring file, C(server/serf.keyring) under its data directory.
    type: path
    default: /opt/nomad/server/serf.keyring
attributes:
  check_mode:
    description: Can run in check mode and report what would change.
    support: full
  diff_mode:
    description: Reports each key installed, made primary or removed, by a hash of the key.
    support: full
author:
  - Evgenii Panin (@eugene-panin)
"""

EXAMPLES = r"""
- name: Converge the keyring
  eugene_panin.hashistack.nomad_keyring:
    keys:
      - "{{ vault_nomad_gossip_key }}"
    token: "{{ nomad_management_token }}"
    ca_path: /etc/nomad.d/tls/ca.pem

- name: First half of a rotation, new key primary, old still accepted
  eugene_panin.hashistack.nomad_keyring:
    keys:
      - "{{ vault_nomad_gossip_key_new }}"
      - "{{ vault_nomad_gossip_key_old }}"
    token: "{{ nomad_management_token }}"
    ca_path: /etc/nomad.d/tls/ca.pem
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

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible_collections.eugene_panin.hashistack.plugins.module_utils.keyring import (
    diff_text,
    plan,
    validate_keys,
)


class KeyringClient(object):
    def __init__(self, module):
        self.module = module
        self.endpoint = module.params["url"].rstrip("/") + "/v1/agent/keyring/"

    def _call(self, op, key=None):
        headers = {"Content-Type": "application/json"}
        if self.module.params["token"]:
            headers["X-Nomad-Token"] = self.module.params["token"]
        method = "GET" if key is None else "POST"
        body = json.dumps({"Key": key}) if key is not None else None
        response, info = fetch_url(
            self.module,
            self.endpoint + op,
            data=body,
            headers=headers,
            method=method,
            ca_path=self.module.params["ca_path"],
        )
        status = info.get("status", -1)
        if status != 200:
            self.module.fail_json(
                msg="%s %s returned %s: %s" % (method, self.endpoint + op, status, info.get("body") or info.get("msg")),
            )
        payload = response.read() if response else b""
        return json.loads(payload) if payload else None

    def pools(self, primary):
        listing = self._call("list") or {}
        nodes = listing.get("NumNodes", 0)
        return [dict(
            NumNodes=nodes,
            Keys=listing.get("Keys") or {},
            PrimaryKeys={primary: nodes} if primary else {},
        )]

    def install(self, key):
        self._call("install", key)

    def use(self, key):
        self._call("use", key)

    def remove(self, key):
        self._call("remove", key)


def local_primary(module):
    path = module.params["keyring_file"]
    try:
        with open(path) as handle:
            keys = json.load(handle)
    except (IOError, OSError, ValueError) as exc:
        module.fail_json(msg="cannot read the keyring file %s: %s" % (path, exc))
    if not isinstance(keys, list) or not keys:
        module.fail_json(msg="the keyring file %s holds no keys" % path)
    return keys[0]


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            keys=dict(type="list", elements="str", required=True, no_log=True),
            url=dict(type="str", default="https://127.0.0.1:4646"),
            token=dict(type="str", no_log=True),
            ca_path=dict(type="str"),
            validate_certs=dict(type="bool", default=True),
            keyring_file=dict(type="path", default="/opt/nomad/server/serf.keyring"),
        ),
        supports_check_mode=True,
    )

    wanted = validate_keys(module)
    client = KeyringClient(module)
    to_install, switch_primary, to_remove = plan(client.pools(local_primary(module)), wanted)
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
            after=diff_text(to_install, wanted[0], switch_primary, to_remove),
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
