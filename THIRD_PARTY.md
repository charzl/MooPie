# Third-party components

- moomoo-api 10.11.7108: official Python SDK, installed from PyPI. Retains its upstream terms.
- PySide6 / Qt: upstream LGPL/GPL/commercial licenses as applicable; packaged with their corresponding distribution metadata and license files by PyInstaller.
- Noto Sans SC variable font: Copyright 2014–2021 Adobe; SIL Open Font License 1.1. Unmodified font from [Google Fonts](https://github.com/google/fonts/tree/main/ofl/notosanssc), SHA-256 `a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da`. Font and license are distributed together in `apps/python/moopython/fonts/` so Chinese and Latin text render without system font installation.

No official OpenD executable, moomoo desktop assets, account information or credentials are included in this repository.

## Official moomoo OpenD runtime

MooPie installs the unchanged, proprietary official GUI OpenD separately. The distribution is obtained from [moomoo's download page](https://www.moomoo.com/download/OpenAPI). Original publisher signatures and embedded notices remain intact. The repository's MIT license applies to our integration/updater code, not OpenD. The build archive is pinned in `runtime/opend.json`; binaries, account data and caches are not committed to Git. Runtime updates are downloaded from moomoo and checked against the official Developer ID publisher identity before selection.
