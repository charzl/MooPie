"""JSON file interface shared by a desktop client or an AI analysis caller."""
import argparse
import json
from pathlib import Path
from .engine import load_rules, scan


def main():
    parser = argparse.ArgumentParser(description='Screen completed daily bars using versioned rules')
    parser.add_argument('input', type=Path)
    parser.add_argument('--rules', type=Path, help='External declarative JSON ruleset')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = scan(json.loads(args.input.read_text(encoding='utf-8')), load_rules(args.rules))
        text = json.dumps(result, indent=2, allow_nan=False) + '\n'
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(2, f'Scan failed: {error}\n')


if __name__ == '__main__':
    main()
