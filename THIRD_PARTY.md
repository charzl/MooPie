# Third-party components

- Moomoo C++ SDK 10.11.7108: official source distribution downloaded from https://www.moomoo.com/download/OpenAPI. Copyright 2026 Moomoo. Vendored unchanged except generated protobuf files are omitted from Git and regenerated during builds. The distribution does not contain a standalone SDK license granting MIT rights; it is not covered by our MIT license.
- Included protobuf 3.21.5 source archive: upstream license is contained inside its source archive. Packaged C++ applications include `THIRD_PARTY_LICENSES/protobuf-LICENSE`.
- Included OpenSSL 3.0.17 source archive: Apache License 2.0; packaged C++ applications include `THIRD_PARTY_LICENSES/openssl-LICENSE.txt`.
- moomoo-api 10.11.7108: official Python SDK, installed from PyPI. Retains its upstream terms.
- PySide6 / Qt: upstream LGPL/GPL/commercial licenses as applicable; packaged with their corresponding distribution metadata and license files by PyInstaller.

No official OpenD executable, moomoo desktop assets, account information or credentials are included in this repository.
