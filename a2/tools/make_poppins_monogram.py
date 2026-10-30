"""Build monochrome A2 SVG outlines from the bundled, OFL-licensed Poppins font.

Requires fonttools. Then run generate_windows_icons.py (ImageMagick 7).
The resulting SVG/ICO files need no fonts installed on the target Windows PC.
"""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / '.github/assets/connect/windows'
FONT = ROOT / '.github/assets/connect/fonts/Poppins-SemiBold.ttf'


def main():
    font = TTFont(FONT)
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    letters = [cmap[ord(char)] for char in 'a2']
    bounds = BoundsPen(glyphs)
    advance = 0
    for name in letters:
        glyphs[name].draw(TransformPen(bounds, (1, 0, 0, 1, advance, 0)))
        advance += font['hmtx'][name][0]
    left, bottom, right, top = bounds.bounds
    scale = min(44 / (right - left), 40 / (top - bottom))
    dx = 32 - (left + right) * scale / 2
    dy = 32 + (top + bottom) * scale / 2
    path = SVGPathPen(glyphs, ntos=lambda value: format(value, '.4f').rstrip('0').rstrip('.'))
    advance = 0
    for name in letters:
        glyphs[name].draw(TransformPen(path, (scale, 0, 0, -scale, dx + advance * scale, dy)))
        advance += font['hmtx'][name][0]
    for name, size, radius, stroke in [('icon', 256, 14, '0'), ('tray-icon', 64, 12, '1.5')]:
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 64 64">
  <!-- Poppins SemiBold, a2 converted to outlines; see ../fonts/OFL.txt. -->
  <rect x="2" y="2" width="60" height="60" rx="{radius}" fill="#000000" stroke="#ffffff" stroke-width="{stroke}"/>
  <path d="{path.getCommands()}" fill="#ffffff"/>
</svg>
'''
        (ASSETS / f'{name}.svg').write_text(svg, encoding='utf-8')


if __name__ == '__main__':
    main()
