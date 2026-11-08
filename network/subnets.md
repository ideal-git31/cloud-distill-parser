# Task 5: Subnetting and NACL

Address block: `10.20.0.0/16`. Subnets are allocated from the largest requirement to the smallest,
each placed right after the previous one, using the smallest prefix that fits.

## Method
For `H` hosts we need `2^b - 2 >= H` (network and broadcast addresses are not usable), so
`b = ceil(log2(H + 2))` host bits and `prefix = 32 - b`.

| Subnet | Hosts needed | H + 2 | Host bits b | 2^b - 2 usable | Prefix |
|---|---|---|---|---|---|
| app | 1,000 | 1,002 | 10 (2^10 = 1,024) | 1,022 | /22 |
| public | 250 | 252 | 8 (2^8 = 256) | 254 | /24 |
| data | 100 | 102 | 7 (2^7 = 128) | 126 | /25 |
| management | 20 | 22 | 5 (2^5 = 32) | 30 | /27 |

(9 host bits would give only 510 usable addresses for `app`, 7 bits only 126 for `public`, 6 bits only 62 for
`data`, 4 bits only 14 for `management`, so these are the smallest prefixes that fit.)

## Allocation
| Subnet | Network address | Prefix | Usable host range | Broadcast | Usable hosts |
|---|---|---|---|---|---|
| app | 10.20.0.0 | /22 | 10.20.0.1 - 10.20.3.254 | 10.20.3.255 | 1,022 |
| public | 10.20.4.0 | /24 | 10.20.4.1 - 10.20.4.254 | 10.20.4.255 | 254 |
| data | 10.20.5.0 | /25 | 10.20.5.1 - 10.20.5.126 | 10.20.5.127 | 126 |
| management | 10.20.5.128 | /27 | 10.20.5.129 - 10.20.5.158 | 10.20.5.159 | 30 |

Working: app starts at 10.20.0.0 and spans 1,024 addresses, so it ends at 10.20.3.255. public starts at
10.20.4.0 and spans 256 addresses (ends 10.20.4.255). data starts at 10.20.5.0 and spans 128 addresses
(ends 10.20.5.127). management starts at 10.20.5.128 and spans 32 addresses (ends 10.20.5.159).
`tests/test_network.py` recomputes this table with Python's `ipaddress` module.

## NACL for the public subnet (`network/nacl.json`)
| Direction | Rule | Match | Action | Why |
|---|---|---|---|---|
| inbound | 100 | all from 198.51.100.0/24 | deny | abusive range, lowest number so it wins over the web allows |
| inbound | 110 | tcp 80 from 0.0.0.0/0 | allow | HTTP |
| inbound | 120 | tcp 443 from 0.0.0.0/0 | allow | HTTPS |
| inbound | 130 | tcp 22 from 10.20.5.128/27 | allow | SSH only from the management subnet |
| inbound | 140 | tcp 1024-65535 from 10.20.0.0/22 | allow | replies from the app subnet to the load balancer's ephemeral ports |
| outbound | 100 | tcp 8000 to 10.20.0.0/22 | allow | load balancer to the service in the app subnet |
| outbound | 110 | tcp 1024-65535 to 0.0.0.0/0 | allow | replies back to clients (their ephemeral ports) |

Everything else is denied by the implicit default deny.

Check: `python tools/nacl_sim.py network/nacl.json network/packets_sample.jsonl --check`

## Why replies need their own rules, and why rule order matters
A NACL is **stateless**: it does not remember that an inbound request was allowed, so the reply is a brand-new
packet that is checked on its own against the outbound rules (and the replies the load balancer receives from the
app subnet against the inbound rules). Without rule 110 clients would send requests but never get an answer back;
without rule 140 the app subnet's replies would be dropped. Clients and the load balancer use ephemeral ports
1024-65535 for their side of the connection, so the reply rules open that range.

Rules are evaluated from the lowest number upward and the **first match decides**. The deny for 198.51.100.0/24
only works if its number (100) is lower than the allow rules for TCP 80/443 (110/120). If it were numbered higher,
a packet from 198.51.100.9 to port 443 would match the allow rule first and be let in.
