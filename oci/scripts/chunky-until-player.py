#!/usr/bin/env python3
"""Run on a Wings host as root: start Chunky while empty, pause at first join.

Use a transient systemd service so the one-shot watcher survives SSH disconnects.
Wings authentication stays in /etc/pelican/config.yml. TLS uses the host trust
store and validates the node certificate while connecting over loopback.
"""
import argparse
import http.client
import json
from pathlib import Path
import re
import socket
import ssl
import time
import uuid

import yaml


MESSAGE = re.compile(r'\[Server thread/INFO\] \[(?:net\.minecraft\.server\.MinecraftServer|net\.minecraft\.server\.players\.PlayerList)/\]: (.*)$')
JOIN = re.compile(r'[A-Za-z0-9_]{1,16} joined the game$')
COUNT = re.compile(r'There are (\d+) of a max of \d+ players online:')


def player_count(line):
    """Only trust server messages, never chat that quotes a join message."""
    match = MESSAGE.search(line)
    if not match:
        return None
    message = match.group(1)
    if JOIN.fullmatch(message):
        return 1
    count = COUNT.match(message)
    return int(count.group(1)) if count else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-uuid', required=True, type=uuid.UUID)
    parser.add_argument('--tls-name', required=True)
    parser.add_argument('--center', required=True, type=int, nargs=2)
    parser.add_argument('--radius', required=True, type=int)
    args = parser.parse_args()
    if args.radius <= 0:
        parser.error('radius must be positive')
    config = yaml.safe_load(Path('/etc/pelican/config.yml').read_text())
    port = config['api']['port']
    context = ssl.create_default_context()
    log = Path(config['system']['data']) / str(args.server_uuid) / 'logs/latest.log'

    def commands(values):
        connection = http.client.HTTPSConnection(args.tls_name, port, context=context, timeout=15)
        try:
            connection.sock = context.wrap_socket(
                socket.create_connection(('127.0.0.1', port), timeout=15),
                server_hostname=args.tls_name)
            connection.request('POST', f'/api/servers/{args.server_uuid}/commands',
                               json.dumps({'commands': values}),
                               {'Authorization': 'Bearer ' + config['token'],
                                'Content-Type': 'application/json'})
            response = connection.getresponse()
            response.read()
            if response.status != 204:
                raise RuntimeError(f'Wings command failed: HTTP {response.status}')
        finally:
            connection.close()

    started = False
    with log.open() as stream:
        identity = log.stat().st_ino
        stream.seek(0, 2)
        commands(['list'])
        last_poll = time.monotonic()
        last_count = last_poll
        try:
            while True:
                if log.stat().st_ino != identity or log.stat().st_size < stream.tell():
                    raise RuntimeError('Game log rotated/truncated; stopping this watcher')
                line = stream.readline()
                if line:
                    count = player_count(line)
                    if count is not None:
                        last_count = time.monotonic()
                        if count > 0:
                            commands(['chunky pause minecraft:overworld'])
                            print('Player present: Chunky paused. Watcher finished.', flush=True)
                            return
                        if not started:
                            x, z = args.center
                            commands(['chunky world minecraft:overworld',
                                      f'chunky center {x} {z}', f'chunky radius {args.radius}',
                                      'chunky shape square', 'chunky quiet 30', 'chunky start'])
                            started = True
                            print(f'Empty server: started radius {args.radius} at {x}, {z}.', flush=True)
                    if '[Chunky]' in line and 'Task finished' in line:
                        print('Chunky completed. Watcher finished.', flush=True)
                        return
                else:
                    time.sleep(0.25)
                now = time.monotonic()
                if now - last_poll >= 5:
                    commands(['list'])
                    last_poll = now
                if now - last_count > 60:
                    raise RuntimeError('No fresh player-count response for 60 seconds')
        except BaseException:
            if started:
                commands(['chunky pause minecraft:overworld'])
            raise


if __name__ == '__main__':
    main()
