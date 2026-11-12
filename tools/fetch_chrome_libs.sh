#!/usr/bin/env bash
# Download the shared libs chrome-headless-shell needs but minimal containers lack, into .tools/chromelibs.
set -e
KIT="$(cd "$(dirname "$0")/.." && pwd)"; D="$KIT/.tools/chromelibs"; mkdir -p "$D/debs"; cd "$D/debs"
ARCH=$(dpkg --print-architecture 2>/dev/null || echo arm64)
P=https://deb.debian.org/debian/pool/main
for f in a/at-spi2-core/libatk1.0-0t64_2.56.2-1+deb13u2 a/at-spi2-core/libatspi2.0-0t64_2.56.2-1+deb13u2 \
         libx/libxcomposite/libxcomposite1_0.4.6-1+b2 libx/libxdamage/libxdamage1_1.1.6-1+b2; do
  curl -sfL -m 60 -O "$P/${f}_${ARCH}.deb" || true
done
for d in *.deb; do dpkg-deb -x "$d" "$D/root"; done
echo "libs in $D/root/usr/lib"
