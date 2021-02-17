# Maintainer: Ryu <ryu@tpgjbo.xyz>
pkgname=yolocr
pkgver=0.0.0
pkgrel=1
pkgdesc="YoloCR is a convenient OCR toolkit."
arch=('x86_64')
url="https://bitbucket.org/YuriZero/yolocr/src/master/"
license=('GPL')
depends=('ffms2'
         'vapoursynth'
         'ffmpeg'
         'vapoursynth-plugin-havsfunc-git'
         'tesseract'
         'imagemagick'
         'parallel')
makedepends=()
optdepends=('vapoursynth-plugin-edi_rpow2-git' 
            'vapoursynth-plugin-waifu2x-w2xc-git'
            'tesseract-data-eng'
            'tesseract-data-fra')
provides=()
backup=()
options=()
install=
changelog=
source=($pkgname-$pkgver.tar.gz)
noextract=()
md5sums=() #autofill using updpkgsums

build() {
  cd "$pkgname-$pkgver"

  ./configure --prefix=/usr
  make
}

package() {
  cd "$pkgname-$pkgver"

  make DESTDIR="$pkgdir/" install
}
