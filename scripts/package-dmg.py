"""Create and mount-verify a drag-to-Applications installer using macOS system tools."""
import argparse,json,os,pathlib,plistlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
REQ='=identifier "com.moomoo.opend" and anchor apple generic and certificate leaf[subject.OU] = "6HE4ZULJ45"'
def run(*args):return subprocess.check_output(args,text=True)
def package(app,output):
    app=pathlib.Path(app).resolve();output=pathlib.Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    metadata=json.loads((app/'Contents/Resources/build-manifest.json').read_text())
    run('codesign','--verify','--deep','--strict',str(app))
    with tempfile.TemporaryDirectory(prefix='mooclients-dmg-') as work:
        root=pathlib.Path(work);stage=root/'image';stage.mkdir()
        run('ditto',str(app),str(stage/app.name));os.symlink('/Applications',stage/'Applications')
        (stage/'安装说明.txt').write_text('将应用图标拖入 Applications 文件夹，然后从“应用程序”打开。\n\n需要 Apple Silicon Mac 和 macOS 14 或更高版本。\n首次打开如受到系统拦截，请在系统设置 → 隐私与安全性中允许运行。当前客户端使用 ad-hoc 签名，尚未公证。\n\n官方 OpenD 会自动启动，请在其窗口登录，然后在客户端连接 OpenD。\n'+f"SDK：{metadata['sdk']['version']}\nOpenD：{metadata['opend']['version']}\n源码：{metadata['source_commit']}\n",encoding='utf-8')
        (stage/'LICENSE.txt').write_bytes((ROOT/'LICENSE').read_bytes());(stage/'THIRD_PARTY.txt').write_bytes((ROOT/'THIRD_PARTY.md').read_bytes())
        run('hdiutil','create','-ov','-format','UDZO','-fs','HFS+','-volname',app.stem+' Installer','-srcfolder',str(stage),str(output))
        run('hdiutil','verify',str(output))
        mount=root/'mount';mount.mkdir()
        run('hdiutil','attach','-readonly','-nobrowse','-mountpoint',str(mount),str(output))
        try:
            installed=mount/app.name
            if not (mount/'Applications').is_symlink() or os.readlink(mount/'Applications')!='/Applications':raise RuntimeError('Invalid Applications shortcut')
            run('codesign','--verify','--deep','--strict',str(installed))
            run('codesign','--verify','--deep','--strict','-R',REQ,str(installed/'Contents/Resources/OpenD/moomoo_OpenD.app'))
            identity=json.loads((installed/'Contents/Resources/build-manifest.json').read_text())
            if identity!=metadata:raise RuntimeError('Installer build identity mismatch')
            info=plistlib.loads((installed/'Contents/Info.plist').read_bytes())
            if info['MooSDKVersion']!=metadata['sdk']['version'] or info['MooOpenDVersion']!=metadata['opend']['version']:raise RuntimeError('Installer version mismatch')
        finally:run('hdiutil','detach',str(mount))
    print(f'Verified drag-to-Applications installer: {output.name} ({output.stat().st_size//1024//1024} MiB)')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('app');p.add_argument('output');a=p.parse_args();package(a.app,a.output)
