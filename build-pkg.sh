#!/bin/bash
# Build dei pacchetti Fortyfax con gli strumenti nativi delle distro:
#   RPM: rpmbuild + packaging/rpm/fortyfax.spec (Fedora Packaging Guidelines)
#   DEB: dpkg-buildpackage + debian/ (Debian Policy)
#
# Usage:
#   ./build-pkg.sh          # entrambi (richiede entrambe le toolchain)
#   ./build-pkg.sh rpm      # solo RPM (richiede rpm-build, python3-devel, desktop-file-utils)
#   ./build-pkg.sh deb      # solo DEB (richiede debhelper, dpkg-dev)
#
# I pacchetti finiscono in dist/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

NAME="fortyfax"
VERSION=$(python3 -c "
import sys; sys.path.insert(0, '.')
from fortyfax import __version__; print(__version__)
")

# --- Coerenza versioni: __init__.py è la fonte, spec e changelog devono combaciare
SPEC_VERSION=$(awk '/^Version:/{print $2; exit}' packaging/rpm/fortyfax.spec)
DEB_VERSION=$(head -1 debian/changelog | sed -E 's/.*\(([^)]+)\).*/\1/')
if [[ "$SPEC_VERSION" != "$VERSION" || "$DEB_VERSION" != "$VERSION" ]]; then
    echo "❌ Versioni non allineate:" >&2
    echo "   fortyfax/__init__.py : $VERSION" >&2
    echo "   packaging/rpm/*.spec : $SPEC_VERSION" >&2
    echo "   debian/changelog     : $DEB_VERSION" >&2
    echo "   Allineale prima di buildare (vedi scripts/bump-version.sh)." >&2
    exit 1
fi

OUTDIR="$SCRIPT_DIR/dist"
mkdir -p "$OUTDIR"
BUILD_WHAT="${1:-all}"

echo "── Fortyfax v${VERSION} — build pacchetti (${BUILD_WHAT}) ──"

# --- RPM ---
if [[ "$BUILD_WHAT" == "all" || "$BUILD_WHAT" == "rpm" ]]; then
    command -v rpmbuild >/dev/null || { echo "❌ rpmbuild non trovato (dnf install rpm-build python3-devel desktop-file-utils)"; exit 1; }
    echo "→ RPM..."
    RPMTOP=$(mktemp -d)
    trap 'rm -rf "$RPMTOP"' EXIT
    mkdir -p "$RPMTOP"/{SOURCES,SPECS}
    tar czf "$RPMTOP/SOURCES/${NAME}-${VERSION}.tar.gz" \
        --transform "s,^,${NAME}-${VERSION}/," \
        --exclude .git --exclude ./dist --exclude '__pycache__' --exclude '*.pyc' \
        --exclude STEVANATO \
        .
    cp packaging/rpm/fortyfax.spec "$RPMTOP/SPECS/"
    rpmbuild --define "_topdir $RPMTOP" -bb "$RPMTOP/SPECS/fortyfax.spec"
    cp "$RPMTOP"/RPMS/noarch/${NAME}-${VERSION}-*.noarch.rpm "$OUTDIR/"
    echo "  ✓ $(ls "$OUTDIR"/${NAME}-${VERSION}-*.noarch.rpm | tail -1)"
fi

# --- DEB ---
if [[ "$BUILD_WHAT" == "all" || "$BUILD_WHAT" == "deb" ]]; then
    command -v dpkg-buildpackage >/dev/null || { echo "❌ dpkg-buildpackage non trovato (apt install debhelper dpkg-dev)"; exit 1; }
    echo "→ DEB..."
    dpkg-buildpackage -us -uc -b
    mv ../"${NAME}_${VERSION}_all.deb" "$OUTDIR/"
    rm -f ../"${NAME}_${VERSION}"_*.changes ../"${NAME}_${VERSION}"_*.buildinfo
    echo "  ✓ $OUTDIR/${NAME}_${VERSION}_all.deb"
fi

echo "── Build completato — pacchetti in dist/ ──"
ls -lh "$OUTDIR"/*"${VERSION}"* 2>/dev/null
