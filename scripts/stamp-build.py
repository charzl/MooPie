"""Embed the exact SDK/OpenD/source identity before signing either client."""
import json,os,pathlib,plistlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def manifest():
    supplied=os.environ.get('MOOMOO_BUILD_MANIFEST')
    if supplied:return json.loads(pathlib.Path(supplied).read_text())
    return dict(schema=1,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sdk=json.loads((ROOT/'runtime/sdk.json').read_text()),opend=json.loads((ROOT/'runtime/opend.json').read_text()))
if __name__=='__main__':
    app=pathlib.Path(sys.argv[1]);data=manifest();resources=app/'Contents/Resources';resources.mkdir(exist_ok=True)
    (resources/'build-manifest.json').write_text(json.dumps(data,indent=2)+'\n')
    info_path=app/'Contents/Info.plist';info=plistlib.loads(info_path.read_bytes())
    info.update(CFBundleShortVersionString='0.1.0',CFBundleVersion=os.environ.get('GITHUB_RUN_NUMBER','1'),MooSDKVersion=data['sdk']['version'],MooOpenDVersion=data['opend']['version'],MooSourceCommit=data['source_commit'])
    info_path.write_bytes(plistlib.dumps(info))
