#!/bin/bash

set -euxo pipefail

pkgname="namban"
arch="all"
maintainer="meshya, D3F4U1T"
pkgdesc="A simple gui tool for set dns settings."
srcdir="$(pwd)"
# Adw.BottomSheet needs libadwaita >= 1.6 (Debian 13+)
depends=(
	"python3"
	"python3-gi"
	"gir1.2-gtk-4.0"
	"gir1.2-adw-1 (>= 1.6)"
	"systemd-resolved"
)

prepare() {
	pkgver="${REL_TAGNAME:?REL_TAGNAME must be set to the release tag}"
	pkgver="${pkgver#v}"
	pkgdir="$srcdir/${pkgname}_${pkgver}_${arch}"
	rm -rf "$pkgdir"
}

package() {
	mkdir -p "$pkgdir/DEBIAN"
	cp -r "$srcdir/package/files/rootfs/." "$pkgdir/"
	cp -r "$srcdir/src" "$pkgdir/usr/lib/namban/src"
	find "$pkgdir" -name __pycache__ -prune -exec rm -rf {} +

	depends_str="$(printf '%s, ' "${depends[@]}")"
	depends_str="${depends_str%, }"

	cat > "$pkgdir/DEBIAN/control" <<-EOF
	Package: $pkgname
	Version: $pkgver
	Architecture: $arch
	Maintainer: $maintainer
	Depends: $depends_str
	Suggests: dnscrypt-proxy
	Description: $pkgdesc
	EOF

	chmod +x "$pkgdir/usr/bin/namban" "$pkgdir"/usr/lib/namban/namban-*
	chmod 644 "$pkgdir/usr/share/polkit-1/actions/com.parchlinux.namban.policy"

	dpkg-deb --build --root-owner-group "$pkgdir"
}

prepare
package
