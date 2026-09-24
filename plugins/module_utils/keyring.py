from __future__ import absolute_import, division, print_function

__metaclass__ = type

import hashlib


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


def diff_text(to_install, primary, switch_primary, to_remove):
    return "".join(
        ["install %s\n" % fingerprint(k) for k in to_install]
        + (["use %s\n" % fingerprint(primary)] if switch_primary else [])
        + ["remove %s\n" % fingerprint(k) for k in to_remove]
    )


def validate_keys(module):
    wanted = [k.strip() for k in module.params["keys"] if k and k.strip()]
    if not wanted:
        module.fail_json(msg="keys must contain at least one key")
    if len(set(wanted)) != len(wanted):
        module.fail_json(msg="keys must not repeat")
    return wanted
