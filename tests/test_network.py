import ipaddress
import json
import math
from pathlib import Path

from tools.nacl_sim import decide, load_rules

ROOT = Path(__file__).resolve().parent.parent


def allocate(reqs, start="10.20.0.0"):
    cur, out = int(ipaddress.ip_address(start)), {}
    for name, hosts in reqs:
        prefix = 32 - math.ceil(math.log2(hosts + 2))
        net = ipaddress.ip_network((cur, prefix))
        out[name] = net
        cur = int(net.broadcast_address) + 1
    return out


def test_subnet_allocation_matches_the_table_in_subnets_md():
    nets = allocate([("app", 1000), ("public", 250), ("data", 100), ("management", 20)])
    assert {k: str(v) for k, v in nets.items()} == {
        "app": "10.20.0.0/22", "public": "10.20.4.0/24", "data": "10.20.5.0/25", "management": "10.20.5.128/27"}
    assert [n.num_addresses - 2 for n in nets.values()] == [1022, 254, 126, 30]


def test_nacl_matches_all_sample_packets_and_the_deny_rule_wins():
    rules = load_rules(ROOT / "network" / "nacl.json")
    for line in (ROOT / "network" / "packets_sample.jsonl").read_text().splitlines():
        p = json.loads(line)
        assert decide(rules, p)[0] == p["expected"], p["id"]
    abusive = {"direction": "inbound", "protocol": "tcp", "port": 80, "address": "198.51.100.200"}
    assert decide(rules, abusive) == ("deny", 100)
    ssh_from_mgmt = {"direction": "inbound", "protocol": "tcp", "port": 22, "address": "10.20.5.130"}
    assert decide(rules, ssh_from_mgmt)[0] == "allow"
