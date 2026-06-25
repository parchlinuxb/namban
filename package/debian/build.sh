#!/bin/bash

set -x

pkgname="namban"
arch="amd64"
maintainer="meshya, D3F4U1T"
pkgdesc="A simple gui tool for set dns settings."
srcdir="$(pwd)"
depends=(
	"python3"
	"gir1.2-gtk-4.0"
	"python3-gi"
	"libadwaita"
)
makedepends=(
	"git"
)

prepare() {
	apt install "${makedepends[@]}" -y
	apt install "${depends[@]}" -y
	pkgver="$(echo "$REL_TAGNAME" | sed 's/v//g')"
	pkgdir="$(pwd)"/"$pkgname"_"v$pkgver"_"$arch"
}

package() {
	mkdir -p "$pkgdir/"{DEBIAN,'usr/'}
	cp -r "$srcdir/package/files/rootfs/"{usr,etc,lib} "$pkgdir/"
	cp -r "$srcdir/src/" "$pkgdir/usr/lib/namban/src/"

	depends_str="${depends[*]}"
	depends_str="${depends_str// /, }"

	echo "Package: $pkgname
	Version: $pkgver
	Architecture: $arch
	Maintainer: $maintainer
	Depends: $depends_str
	Description: $pkgdesc" | tr -d '\t' > "$pkgdir/DEBIAN/control"

	chmod +x "$pkgdir/usr/"{bin/namban,lib/namban/{namban-emergency-rollback}}

	dpkg-deb --build --root-owner-group "$pkgdir"
}

prepare
package
