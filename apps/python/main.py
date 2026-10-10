import argparse
import os
import sys

def main():
    parser=argparse.ArgumentParser(description="MooPython desktop market client")
    parser.add_argument("--render-preview")
    parser.add_argument("--sdk-check", action="store_true")
    parser.add_argument("--quit-after",type=int,default=0)
    parser.add_argument("--host")
    parser.add_argument("--port",type=int,default=11111)
    args=parser.parse_args()
    if args.sdk_check:
        import moomoo
        assert callable(moomoo.OpenQuoteContext)
        print("Official moomoo SDK import passed")
        return 0
    if args.render_preview:
        os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from moopython.ui import MainWindow
    app=QApplication([sys.argv[0]])
    app.setApplicationName("MooPython")
    window=MainWindow(); window.show()
    if args.host:
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
