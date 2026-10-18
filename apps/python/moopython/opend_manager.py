"""macOS official OpenD installer/updater, independent of Qt and the quote SDK."""
import argparse
from contextlib import suppress
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

REQUIREMENT = 'identifier "com.moomoo.opend" and anchor apple generic and certificate leaf[subject.OU] = "6HE4ZULJ45"'


def parts(version):
    if not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Invalid OpenD version')
    return tuple(int(field) for field in version.split('.'))


def newer(left, right): return parts(left) > parts(right)


def download_url(version):
    parts(version)
    return f'https://softwaredownload.moomoo.com/moomoo_OpenD_{version}_Mac.tar.gz'


def version_from_redirect(headers):
    for line in headers.splitlines():
        if not line.lower().startswith('location:'): continue
        url = urlsplit(line.split(':', 1)[1].strip())
        if url.scheme != 'https' or url.hostname not in ('softwaredownload.moomoo.com', 'softwaredownload.futunn.com'): continue
        match = re.fullmatch(r'(?:moomoo|Futu)_OpenD_([0-9]+\.[0-9]+\.[0-9]+)_Mac.tar.gz', url.path.rsplit('/', 1)[-1])
        if match: return match[1]
    raise ValueError('Official latest-version service unavailable')


def command(executable, *arguments):
    result = subprocess.run([executable, *map(str, arguments)], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=660)
    if result.returncode:
        raise RuntimeError(f'{Path(executable).name} failed: {result.stdout[:1500]}')
    return result.stdout


def running_bundle_paths():
    text = command('/usr/bin/lsappinfo', 'info', '-only', 'bundlepath', 'com.moomoo.opend')
    return [Path(json.loads(value)) for value in re.findall(r'"LSBundlePath"=("(?:[^"\\]|\\.)*")', text)]


class Store:
    def __init__(self, root): self.root = Path(root)

    def app(self, version):
        parts(version)
        return self.root / 'versions' / version / 'moomoo_OpenD.app'

    def read(self):
        path = self.root / 'selection.json'
        if not path.exists(): return None
        state = json.loads(path.read_text(encoding='utf-8'))
        parts(state['current'])
        if state.get('previous') is not None: parts(state['previous'])
        # Older installations used Foundation's seconds since 2001-01-01.
        if 'last_check' not in state and 'lastCheck' in state:
            state['last_check'] = state['lastCheck'] + 978307200
        return state

    def save(self, state):
        parts(state['current'])
        if state.get('previous') is not None: parts(state['previous'])
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.root, delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(state, stream, allow_nan=False)
                stream.flush(); os.fsync(stream.fileno())
            temporary.replace(self.root / 'selection.json')
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)

    def activate(self, version, validate):
        validate(self.app(version))
        state = self.read()
        if state and not newer(version, state['current']): return
        self.save(dict(current=version, previous=state['current'] if state else None, last_check=time.time()))

    def rollback(self, validate):
        state = self.read()
        if not state or not state.get('previous'): raise ValueError('No previous OpenD available')
        validate(self.app(state['previous']))
        self.save(dict(current=state['previous'], previous=state['current'], last_check=time.time()))


class Manager:
    def __init__(self, root):
        import fcntl
        self.store = Store(root)
        self.store.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = (self.store.root / 'update.lock').open('a')
        try: fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock.close()
            raise RuntimeError('另一客户端正在管理 OpenD，请稍后重试') from None
        # Only staging directories owned by this store are discarded, under the lock.
        for item in self.store.root.glob('staging-*'):
            if item.is_dir() and not item.is_symlink(): shutil.rmtree(item)

    def __enter__(self): return self

    def __exit__(self, *_): self.lock.close()

    def validate(self, app, version=None):
        app = Path(app)
        with (app / 'Contents/Info.plist').open('rb') as stream: info = plistlib.load(stream)
        if info.get('CFBundleIdentifier') != 'com.moomoo.opend': raise ValueError('Invalid official OpenD bundle')
        actual = info.get('CFBundleShortVersionString'); parts(actual)
        if version is not None and actual != version: raise ValueError('OpenD package version mismatch')
        command('/usr/bin/codesign', '--verify', '--deep', '--strict', '-R', '=' + REQUIREMENT, app)
        architectures = command('/usr/bin/lipo', '-archs', app / 'Contents/MacOS/moomoo_OpenD').split()
        expected = 'arm64' if platform.machine() == 'arm64' else 'x86_64'
        if expected not in architectures: raise ValueError('OpenD does not support this Mac architecture')

    def bootstrap(self, bundle, version):
        state = self.store.read()
        if state:
            self.validate(self.store.app(state['current']), state['current']); return
        self.validate(bundle, version)
        destination = self.store.app(version)
        destination.parent.mkdir(parents=True, exist_ok=True)
        command('/usr/bin/ditto', bundle, destination)
        self.store.activate(version, lambda app: self.validate(app, version))
        self.store.save(dict(current=version))

    def ensure_installed(self, version, sha256, allow_download=True):
        parts(version)
        if not isinstance(sha256, str) or not re.fullmatch('[0-9a-f]{64}', sha256):
            raise ValueError('Invalid OpenD archive checksum')
        state = self.store.read()
        if state:
            self.validate(self.store.app(state['current']), state['current'])
            if not newer(version, state['current']): return
        else:
            for candidate in [*running_bundle_paths(), Path('/Applications/moomoo_OpenD.app')]:
                try:
                    self.validate(candidate)
                    with (candidate / 'Contents/Info.plist').open('rb') as stream:
                        actual = plistlib.load(stream)['CFBundleShortVersionString']
                except (OSError, ValueError, RuntimeError): continue
                if not newer(version, actual):
                    self.bootstrap(candidate, actual); return
        if not allow_download: raise ValueError('尚未安装兼容的 OpenD；首次使用需要联网下载')
        self.install(version, sha256)

    def launch(self):
        state = self.store.read()
        if not state: raise ValueError('OpenD not installed')
        if running_bundle_paths(): return  # Reuse the user's logged-in gateway.
        target = self.store.app(state['current']); self.validate(target, state['current'])
        try: command('/usr/bin/open', '-a', target)
        except RuntimeError:
            self.store.rollback(self.validate)
            command('/usr/bin/open', '-a', self.store.app(self.store.read()['current']))

    def update(self, force=False):
        state = self.store.read()
        if not state: raise ValueError('OpenD not installed')
        if not force and time.time() - state.get('last_check', 0) < 86400:
            return f'OpenD {state["current"]} · 自动检查间隔 24 小时'
        state['last_check'] = time.time(); self.store.save(state)
        latest = None
        for host in ('www.moomoo.com', 'www.futunn.com'):
            try:
                headers = command('/usr/bin/curl', '--fail', '--silent', '--show-error', '--proto', '=https',
                                  '--max-time', '20', '-I', f'https://{host}/download/fetch-lasted-link?name=opend-macos')
                latest = version_from_redirect(headers); break
            except (ValueError, RuntimeError): continue
        if latest is None: raise RuntimeError(f'更新服务暂不可用，保留 OpenD {state["current"]}')
        if not newer(latest, state['current']): return f'OpenD {state["current"]} 已是最新版'
        return self.install(latest)

    def install(self, version, sha256=None):
        existing = self.store.app(version)
        if existing.exists():
            try: self.validate(existing, version)
            except (OSError, ValueError, RuntimeError): pass
            else:
                self.store.activate(version, lambda app: self.validate(app, version))
                return f'OpenD {version} 已校验并选中；重新启动官方 OpenD 生效'
        if existing.resolve() in [p.resolve() for p in running_bundle_paths()]:
            raise ValueError('待更新路径仍有 OpenD 运行；请退出官方 OpenD 后重试')
        with tempfile.TemporaryDirectory(prefix='staging-', dir=self.store.root) as directory:
            stage = Path(directory); archive = stage / 'download.tar.gz'
            command('/usr/bin/curl', '--fail', '--silent', '--show-error', '--proto', '=https', '--max-time', '600',
                    '--max-filesize', '1073741824', '--output', archive, download_url(version))
            if sha256:
                with archive.open('rb') as stream: actual = hashlib.file_digest(stream, 'sha256').hexdigest()
                if actual != sha256: raise ValueError('Official OpenD archive SHA-256 mismatch')
            entry = f'moomoo_OpenD_{version}_Mac/moomoo_OpenD-GUI_{version}_Mac/moomoo_OpenD-GUI_{version}_Mac.dmg'
            command('/usr/bin/tar', '-xzf', archive, '-C', stage, entry)
            mount = stage / 'mount'; mount.mkdir()
            command('/usr/bin/hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', mount, stage / entry)
            try:
                app = mount / 'moomoo_OpenD.app'; self.validate(app, version)
                if existing.parent.exists(): shutil.rmtree(existing.parent)
                existing.parent.mkdir(parents=True)
                command('/usr/bin/ditto', app, existing)
                self.store.activate(version, lambda target: self.validate(target, version))
            finally:
                with suppress(RuntimeError): command('/usr/bin/hdiutil', 'detach', mount)
        return f'已下载并校验 OpenD {version}；退出官方 OpenD 后重新启动即可使用，旧版可回退'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Manage the official macOS OpenD installation; never logs in or trades')
    parser.add_argument('--root', type=Path, default=Path.home() / 'Library/Application Support/MooClients/OpenD')
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--bundle', type=Path); parser.add_argument('--version')
    for name in ('verify', 'offline', 'launch', 'force', 'rollback'): parser.add_argument('--' + name, action='store_true')
    parser.add_argument('--output', type=Path, help='JSON result for a windowed application without stdout')
    args = parser.parse_args(argv); messages = []
    def emit(text):
        messages.append(text)
        if sys.stdout is not None: print(text, flush=True)
    result = {}; code = 0
    try:
        if sys.platform != 'darwin': raise ValueError('The OpenD installation manager is only available on macOS')
        with Manager(args.root) as manager:
            if args.verify:
                if not args.bundle or not args.version: raise ValueError('Missing --bundle / --version')
                manager.validate(args.bundle, args.version); emit(f'官方 OpenD {args.version} 签名及架构验证通过')
            else:
                if args.metadata:
                    metadata = json.loads(args.metadata.read_text(encoding='utf-8'))
                    emit('正在准备官方 OpenD；已有安装将复用，首次使用可能需要下载…')
                    manager.ensure_installed(metadata['version'], metadata['sha256'], not args.offline)
                elif args.bundle and args.version: manager.bootstrap(args.bundle, args.version)
                else: raise ValueError('Missing --metadata or --bundle / --version')
                if args.rollback:
                    manager.store.rollback(manager.validate); emit('已回退；重新启动官方 OpenD 生效')
                else:
                    if args.launch: manager.launch(); emit('官方 OpenD 已启动；请在其窗口登录，再连接行情')
                    if not args.offline: emit(manager.update(args.force))
    except Exception as error:
        result['error'] = str(error); emit(str(error)); code = 1
    if args.output: args.output.write_text(json.dumps(dict(result, messages=messages), ensure_ascii=False), encoding='utf-8')
    return code


if __name__ == '__main__': raise SystemExit(main())
