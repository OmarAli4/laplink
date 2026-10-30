import array
import ast
import struct
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Compiles django.po files into binary django.mo files using pure Python (no external gettext needed).'

    def handle(self, *args, **options):
        locale_dirs = getattr(settings, 'LOCALE_PATHS', [Path(settings.BASE_DIR) / 'locale'])
        for locale_dir in locale_dirs:
            locale_path = Path(locale_dir)
            if not locale_path.exists():
                continue
            for po_file in locale_path.rglob('*.po'):
                mo_file = po_file.with_suffix('.mo')
                self.compile_po_to_mo(po_file, mo_file)
                self.stdout.write(self.style.SUCCESS(f'Compiled {po_file} -> {mo_file}'))

    def compile_po_to_mo(self, po_path: Path, mo_path: Path):
        messages = {}
        current_msgid = None
        current_msgstr = None
        in_msgid = False
        in_msgstr = False
        is_fuzzy = False

        lines = po_path.read_text(encoding='utf-8').splitlines()

        def commit():
            nonlocal current_msgid, current_msgstr, is_fuzzy
            if current_msgid is not None and current_msgstr is not None:
                if not is_fuzzy and (current_msgid == '' or current_msgstr != ''):
                    messages[current_msgid] = current_msgstr
            current_msgid = None
            current_msgstr = None
            is_fuzzy = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                commit()
                in_msgid = False
                in_msgstr = False
                continue
            if line.startswith('#,'):
                if 'fuzzy' in line:
                    is_fuzzy = True
                continue
            if line.startswith('#'):
                continue
            if line.startswith('msgid '):
                if in_msgstr:
                    commit()
                in_msgid = True
                in_msgstr = False
                current_msgid = ast.literal_eval(line[5:].strip())
            elif line.startswith('msgstr '):
                in_msgid = False
                in_msgstr = True
                current_msgstr = ast.literal_eval(line[6:].strip())
            elif line.startswith('"') and line.endswith('"'):
                val = ast.literal_eval(line)
                if in_msgid and current_msgid is not None:
                    current_msgid += val
                elif in_msgstr and current_msgstr is not None:
                    current_msgstr += val

        commit()

        # Sort keys as required by GNU MO binary search format
        keys = sorted(messages.keys())
        offsets = []
        ids = b''
        strs = b''
        for k in keys:
            b_id = k.encode('utf-8')
            b_str = messages[k].encode('utf-8')
            offsets.append((len(ids), len(b_id), len(strs), len(b_str)))
            ids += b_id + b'\x00'
            strs += b_str + b'\x00'

        keystart = 7 * 4 + 16 * len(keys)
        valuestart = keystart + len(ids)
        koffsets = []
        voffsets = []
        for o1, l1, o2, l2 in offsets:
            koffsets += [l1, o1 + keystart]
            voffsets += [l2, o2 + valuestart]

        output = struct.pack(
            'Iiiiiii',
            0x950412de,        # Magic
            0,                 # Version
            len(keys),         # # of entries
            7 * 4,             # start of key index
            7 * 4 + len(keys) * 8,  # start of value index
            0, 0               # size and offset of hash table
        )
        output += array.array('i', koffsets).tobytes()
        output += array.array('i', voffsets).tobytes()
        output += ids
        output += strs

        mo_path.write_bytes(output)
