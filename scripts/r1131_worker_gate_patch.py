"""R11.31 worker: ask once for coordinate registration, never fabricate colors."""
from pathlib import Path
import os
root=Path(os.environ["DS_COMPARE_SOURCE"])
p=root/"dsac29/worker_v37.py"
s=p.read_text(encoding="utf8")
a="    p.add_argument('--align',action='store_true')"
b=a+"\n    p.add_argument('--align-auto',action='store_true',help='Check common coordinates, ask approval if B needs moving')"
assert s.count(a)==1
s=s.replace(a,b,1)
a="""            from .cli import process
            palette=json.loads(ns.palette)"""
b="""            from .cli import process
            import time,uuid
            def approve_alignment(proposal):
                request=folder/'_WYROWNANIE_PYTANIE.json'
                answer=folder/'_WYROWNANIE_ODPOWIEDZ.json'
                try:request.unlink(missing_ok=True);answer.unlink(missing_ok=True)
                except OSError:pass
                token=uuid.uuid4().hex
                info={
                    'token':token,'status':'needs_confirmation',
                    'translation_mm':[round(float(v),3) for v in proposal.get('translation_B_to_A_mm',(0,0,0))],
                    'method':str(proposal.get('method','')),
                    'votes':int(proposal.get('votes',0)),
                    'anchors':int(proposal.get('anchors',0)),
                }
                request.write_text(json.dumps(info,ensure_ascii=False),encoding='utf8')
                emit('Wykryto różnicę położenia całego złożenia. Oczekiwanie na decyzję użytkownika…')
                deadline=time.monotonic()+600
                while time.monotonic()<deadline:
                    if answer.exists():
                        try:
                            resp=json.loads(answer.read_text(encoding='utf8'))
                            if resp.get('token')==token and resp.get('decision') in ('align','cancel'):
                                return resp['decision']
                        except (OSError,ValueError):pass
                    time.sleep(.2)
                raise RuntimeError('Przekroczono czas oczekiwania na decyzję o wyrównaniu (10 minut).')
            palette=json.loads(ns.palette)"""
assert s.count(a)==1,s.count(a)
s=s.replace(a,b,1)
a="colors=palette,progress=emit,align=ns.align,revision_style=ns.revision_style"
b="colors=palette,progress=emit,align=ns.align,auto_align=ns.align_auto,alignment_approval=approve_alignment if ns.align_auto else None,revision_style=ns.revision_style"
assert s.count(a)==1
s=s.replace(a,b,1)
p.write_text(s,encoding='utf8')
print('R11.31 worker: bounded decision handshake, no second import/analysis worker')
