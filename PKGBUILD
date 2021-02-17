# Maintainer: Ryu <ryu@tpgjbo.xyz>
pkgname=yolocr
pkgver=0.0.0
pkgrel=1
pkgdesc="YoloCR is a convenient OCR toolkit."
arch=('x86_64')
url="https://github.com/Ryu1845/YoloCR.git"
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
provides=('yolocr'
          'YoloCR'
          'YoloResize'
          'YoloSeuil')
source=("$pkgname::git+$url")

build() {
  cd "$pkgname"
  sed -i "s/config_path = 'config.toml'/#config_path = 'config.toml'/" YoloCR.vpy
  sed -i "s/config_path = 'config.toml'/#config_path = 'config.toml'/" YoloResize.vpy
  sed -i "s/config_path = 'config.toml'/#config_path = 'config.toml'/" YoloSeuil.vpy
  echo "vspipe -y /usr/lib/yolocr/YoloCR.vpy --arg config_path='/etc/yolocr/config.toml' -" > YoloCR
  chmod +x YoloCR
  echo "vspipe -y /usr/lib/yolocr/YoloResize.vpy --arg config_path='/etc/yolocr/config.toml' -" > YoloResize
  chmod +x YoloResize
  echo "vspipe -y /usr/lib/yolocr/YoloSeuil.vpy --arg config_path='/etc/yolocr/config.toml' -" > YoloSeuil
  chmod +x YoloSeuil
}

package() {
  cd "$pkgname"
  install -Dm755 YoloCR "$pkgdir"/usr/bin/YoloCR
  install -Dm755 YoloResize "$pkgdir"/usr/bin/YoloResize
  install -Dm755 YoloSeuil "$pkgdir"/usr/bin/YoloResize
  install -Dm755 YoloCR.sh "$pkgdir"/url/bin/yolocr
  install -Dm644 YoloCR.vpy "$pkgdir"/usr/lib/"$pkgname"/YoloCR.vpy
  install -Dm644 YoloResize.vpy "$pkgdir"/usr/lib/"$pkgname"/YoloResize.vpy
  install -Dm644 YoloSeuil.vpy "$pkgdir"/usr/lib/"$pkgname"/YoloSeuil.vpy
  install -Dm644 config.toml.example "$pkgdir"/etc/"$pkgname"/config.toml
  install -Dm644 README "$pkgdir"/usr/share/doc/"$pkgname"/README
  install -Dm644 README_EN.md "$pkgdir"/usr/share/doc/"$pkgname"/README_EN
}
md5sums=('SKIP')
