"""DS Compare V4.1 entry. Worker mode is kept separate from the UI."""
import sys

if __name__=='__main__':
    if '--dscompare-worker' in sys.argv:
        from dsac29.gui import _worker_main
        sys.exit(_worker_main(sys.argv[1:]))
    elif '--worker' in sys.argv:
        from dsac29.worker_v37 import main
        sys.exit(main(sys.argv[1:]))
    else:
        import argparse
        p=argparse.ArgumentParser()
        p.add_argument('--a',default='')
        p.add_argument('--b',default='')
        p.add_argument('--smoke-test-ui',default='')
        args=p.parse_args()
        if args.smoke_test_ui:
            import json
            from pathlib import Path
            from PySide6.QtWidgets import QApplication
            from dsac29.gui_qt37 import Window
            app=QApplication([]);app.setStyle('Fusion')
            w=Window(args.a,args.b);w.show();app.processEvents()
            output=Path(args.smoke_test_ui);output.mkdir(parents=True,exist_ok=True)
            for key in ('start','compare','results','settings'):
                w.navigate(key);app.processEvents();w.grab().save(str(output/(key+'.png')))
            assert all(not b.icon().isNull() for b in w.nav.values())
            w.close()
            (output/'UI_OK.json').write_text(json.dumps({'version':'4.1','pages':4,'icons':6}))
            sys.exit(0)
        from dsac29.gui_qt37 import main
        sys.exit(main(args.a,args.b))
