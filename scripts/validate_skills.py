"""Dependency-free checks for this repository's deliberately simple skill format.

This is a structural check, not an agent behavior or scientific quality test.
Run the installed skill-creator quick_validate.py as an additional check when available.
"""
from pathlib import Path
import re
import sys


def validate(root: Path) -> list[str]:
    errors = []
    skills = sorted((root / '.agents' / 'skills').glob('*/SKILL.md'))
    if not skills:
        return ['No repository skills found']
    names = set()
    for path in skills:
        text = path.read_text(encoding='utf-8-sig')
        label = path.relative_to(root).as_posix()
        parts = text.split('---', 2)
        if not text.startswith('---\n') or len(parts) < 3:
            errors.append(f'{label}: missing YAML frontmatter')
            continue
        fields = {}
        for line in parts[1].splitlines():
            if ':' in line and not line.startswith(' '):
                key, value = line.split(':', 1)
                fields[key] = value.strip().strip('\"\'')
        name = fields.get('name', '')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or len(name) >= 64:
            errors.append(f'{label}: invalid name')
        if name != path.parent.name or name in names:
            errors.append(f'{label}: folder/name mismatch or duplicate name')
        names.add(name)
        if not fields.get('description') or len(fields['description']) > 1024:
            errors.append(f'{label}: description missing or too long')
        if len(parts[2].strip()) < 50:
            errors.append(f'{label}: instructions too short')
        for link in re.findall(r'\]\(([^)]+)\)', parts[2]):
            if '://' in link or link.startswith('#'):
                continue
            target = link.split('#', 1)[0]
            if target and not (path.parent / target).exists():
                errors.append(f'{label}: broken local link {target}')
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate(root)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    count = len(list((root / '.agents' / 'skills').glob('*/SKILL.md')))
    print(f'{count} skills: frontmatter, names and local links OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
