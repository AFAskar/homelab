#!/usr/bin/env python3
"""Private libvirt guest bundles: disk, XML, firmware, TPM and optional RAM.

Export runs locally. Import/start/save/status run as root on the dedicated lab
host. Existing guests and source files are never overwritten. A working RAM
checkpoint is consumed only after successful restore; exported bundles stay on
the sending machine. No cold-boot fallback is performed for a failed restore.
"""
import argparse
import copy
from contextlib import contextmanager, nullcontext
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET

ROOT = Path('/srv/pelican/lab/guests')
URI = 'qemu:///system'
LOCKFILE = Path('/run/libvirt/homelab-lab.lock')


@contextmanager
def exclusive_host_operation():
    if os.geteuid() != 0:
        raise ValueError('Run host operations through sudo')
    with LOCKFILE.open('a') as lock:
        os.chmod(LOCKFILE, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another guest import/start/save is active; inspect it before retrying') from None
        yield


def run(*args, uri=None, capture=True):
    command = ['virsh', '-c', uri or URI, *args]
    return subprocess.run(command, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def name_ok(name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', name):
        raise ValueError('Guest name must be a simple identifier, at most 64 characters')
    return name


def domain_ok(xml):
    if xml.tag != 'domain' or xml.get('type') != 'kvm':
        raise ValueError('A KVM domain is required')
    name_ok(xml.findtext('name', ''))
    uuid.UUID(xml.findtext('uuid', ''))
    if xml.find("./os/type").get('arch') != 'x86_64':
        raise ValueError('Only x86-64 guests are supported')
    if any(e.tag not in {'name', 'uuid', 'title', 'description', 'metadata', 'memory', 'currentMemory', 'vcpu', 'os', 'features', 'cpu', 'clock', 'on_poweroff', 'on_reboot', 'on_crash', 'pm', 'devices', 'seclabel', 'resource', 'cputune'} for e in xml):
        raise ValueError('Unsupported host-affecting domain configuration')
    allowed = {'emulator', 'disk', 'controller', 'interface', 'serial', 'console',
               'channel', 'input', 'tpm', 'graphics', 'sound', 'audio', 'video',
               'redirdev', 'watchdog', 'memballoon', 'rng'}
    if any(e.tag not in allowed for e in xml.find('devices')):
        raise ValueError('Host devices, shared filesystems and custom devices are not supported')
    for e in xml.findall('./devices/input'):
        if e.get('type') not in ['tablet', 'mouse', 'keyboard'] or e.find('source') is not None:
            raise ValueError('Host input-device passthrough is not accepted')
    for tag in ['serial', 'console', 'channel']:
        for e in xml.findall('./devices/' + tag):
            if e.get('type') not in ['pty', 'unix', 'spicevmc']:
                raise ValueError('Host file/network character devices are not accepted')
    if any(e.tag.startswith('{http://libvirt.org/schemas/domain/qemu/') for e in xml):
        raise ValueError('Arbitrary QEMU command lines are not supported')
    memory = xml.find('memory')
    units = {'KiB': 1, 'MiB': 1024, 'GiB': 1048576}
    if memory.get('unit', 'KiB') not in units:
        raise ValueError('Unsupported guest memory unit')
    kib = int(memory.text) * units[memory.get('unit', 'KiB')]
    if not 4194304 <= kib <= 16777216 or not 2 <= int(xml.findtext('vcpu')) <= 4:
        raise ValueError('Guest must fit 4–16 GiB RAM and 2–4 vCPUs; no allocation is changed silently')
    tpm = xml.find('./devices/tpm/backend')
    if tpm is None or tpm.get('type') != 'emulator' or tpm.get('version') != '2.0':
        raise ValueError('Windows guest requires an emulated TPM 2.0')
    secure = xml.find("./os/firmware/feature[@name='secure-boot']")
    enrolled = xml.find("./os/firmware/feature[@name='enrolled-keys']")
    loader = xml.find('./os/loader')
    if secure is None or secure.get('enabled') != 'yes' or enrolled is None or enrolled.get('enabled') != 'yes':
        raise ValueError('Secure Boot and enrolled firmware keys are required')
    if loader is not None and loader.get('secure') != 'yes':
        raise ValueError('The selected firmware loader must support Secure Boot')


def manifest(directory, **metadata):
    hashes = {str(p.relative_to(directory)): digest(p) for p in directory.rglob('*') if p.is_file()}
    (directory / 'manifest.json').write_text(json.dumps({'format': 1, **metadata, 'sha256': hashes}, indent=2) + '\n')


def verify(directory):
    directory = directory.resolve(strict=True)
    if any(p.is_symlink() for p in directory.rglob('*')):
        raise ValueError('Symlinks are not allowed in guest bundles')
    m = json.loads((directory / 'manifest.json').read_text())
    if m['format'] != 1:
        raise ValueError('Unsupported guest bundle format')
    actual = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    if set(m['sha256']) != actual:
        raise ValueError('Bundle contents and manifest differ')
    for relative, checksum in m['sha256'].items():
        path = (directory / relative).resolve(strict=True)
        if not path.is_relative_to(directory) or digest(path) != checksum:
            raise ValueError('Unsafe path or checksum mismatch: ' + relative)
    xml = ET.parse(directory / 'domain.xml').getroot()
    domain_ok(xml)
    return m, xml


def write_xml(xml, path):
    ET.indent(xml)
    ET.ElementTree(xml).write(path, encoding='unicode', xml_declaration=True)


def export(args):
    global URI
    URI = args.uri
    directory = args.directory.resolve()
    directory.mkdir(mode=0o700)  # Refuse an existing bundle.
    state = run('domstate', args.name).strip()
    if state != 'shut off' and not args.save:
        raise ValueError('Source must be shut off, or explicitly use --save to preserve RAM and stop it')
    if args.save and state not in ['running', 'paused']:
        raise ValueError('--save requires a running or paused guest')
    # Validate before stopping any source guest.
    xml = ET.fromstring(run('dumpxml', args.name, '--inactive'))
    domain_ok(xml)
    if args.save:
        run('save', args.name, str(directory / 'state.save'), capture=False)
        xml = ET.fromstring(run('save-image-dumpxml', str(directory / 'state.save')))
    # On an export failure retain state.save: virsh restore can recover the source.
    for index, disk in enumerate(xml.findall('./devices/disk')):
        source = disk.find('source')
        if source is None:
            continue
        if disk.get('type') != 'file' or not source.get('file') or disk.find('auth') is not None:
            raise ValueError('Only ordinary local file-backed disks/media can be bundled')
        filename = f'disk-{index}.qcow2' if disk.get('device') == 'disk' else f'media-{index}.iso'
        destination = directory / filename
        if disk.get('device') == 'disk':
            subprocess.run(['qemu-img', 'convert', '-O', 'qcow2', source.get('file'), str(destination)], check=True)
            driver = disk.find('driver')
            if driver is None:
                driver = ET.SubElement(disk, 'driver', {'name': 'qemu'})
            driver.set('type', 'qcow2')
        else:
            shutil.copyfile(source.get('file'), destination)
        source.clear(); source.set('file', filename)
        for backing in list(disk.findall('backingStore')):
            disk.remove(backing)
    for element, filename in [(xml.find('./os/loader'), 'firmware.bin'), (xml.find('./os/nvram'), 'nvram.bin')]:
        if element is not None and element.text:
            shutil.copyfile(element.text, directory / filename)
            element.text = filename
            element.attrib.pop('template', None)
            element.attrib.pop('templateFormat', None)
    backend = xml.find('./devices/tpm/backend')
    source = backend.find('source')
    if source is not None:
        tpm_source = Path(source.get('path'))
    else:
        base = Path.home() / '.config/libvirt/qemu/swtpm' if URI == 'qemu:///session' else Path('/var/lib/libvirt/swtpm')
        tpm_source = base / xml.findtext('uuid') / 'tpm2'
    if not tpm_source.is_dir():
        raise ValueError('Cannot locate persistent TPM state; supply a libvirt emulator directory backend')
    shutil.copytree(tpm_source, directory / 'tpm')
    if source is None:
        source = ET.SubElement(backend, 'source')
    source.attrib = {'type': 'dir', 'path': 'tpm'}
    backend.set('persistent_state', 'yes')
    guest_cpu = xml.find('cpu')
    cpu = copy.deepcopy(guest_cpu) if guest_cpu is not None and guest_cpu.get('mode') == 'custom' else ET.fromstring(run('capabilities')).find('./host/cpu')
    # Compare the source CPU requirements before accepting an opaque RAM image.
    for e in list(cpu):
        if e.tag not in ['model', 'vendor', 'feature']:
            cpu.remove(e)
    cpu.set('mode', 'custom'); cpu.set('match', 'minimum')
    write_xml(cpu, directory / 'source-cpu.xml')
    write_xml(xml, directory / 'domain.xml')
    manifest(directory, name=args.name, saved_ram=args.save,
             hypervisor=run('version'), machine=xml.find('./os/type').get('machine'))
    print('Bundle complete:', directory)
    if args.save:
        print('Source remains saved/off. Do not resume it and reuse this checkpoint with later modified source disks.')


def image(args):
    name_ok(args.name)
    args.directory.mkdir(mode=0o700)
    xml = ET.fromstring("""<domain type='kvm'>
      <name/><uuid/><memory unit='MiB'>16384</memory><currentMemory unit='MiB'>16384</currentMemory><vcpu>4</vcpu>
      <os firmware='efi'><type arch='x86_64' machine='pc-q35-10.2'>hvm</type><firmware>
        <feature enabled='yes' name='secure-boot'/><feature enabled='yes' name='enrolled-keys'/>
      </firmware><boot dev='hd'/></os>
      <features><acpi/><apic/><smm state='on'/></features>
      <cpu mode='custom' match='exact' check='partial'><model fallback='forbid'>EPYC-Rome-v5</model><feature policy='disable' name='lbrv'/><feature policy='disable' name='tsc-scale'/><feature policy='disable' name='pause-filter'/><feature policy='disable' name='pfthreshold'/><feature policy='disable' name='v-vmsave-vmload'/><topology sockets='1' cores='4' threads='1'/></cpu>
      <clock offset='localtime'/><on_poweroff>destroy</on_poweroff><on_reboot>restart</on_reboot>
      <devices><emulator>/usr/bin/qemu-system-x86_64</emulator>
      <disk type='file' device='disk'><driver name='qemu' type='qcow2'/><source file='disk-0.qcow2'/><target dev='vda' bus='virtio'/></disk>
      <interface type='network'><mac address='52:54:00:10:11:01'/><source network='lab'/><model type='virtio'/></interface>
      <channel type='unix'><target type='virtio' name='org.qemu.guest_agent.0'/></channel>
      <tpm model='tpm-crb'><backend type='emulator' version='2.0' persistent_state='yes'><source type='dir' path='tpm'/></backend></tpm>
      <graphics type='spice'><listen type='none'/></graphics><video><model type='vga'/></video>
      <memballoon model='virtio'/></devices></domain>""")
    xml.find('name').text = args.name; xml.find('uuid').text = str(uuid.uuid4())
    domain_ok(xml)
    subprocess.run(['qemu-img', 'convert', '-O', 'qcow2', str(args.image), str(args.directory / 'disk-0.qcow2')], check=True)
    (args.directory / 'tpm').mkdir(mode=0o700)
    write_xml(xml, args.directory / 'domain.xml')
    manifest(args.directory, name=args.name, saved_ram=False)
    print('Cold-boot image bundle created. Existing BitLocker disks need their original TPM/NVRAM bundle or recovery key.')


def host_only():
    if os.geteuid() != 0:
        raise ValueError('Run the host lifecycle commands through sudo')
    with open('/dev/kvm', 'r+b', buffering=0) as kvm:
        if fcntl.ioctl(kvm, 0xAE00, 0) != 12:
            raise ValueError('Hardware KVM is unavailable; software emulation is not a fallback')


def guests():
    return run('list', '--name').split()


def activate_network(xml, directory):
    if guests():
        raise ValueError('Only one guest may run at a time; save it before switching guests')
    interfaces = xml.findall('./devices/interface')
    if len(interfaces) != 1 or interfaces[0].find('mac') is None:
        raise ValueError('Exactly one guest NIC with a MAC is required')
    network = ET.fromstring(run('net-dumpxml', 'lab'))
    dhcp = network.find('./ip/dhcp')
    for child in list(dhcp):
        dhcp.remove(child)
    ET.SubElement(dhcp, 'host', {'mac': interfaces[0].find('mac').get('address'), 'ip': '192.168.124.10'})
    network_file = directory / 'network.xml'
    write_xml(network, network_file)
    active = run('net-list', '--name').split()
    if 'lab' in active:
        run('net-destroy', 'lab')
    # Only this inactive network's generated lease cache is disposable.
    for filename in ['lab.leases', 'lab.status']:
        (Path('/var/lib/libvirt/dnsmasq') / filename).unlink(missing_ok=True)
    run('net-define', str(network_file)); run('net-start', 'lab'); run('net-autostart', 'lab')


def import_guest(args):
    host_only()
    args.directory = args.directory.resolve(strict=True)
    m, xml = verify(args.directory)
    name = name_ok(xml.findtext('name'))
    if name in run('list', '--all', '--name').split() or (ROOT / name).exists():
        raise ValueError('Guest/name already exists; no files or domain overwritten')
    if guests():
        raise ValueError('Save the active guest before importing another')
    if not m['saved_ram'] and xml.find('cpu') is not None and xml.find('cpu').get('mode') == 'custom':
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml') as check:
            check.write(ET.tostring(xml.find('cpu'), encoding='unicode')); check.flush()
            run('hypervisor-cpu-compare', check.name, '--error', capture=False)
    if m['saved_ram']:
        run('hypervisor-cpu-compare', str(args.directory / 'source-cpu.xml'), '--error', capture=False)
    machine = xml.find('./os/type').get('machine')
    available = ET.fromstring(run('capabilities'))
    if machine not in [x.text for x in available.findall('.//machine')] and machine not in [x.get('canonical') for x in available.findall('.//machine')]:
        raise ValueError('Destination QEMU lacks the saved machine type: ' + str(machine))
    for disk in xml.findall('./devices/disk'):
        if disk.get('type') != 'file' or disk.find('auth') is not None:
            raise ValueError('Remote/block/encrypted host-backed storage is not accepted')
        source = disk.find('source')
        if source is None:
            continue
        relative = source.get('file', '')
        if relative not in m['sha256']:
            raise ValueError('Disk is outside the verified bundle')
        if disk.get('device') == 'disk':
            info = json.loads(subprocess.check_output(['qemu-img', 'info', '--output=json', str(args.directory / relative)]))
            if info.get('format') != 'qcow2' or info.get('backing-filename') or info.get('encrypted') or info.get('format-specific', {}).get('data', {}).get('data-file'):
                raise ValueError('A self-contained qcow2 disk is required')
    for tag in ['loader', 'nvram']:
        e = xml.find('./os/' + tag)
        if e is not None and e.text and e.text not in m['sha256']:
            raise ValueError('Firmware/NVRAM is outside the verified bundle')
    if xml.find('./devices/tpm/backend/source') is None or not (args.directory / 'tpm').is_dir():
        raise ValueError('A private TPM directory is required')
    destination = ROOT / name
    # The incoming folder is on the same data volume; do not double-copy disks.
    if args.directory.resolve().parent != Path('/srv/pelican/lab/incoming'):
        raise ValueError('Import only a fresh /srv/pelican/lab/incoming/<transfer-id> directory')
    original_xml = (args.directory / 'domain.xml').read_bytes()
    args.directory.rename(destination)
    try:
        for disk in xml.findall('./devices/disk'):
            source = disk.find('source')
            if source is not None:
                source.set('file', str(destination / source.get('file')))
        for tag in ['loader', 'nvram']:
            element = xml.find('./os/' + tag)
            if element is not None and element.text:
                if element.text not in m['sha256']:
                    raise ValueError('Firmware/NVRAM is outside the verified bundle')
                element.text = str(destination / element.text)
        if xml.find('./os/nvram') is None:
            ET.SubElement(xml.find('os'), 'nvram').text = str(destination / 'nvram.fd')
        for label in list(xml.findall('seclabel')) + list(xml.findall('resource')):
            xml.remove(label)
        for audio in xml.findall('./devices/audio'):
            audio.set('type', 'spice')
        xml.find('./devices/emulator').text = '/usr/bin/qemu-system-x86_64'
        nic = xml.find('./devices/interface'); nic.set('type', 'network')
        for child in list(nic):
            if child.tag in ['source', 'backend', 'target', 'script', 'filterref', 'portForward', 'virtualport']:
                nic.remove(child)
        ET.SubElement(nic, 'source', {'network': 'lab'})
        for graphics in xml.findall('./devices/graphics'):
            graphics.attrib = {'type': 'spice'}
            for child in list(graphics):
                graphics.remove(child)
            ET.SubElement(graphics, 'listen', {'type': 'none'})
        for element in xml.findall('./devices/channel/source') + xml.findall('./devices/serial/source') + xml.findall('./devices/console/source'):
            element.attrib.pop('path', None)
        for rng in xml.findall('./devices/rng/backend'):
            rng.text = '/dev/urandom'
        backend = xml.find('./devices/tpm/backend')
        backend.find('source').set('path', str(destination / 'tpm'))
        backend.set('persistent_state', 'yes')
        # QEMU may write its disks, not the root-owned control XML or directory.
        writable = {Path(e.get('file')) for e in xml.findall('./devices/disk/source')}
        writable |= {Path(e.text) for e in [xml.find('./os/loader'), xml.find('./os/nvram')] if e is not None and e.text}
        writable.add(destination / 'state.save')
        for path in [destination, *destination.rglob('*')]:
            if path == destination:
                shutil.chown(path, user='root', group='root'); path.chmod(0o711)
            elif path.is_relative_to(destination / 'tpm'):
                shutil.chown(path, user='swtpm', group='swtpm'); path.chmod(0o700 if path.is_dir() else 0o600)
            elif path in writable:
                shutil.chown(path, user='libvirt-qemu', group='libvirt-qemu'); path.chmod(0o600)
            else:
                shutil.chown(path, user='root', group='root'); path.chmod(0o700 if path.is_dir() else 0o600)
        write_xml(xml, destination / 'domain.xml')
        subprocess.run(['virt-xml-validate', str(destination / 'domain.xml'), 'domain'], check=True)
        run('define', str(destination / 'domain.xml'))
    except BaseException:
        # A failed response can still have defined a domain: retain its files then.
        if name not in run('list', '--all', '--name').split():
            (destination / 'domain.xml').write_bytes(original_xml)
            destination.rename(args.directory)
            for path in [args.directory, *args.directory.rglob('*')]:
                shutil.chown(path, user='ubuntu', group='ubuntu')
                path.chmod(0o700 if path.is_dir() else 0o600)
        raise
    print('Imported', name, 'without starting it. Original sending-side bundle remains untouched.')


def lifecycle(args):
    host_only()
    name = name_ok(args.name)
    directory = ROOT / name
    if not directory.is_dir():
        raise ValueError('Guest is not registered in the lab store')
    state = run('domstate', name).strip()
    checkpoint = directory / 'state.save'
    if args.command == 'status':
        print(json.dumps({'name': name, 'state': state, 'saved_ram': checkpoint.exists()})); return
    if args.command == 'save':
        if state not in ['shut off', 'running', 'paused']:
            raise ValueError('Wait for the current guest operation before saving')
        if state == 'shut off':
            print('Already stopped; saved checkpoint preserved'); return
        if checkpoint.exists():
            raise ValueError('Existing RAM checkpoint is preserved; no overwrite allowed')
        checkpoint.touch(mode=0o600, exist_ok=False)
        shutil.chown(checkpoint, user='libvirt-qemu', group='libvirt-qemu')
        try:
            run('save', name, str(checkpoint), capture=False)
        except BaseException:
            # An empty placeholder contains no recoverable RAM. Preserve any data.
            if checkpoint.exists() and checkpoint.stat().st_size == 0:
                checkpoint.unlink()
            raise
        # Store the resolved ABI (machine, PCI addresses, firmware), not the original template.
        saved_xml = ET.fromstring(run('save-image-dumpxml', str(checkpoint)))
        domain_ok(saved_xml)
        write_xml(saved_xml, directory / 'domain.xml')
        print('Guest RAM saved; disk, TPM and firmware remain on the data volume'); return
    if args.command == 'start':
        subprocess.run(['systemctl', 'is-active', '--quiet', 'lab-firewall.service'], check=True)
        if state == 'running':
            print('Already running'); return
        if state != 'shut off':
            raise ValueError('Guest must be off before start/restore')
        xml = ET.parse(directory / 'domain.xml').getroot()
        infos = [json.loads(subprocess.check_output(['qemu-img', 'info', '--output=json', e.get('file')])) for e in xml.findall("./devices/disk[@device='disk']/source")]
        memory = xml.find('memory'); scale = {'KiB': 1024, 'MiB': 1048576, 'GiB': 1073741824}
        ram = int(memory.text) * scale[memory.get('unit', 'KiB')]
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
        if available < ram + 2147483648:
            raise ValueError('Insufficient available RAM; no game server is stopped or overcommitted')
        free = shutil.disk_usage(directory).free
        # Leave room for disk growth and the next RAM checkpoint; never silently resize storage.
        virtual = sum(i['virtual-size'] for i in infos)
        if virtual + ram > 120 * 1073741824:
            raise ValueError('Guest disks plus RAM exceed the reserved 120 GiB lab budget')
        required = sum(max(0, i['virtual-size'] - i.get('actual-size', 0)) for i in infos) + (0 if checkpoint.exists() else ram) + 1073741824
        if free < required:
            raise ValueError('Insufficient space for disk growth and RAM save; archive inactive guests or review a larger data volume')
        tpm = directory / 'tpm'
        if not tpm.exists():
            # libvirt removes an empty TPM directory after failed manufacturing.
            tpm.mkdir(mode=0o700)
            shutil.chown(tpm, user='swtpm', group='swtpm')
        activate_network(xml, directory)
        if checkpoint.exists():
            # libvirt enforces the saved ABI; failures retain the checkpoint.
            run('restore', str(checkpoint), '--xml', str(directory / 'domain.xml'), capture=False)
            checkpoint.unlink()  # Consume only the successful working checkpoint, like managedsave.
            # Different host networks require a DHCP refresh, not a Windows reboot.
            mac = xml.find('./devices/interface/mac').get('address')
            run('domif-setlink', name, mac, 'down'); run('domif-setlink', name, mac, 'up')
        else:
            run('start', name, capture=False)
        print('Guest started. Verify Windows Secure Boot, TPM 2.0 and private RDP inside the guest.')


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    ex = sub.add_parser('export'); ex.add_argument('name'); ex.add_argument('directory', type=Path)
    ex.add_argument('--uri', default='qemu:///session'); ex.add_argument('--save', action='store_true')
    img = sub.add_parser('image'); img.add_argument('image', type=Path); img.add_argument('directory', type=Path); img.add_argument('--name', default='win11-lab')
    ck = sub.add_parser('check'); ck.add_argument('directory', type=Path)
    im = sub.add_parser('import'); im.add_argument('directory', type=Path)
    for command in ['start', 'save', 'status']:
        s = sub.add_parser(command); s.add_argument('name')
    args = p.parse_args()
    try:
        with exclusive_host_operation() if args.command in {'import', 'start', 'save'} else nullcontext():
            if args.command == 'export': export(args)
            elif args.command == 'image': image(args)
            elif args.command == 'check': verify(args.directory); print('Bundle checksums and guest security configuration passed')
            elif args.command == 'import': import_guest(args)
            else: lifecycle(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
