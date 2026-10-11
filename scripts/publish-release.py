"""Publish both verified installers as one release only after all CI jobs succeed."""
import hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(sys.argv[1]).resolve()
def require(condition,message):
 if not condition:raise RuntimeError(message)
def gh(*args):return subprocess.check_output(['gh',*args],text=True)
manifest_path=ROOT/'resolved-build.json';manifest=json.loads(manifest_path.read_text())
require(manifest['source_commit']==os.environ['GITHUB_SHA'], 'Release source commit mismatch')
tag=manifest['release_tag'];files=[ROOT/'MooPython-macos-arm64.dmg',ROOT/'MooSwiftCpp-macos-arm64.dmg']
for file in files:require(file.is_file() and file.stat().st_size>10*1024*1024, 'Missing installer')
for name in ('python-build.json','swift-cpp-build.json'):
 data=json.loads((ROOT/name).read_text());require(data['commit']==manifest['source_commit'],'Client source identity mismatch')
 require(data['sdk_version']==manifest['sdk']['version'] and data['opend_version']==manifest['opend']['version'],'Client SDK/OpenD identity mismatch')
checksums=ROOT/'SHA256SUMS.txt'
with checksums.open('w') as out:
 for file in files:
  digest=hashlib.sha256()
  with file.open('rb') as src:
   for block in iter(lambda:src.read(1024*1024),b''):digest.update(block)
  out.write(f'{digest.hexdigest()}  {file.name}\n')
notes=ROOT/'release-notes.md';notes.write_text(f'''两版 macOS 安装包：打开 DMG，把应用拖入 Applications。

- SDK：{manifest['sdk']['version']}
- 内置官方 OpenD：{manifest['opend']['version']}
- 源码提交：{manifest['source_commit']}
- 支持 Apple Silicon、macOS 14 及以上。

已通过两版 SDK/界面测试、真实 OpenD 更新与启动校验、DMG 挂载和签名检查。账号登录与真实行情权限仍需用户验收；当前为实验性看盘客户端，未实现完整交易功能。客户端使用 ad-hoc 签名，尚未公证，首次打开可能需要在系统“隐私与安全性”中允许运行；内置 OpenD 保留官方签名。

SHA256SUMS.txt 可校验下载文件；resolved-build.json 记录构建时使用的官方源和哈希。comparison.md 是离线客户端性能报告，CPU/RSS 不包含登录后的 OpenD。
''')
existing=subprocess.run(['gh','release','view',tag,'--json','isDraft'],capture_output=True,text=True)
if existing.returncode==0:
 if not json.loads(existing.stdout)['isDraft']:raise RuntimeError('Release already published; refusing overwrite')
else:
 gh('release','create',tag,'--draft','--prerelease','--target',manifest['source_commit'],'--title',f"macOS · SDK {manifest['sdk']['version']} · OpenD {manifest['opend']['version']}",'--notes-file',str(notes))
assets=[*files,checksums,manifest_path,ROOT/'comparison.md',ROOT/'comparison.json',ROOT/'python-build.json',ROOT/'swift-cpp-build.json',ROOT/'python-opend-smoke.json',ROOT/'swift-cpp-opend-smoke.json']
gh('release','upload',tag,*map(str,assets),'--clobber')
# Do not expose a partially uploaded pair. Only turn the draft public once all assets exist.
found=json.loads(gh('release','view',tag,'--json','assets'))['assets'];expected={p.name:p.stat().st_size for p in assets}
actual={a['name']:a['size'] for a in found}
require(all(actual.get(name)==size for name,size in expected.items()), 'Release asset verification failed')
gh('release','edit',tag,'--draft=false','--prerelease','--notes-file',str(notes))
print(gh('release','view',tag,'--json','url','--jq','.url').strip())
