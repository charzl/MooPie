"""Preflight both validated installers, then publish atomically through a draft."""
import hashlib,json,os,pathlib,re,shutil,subprocess,sys
CLIENTS=('MooPython','MooSwiftCpp')
def collect_artifacts(root):
 root=pathlib.Path(root);target=root.with_name(root.name+'-normalized');target.mkdir(parents=True,exist_ok=True)
 names=['resolved-build.json','comparison.md','comparison.json']
 for client,prefix in zip(CLIENTS,('python','swift-cpp')):names.extend([f'{client}-macos-arm64.dmg',f'{client}-macos-arm64.validation.json',f'{prefix}-build.json',f'{prefix}-opend-smoke.json'])
 for name in names:
  matches=[path for path in root.rglob(name) if path.is_file()]
  require(bool(matches),'Missing release asset: '+name)
  require(len({digest(path) for path in matches})==1,'Conflicting release assets: '+name)
  shutil.copyfile(matches[0],target/name)
 return target
def require(condition,message):
 if not condition:raise RuntimeError(message)
def digest(path):
 result=hashlib.sha256()
 with pathlib.Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
 return result.hexdigest()
def preflight(root,source_commit,min_bytes=10*1024*1024):
 root=pathlib.Path(root);manifest=json.loads((root/'resolved-build.json').read_text())
 require(manifest.get('schema')==1,'Unsupported release manifest')
 require(re.fullmatch(r'[a-f0-9]{40}',source_commit) is not None and manifest['source_commit']==source_commit,'Release source commit mismatch')
 for component in ('sdk','opend'):require(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',manifest[component]['version']) is not None,'Invalid release version')
 expected_tag=f"build-{source_commit[:12]}-sdk{manifest['sdk']['version']}-opend{manifest['opend']['version']}"
 require(manifest['release_tag']==expected_tag or re.fullmatch(re.escape(expected_tag)+r'-run[0-9]+',manifest['release_tag']) is not None,'Invalid release tag')
 files=[]
 for client,prefix in zip(CLIENTS,('python','swift-cpp')):
  image=root/f'{client}-macos-arm64.dmg';report=root/f'{client}-macos-arm64.validation.json'
  require(image.is_file() and image.stat().st_size>min_bytes,'Missing or truncated installer: '+client)
  with image.open('rb') as stream:stream.seek(-512,2);require(stream.read(4)==b'koly','Invalid DMG container: '+client)
  validation=json.loads(report.read_text());build=json.loads((root/f'{prefix}-build.json').read_text())
  require(validation['file']==image.name and validation['size_bytes']==image.stat().st_size and validation['sha256']==digest(image),'Installer checksum mismatch: '+client)
  for flag in ('mounted_verified','applications_link_verified','client_signature_verified','official_opend_signature_verified'):require(validation.get(flag) is True,'Installer validation incomplete: '+flag)
  require(validation['source_commit']==source_commit and build['commit']==source_commit,'Client source identity mismatch')
  require(build['app']==client+'.app' and build['architecture']=='arm64','Incorrect client or architecture')
  for component in ('sdk','opend'):
   require(validation[f'{component}_version']==manifest[component]['version'] and build[f'{component}_version']==manifest[component]['version'],'Client SDK/OpenD identity mismatch')
  smoke=json.loads((root/f'{prefix}-opend-smoke.json').read_text())
  require(smoke['version']==manifest['opend']['version'] and smoke.get('official_signature_verified') is True and smoke.get('updater_bootstrap_verified') is True and smoke.get('official_gui_alive_seconds',0)>=5,'Real OpenD startup validation missing')
  files.append(image)
 require((root/'comparison.md').is_file() and (root/'comparison.json').is_file(),'Performance report missing')
 return manifest,files

def gh(*args):
 result=subprocess.run(['gh',*args],capture_output=True,text=True)
 if result.returncode:raise subprocess.CalledProcessError(result.returncode,result.args,output=result.stdout,stderr=result.stderr)
 return result.stdout
def publish(root,source_commit,call=gh,min_bytes=10*1024*1024):
 root=pathlib.Path(root);manifest,files=preflight(root,source_commit,min_bytes)
 tag=manifest['release_tag'];checksums=root/'SHA256SUMS.txt'
 checksums.write_text(''.join(f'{digest(file)}  {file.name}\n' for file in files))
 notes=root/'release-notes.md';notes.write_text(f'''两版 macOS 安装包：打开 DMG，把应用拖入 Applications。

- SDK：{manifest['sdk']['version']}
- 内置官方 OpenD：{manifest['opend']['version']}
- 源码提交：{manifest['source_commit']}
- 支持 Apple Silicon、macOS 14 及以上。

已通过两版 SDK/界面测试、真实 OpenD 更新与启动校验、DMG 挂载和签名检查。账号登录与真实行情权限仍需用户验收；当前为实验性看盘客户端，未实现完整交易功能。客户端使用 ad-hoc 签名，尚未公证，首次打开可能需要在系统“隐私与安全性”中允许运行；内置 OpenD 保留官方签名。

SHA256SUMS.txt 可校验下载文件；resolved-build.json 记录官方源和哈希。comparison.md 是离线客户端性能报告，CPU/RSS 不包含登录后的 OpenD。
''')
 try:existing=json.loads(call('api',f"repos/{os.environ['GITHUB_REPOSITORY']}/releases/tags/{tag}"))
 except subprocess.CalledProcessError as error:
  if '404' not in str(error.stderr):raise
  existing=None
 if existing is not None:require(existing.get('draft') is True,'Release already published; refusing overwrite')
 else:call('release','create',tag,'--draft','--prerelease','--target',source_commit,'--title',f"macOS · SDK {manifest['sdk']['version']} · OpenD {manifest['opend']['version']}",'--notes-file',str(notes))
 assets=[*files,checksums,root/'resolved-build.json',root/'comparison.md',root/'comparison.json']
 for client,prefix in zip(CLIENTS,('python','swift-cpp')):assets.extend([root/f'{client}-macos-arm64.validation.json',root/f'{prefix}-build.json',root/f'{prefix}-opend-smoke.json'])
 call('release','upload',tag,*map(str,assets),'--clobber')
 found=json.loads(call('release','view',tag,'--json','assets'))['assets'];expected={p.name:p.stat().st_size for p in assets};actual={a['name']:a['size'] for a in found}
 require(all(actual.get(name)==size for name,size in expected.items()),'Release asset verification failed')
 call('release','edit',tag,'--draft=false','--prerelease','--notes-file',str(notes))
 return call('release','view',tag,'--json','url','--jq','.url').strip()
if __name__=='__main__':print(publish(collect_artifacts(pathlib.Path(sys.argv[1]).resolve()),os.environ['GITHUB_SHA']))
