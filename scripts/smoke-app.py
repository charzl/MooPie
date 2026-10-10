"""Launch the packaged executable and require a real PNG preview (no OpenD needed)."""
import pathlib, plistlib, subprocess, sys
app=pathlib.Path(sys.argv[1]).resolve(); output=pathlib.Path(sys.argv[2]).resolve()
output.parent.mkdir(parents=True,exist_ok=True)
output.unlink(missing_ok=True)
info=plistlib.loads((app/'Contents/Info.plist').read_bytes())
binary=app/'Contents/MacOS'/info['CFBundleExecutable']
subprocess.run([str(binary),'--render-preview',str(output)],check=True,timeout=90)
assert output.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), 'Preview missing or invalid'
print(f'Packaged launch and render passed: {app.name}')
