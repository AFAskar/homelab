#!/usr/bin/env python3
"""Probe public Mindustry TCP/UDP allocations and reject public admin services.

UDP discovery follows ArcNetProvider.pingHost / NetworkIO.readServerData in
Anuken/Mindustry v160.7. A server response proves application traffic, not just
an open UDP socket. Run from an external client, independently of OCI routes.
"""
import concurrent.futures
import json
from pathlib import Path
import socket
import struct
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
nodes = json.loads(subprocess.check_output(
    ['terraform', '-chdir=' + str(root / 'terraform'), 'output', '-json', 'wings_instances']))


def probe(item):
    name, instance = item
    address = instance['public_ip']
    result = {'node': name, 'public_ip': address}
    try:
        with socket.create_connection((address, 25565), timeout=4):
            result['tcp_game'] = True
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.settimeout(4)
            udp.connect((address, 25565))
            result['client_source'] = udp.getsockname()[0]
            udp.send(bytes([254, 1]))
            response = udp.recv(512)
        offset = 0
        strings = []
        for _ in range(2):
            length = response[offset]
            offset += 1
            strings.append(response[offset:offset + length].decode('utf-8'))
            offset += length
        players, wave, version = struct.unpack_from('>iii', response, offset)
        result.update(server_name=strings[0], map=strings[1], players=players, wave=wave, version=version)
        result['udp_game'] = strings[0] == 'mindustry-' + name
    except (OSError, ValueError, IndexError, struct.error) as error:
        result['error'] = str(error)
    result['public_admin_ports'] = []
    for port in [22, 2022, 3389, 8080, 9100]:
        try:
            with socket.create_connection((address, port), timeout=2):
                result['public_admin_ports'].append(port)
        except OSError:
            pass
    return result


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(probe, sorted(nodes.items())))
print(json.dumps(results, indent=2))
if any(not r.get('tcp_game') or not r.get('udp_game') or r['public_admin_ports'] for r in results):
    sys.exit(1)
