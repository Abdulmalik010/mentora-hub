# Embedded PDF fonts

Session-notes PDFs embed Inter (SIL OFL 1.1, see OFL.txt).

- Source: https://github.com/google/fonts (ofl/inter), variable font
  `Inter[opsz,wght].ttf` plus the repository's OFL.txt, fetched 2026-10-30.
- `Inter-Regular.ttf` / `Inter-Bold.ttf` are static instances (wght 400 /
  700, opsz 14) produced with fonttools' variable-font instancer.
- Inter is also the app's UI font, so PDFs match the product visually.
- Verified glyph coverage: U+20A6 (₦), U+2192, U+2713, U+2022, U+2014,
  U+00B7, U+2264.
