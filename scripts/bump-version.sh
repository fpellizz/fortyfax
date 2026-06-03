#!/bin/bash
# Allinea la versione in tutti i punti che la dichiarano:
#   fortyfax/__init__.py  (fonte primaria, letta anche da pyproject.toml)
#   packaging/rpm/fortyfax.spec
#   debian/changelog      (nuova entry in testa)
#
# Usage: ./scripts/bump-version.sh 2.3.4 ["riga di changelog"]
set -euo pipefail

cd "$(dirname "$0")/.."

NEW="${1:?Usage: $0 <versione> [\"riga di changelog\"]}"
NOTE="${2:-Nuova release.}"

[[ "$NEW" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "❌ Versione non valida: $NEW (atteso X.Y.Z)"; exit 1; }

OLD=$(python3 -c "
import sys; sys.path.insert(0, '.')
from fortyfax import __version__; print(__version__)
")

# __init__.py
sed -i "s/__version__ = \"$OLD\"/__version__ = \"$NEW\"/" fortyfax/__init__.py

# spec (Version + entry nel %changelog)
sed -i "s/^Version:        $OLD/Version:        $NEW/" packaging/rpm/fortyfax.spec
SPEC_DATE=$(LC_ALL=C date '+%a %b %d %Y')
sed -i "/^%changelog/a * ${SPEC_DATE} Fabio Pellizzaro <fabio.pellizzaro@decisyon.com> - ${NEW}-1\n- ${NOTE}\n" packaging/rpm/fortyfax.spec

# debian/changelog (nuova entry in testa)
DEB_DATE=$(LC_ALL=C date -R)
TMP=$(mktemp)
cat > "$TMP" <<EOF
fortyfax (${NEW}) unstable; urgency=medium

  * ${NOTE}

 -- Fabio Pellizzaro <fabio.pellizzaro@decisyon.com>  ${DEB_DATE}

EOF
cat debian/changelog >> "$TMP"
mv "$TMP" debian/changelog

echo "✓ Versione: $OLD → $NEW"
grep -H "__version__" fortyfax/__init__.py
grep -H "^Version:" packaging/rpm/fortyfax.spec
head -1 debian/changelog
