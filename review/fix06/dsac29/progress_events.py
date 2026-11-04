"""Timestamped progress. Counters describe a named stage, never a guessed total."""
import json
import os
import re
import time


class ProgressEvents:
    def __init__(self, path):
        self.path = path
        self.phase = 'Uruchamianie'
        self.durable_phases = os.environ.get('DSCOMPARE_DURABLE_PHASES', '') == '1'

    def __call__(self, message):
        message = str(message)
        stages = (
            ('Wczytywanie', 'Import STEP'), ('Import ', 'Import STEP'),
            ('Etap 1/3: sprawdzanie', 'Zgodność położenia'),
            ('etap 2/3: przesunięte', 'Ruch części'), ('Etap transformacji', 'Ruch części'),
            ('Weryfikacja przesunięcia', 'Weryfikacja wyrównania B-Rep'),
            ('Zmiany materiału', 'Weryfikacja materiału'),
            ('budowanie kolorowego STEP', 'Eksport STEP'),
            ('BOM', 'Zestawienie BOM'), ('Podgląd', 'Podgląd 3D'),
            ('Generowanie niezależnego podglądu', 'Podgląd 3D'),
            ('Finalizowanie', 'Finalizacja'), ('Gotowe:', 'Zakończono'),
        )
        previous_phase = self.phase
        for trigger, label in stages:
            if trigger in message:
                self.phase = label
                break
        data = {'tekst': message, 'timestamp_ms': round(time.time() * 1000), 'phase': self.phase}
        # Only explicit completed/total stage counters are progress percentages.
        match = re.search(r'(?:Etap zgodności|Etap transformacji|Weryfikacja przesunięcia B-Rep|R17: geometria rewizji|Podgląd HTML|BOM: grupowanie):?\s*(\d+)/(\d+)', message)
        if match:
            data.update(completed=int(match[1]), total=int(match[2]))
        checks = re.search(r'; B-Rep:\s*(\d+)|,\s*test\s+(\d+)', message)
        if checks:
            data['checks'] = int(checks[1] or checks[2])
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(data, ensure_ascii=False) + '\n')
            stream.flush()
            # Crash triage: persist phase transitions before entering native OCCT.
            # Opt-in avoids an fsync on every progress event in normal operation.
            if self.durable_phases and self.phase != previous_phase:
                os.fsync(stream.fileno())
