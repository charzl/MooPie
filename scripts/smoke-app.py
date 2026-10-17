"""Launch the packaged executable and require a real PNG preview (no OpenD needed)."""
import json, pathlib, plistlib, subprocess, sys
app=pathlib.Path(sys.argv[1]).resolve(); output=pathlib.Path(sys.argv[2]).resolve()
output.parent.mkdir(parents=True,exist_ok=True)
output.unlink(missing_ok=True)
info=plistlib.loads((app/'Contents/Info.plist').read_bytes())
binary=app/'Contents/MacOS'/info['CFBundleExecutable']
subprocess.run([str(binary),'--sdk-check'],check=True,timeout=90)
if app.name in ('MooPython.app', 'MooPie.app'):
    subprocess.run([str(binary),'options','--help'],check=True,timeout=90)
subprocess.run([str(binary),'--render-preview',str(output)],check=True,timeout=90)
assert output.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), 'Preview missing or invalid'
result=output.with_suffix('.research-error.json')
result.unlink(missing_ok=True)
process=subprocess.run([str(binary),'research','trend','AAPL','--port','1','--output',str(result)],timeout=30)
assert process.returncode==1 and json.loads(result.read_text(encoding='utf-8'))['error'], 'Research error protocol failed'
print(f'Packaged launch and render passed: {app.name}')
