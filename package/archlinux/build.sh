#!/bin/bash
set -eo pipefail

ziperrorandexit() {
    echo make sure you have zip installed and you are in archlinux directory
    exit 1
}
buildicon() {
    echo "Starting Icon build"
    cd ../files
    bash ./build-icon.sh
    cd ../archlinux
}
main () {
    buildicon
    rm -rf build
    mkdir -p build
    cd ../..
    rm -rf src/**/__pycache__
    zip -r package/archlinux/build/namban-source.zip src || ziperrorandexit
    cd package/files
    zip -r ../archlinux/build/namban-source.zip rootfs || ziperrorandexit
    cd ../archlinux || return
    cp PKGBUILD build
    # On release CI, version the package from the tag (pacman forbids '-' in pkgver)
    if [ -n "${release_name:-}" ]; then
        ver="${release_name#v}"
        sed -i "s/^pkgver=.*/pkgver=${ver//-/_}/; s/^pkgrel=.*/pkgrel=1/" build/PKGBUILD
    fi
    cd build || return
    makepkg -sc
    cd ..
}

main
