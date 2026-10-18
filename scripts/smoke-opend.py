"""Verify genuine OpenD and updater, then start the official GUI without credentials.
No quote login or market entitlement is asserted. Only the process started here is stopped.
"""
import argparse,json,os,pathlib,plistlib,shutil,signal,subprocess,tempfile,time

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('app'); parser.add_argument('output'); args=parser.parse_args()
    app=pathlib.Path(args.app).resolve(); directory=app/'Contents/Resources/OpenD'
    metadata=json.loads((directory/'opend.json').read_text()); gateway=directory/'moomoo_OpenD.app'
    helper=[str(app/'Contents/MacOS'/app.stem),'opend']
    external=app.stem == 'MooPie'
    if external and list(app.rglob('moomoo_OpenD.app')): raise RuntimeError('MooPie must not bundle OpenD')
    command=[*helper,'--metadata',str(directory/'opend.json')] if external else [*helper,'--bundle',str(gateway),'--version',metadata['version']]
    with tempfile.TemporaryDirectory(prefix='mooclients-opend-smoke-') as work:
        root=pathlib.Path(work)/'runtime'
        if external:
            subprocess.run([*command,'--root',str(root)],check=True,timeout=900)
            gateway=root/'versions'/metadata['version']/'moomoo_OpenD.app'
        else:
            subprocess.run([*command,'--root',str(root),'--verify'],check=True,timeout=60)
        subprocess.run([*command,'--root',str(root),'--offline'],check=True,timeout=90)
        state=json.loads((root/'selection.json').read_text()); assert state['current']==metadata['version']
        installed=root/'versions'/metadata['version']/'moomoo_OpenD.app'
        # Validate the copied executable as well; changing its publisher or version must fail.
        subprocess.run([*helper,'--bundle',str(installed),'--version',metadata['version'],'--root',str(root),'--verify'],check=True,timeout=60)
        rejected=subprocess.run([*helper,'--bundle',str(gateway),'--version','0.0.0','--root',str(root),'--verify'],capture_output=True,timeout=60)
        assert rejected.returncode!=0, 'Incorrect version accepted'
        binary=installed/'Contents/MacOS/moomoo_OpenD'
        with (pathlib.Path(work)/'opend.log').open('w') as log:
            process=subprocess.Popen([str(binary)],cwd=work,stdout=log,stderr=log,start_new_session=True)
            try:
                time.sleep(5)
                assert process.poll() is None, f'Genuine GUI OpenD exited early: {process.returncode}'
                # Versioning/rollback tests use fixtures; this is the real publisher-signed runtime.
                result=dict(version=metadata['version'],archive_sha256=metadata['sha256'],official_signature_verified=True,
                    opend_bundled=not external,updater_bootstrap_verified=True,external_bootstrap_verified=external,incorrect_version_rejected=True,official_gui_alive_seconds=5,
                    account_logged_in=False,quote_connection_tested=False,
                    note='Real official OpenD startup only. Login, quotes, CPU/RSS under live data and entitlement acceptance require a user account.')
            finally:
                if process.poll() is None:
                    os.killpg(process.pid,signal.SIGTERM)
                    try: process.wait(timeout=10)
                    except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL); process.wait()
        subprocess.run(['codesign','--verify','--deep','--strict',str(installed)],check=True,timeout=60)
        # Build a tampered wrapper around the real signed executable; do not modify a
        # launched application (macOS App Management protects installed bundles).
        altered=pathlib.Path(work)/'tampered.app'; (altered/'Contents/MacOS').mkdir(parents=True)
        shutil.copy2(binary,altered/'Contents/MacOS/moomoo_OpenD')
        info=plistlib.loads((installed/'Contents/Info.plist').read_bytes()); info['CFBundleName']='tampered'
        (altered/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
        tampered=subprocess.run([*helper,'--bundle',str(altered),'--version',metadata['version'],'--root',str(root),'--verify'],capture_output=True,timeout=60)
        assert tampered.returncode!=0, 'Tampered publisher-signed bundle accepted'
        result['tampered_signature_rejected']=True
    output=pathlib.Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
