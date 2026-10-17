import argparse
import os
import sys

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'paper':
        from moopython.paper_cli import main as paper_main
        return paper_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == 'research':
        from moopython.research_cli import main as research_main
        return research_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == 'options':
        from moopython.options_cli import main as options_main
        return options_main(sys.argv[2:])
    parser=argparse.ArgumentParser(description="MooPie desktop market client")
    parser.add_argument("--render-preview")
    parser.add_argument("--sdk-check", action="store_true")
    parser.add_argument("--benchmark-output")
    parser.add_argument("--quit-after",type=int,default=0)
    parser.add_argument("--host")
    parser.add_argument("--classic", action="store_true", help="Open the full market dashboard")
    parser.add_argument("--port",type=int,default=11111)
    args=parser.parse_args()
    if args.sdk_check:
        import moomoo
        assert callable(moomoo.OpenQuoteContext)
        import json,pathlib
        manifest=pathlib.Path(sys.executable).resolve().parent.parent/'Resources/build-manifest.json'
        if getattr(sys,'frozen',False) and sys.platform == 'darwin':
            expected=json.loads(manifest.read_text())['sdk']['version']
            assert moomoo.__version__==expected, f'SDK version mismatch: {moomoo.__version__} vs {expected}'
        print(json.dumps(dict(sdk_version=moomoo.__version__,implementation='python-qt')))
        return 0
    if args.benchmark_output:
        os.environ["QT_QPA_PLATFORM"]="offscreen"
        os.environ["QT_SCALE_FACTOR"]="1"
        import moomoo
    if args.render_preview:
        os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from moopython.research import load_rules
    load_rules()  # Validate packaged rule availability before presenting the UI.
    if args.classic or args.benchmark_output:
        from moopython.ui import MainWindow
    else:
        from moopython.research_ui import ResearchWindow as MainWindow
    app=QApplication([sys.argv[0]])
    app.setApplicationName("MooPie")
    settings=None
    if args.benchmark_output:
        from PySide6.QtCore import QSettings
        settings=QSettings(args.benchmark_output+".settings.ini",QSettings.Format.IniFormat)
        settings.clear()
    window=(MainWindow(settings=settings) if args.classic or args.benchmark_output else
            MainWindow(settings=settings, auto_load=not args.render_preview))
    window.show()
    if hasattr(window, 'port'): window.port.setValue(args.port)
    if args.benchmark_output:
        from moopython.benchmark import start
        start(window,args.benchmark_output)
    if args.classic and not args.render_preview and not args.benchmark_output:
        QTimer.singleShot(300,lambda:window.runtime.run('launch'))
        window.opend_update_timer=QTimer(window)
        window.opend_update_timer.setInterval(24*60*60*1000)
        window.opend_update_timer.timeout.connect(lambda:window.runtime.run('check'))
        window.opend_update_timer.start()
    if args.host and hasattr(window, 'connect_gateway'):
        QTimer.singleShot(100,lambda:window.connect_gateway(args.host,args.port))
    if args.render_preview:
        def render():
            window.grab().save(args.render_preview)
            window.close()
        QTimer.singleShot(300,render)
    if args.quit_after:
        QTimer.singleShot(args.quit_after*1000,window.close)
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
