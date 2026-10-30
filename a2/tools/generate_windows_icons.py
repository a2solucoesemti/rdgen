"""Package the supplied official A2 logo without recreating its lettering.

Requires ImageMagick 7. The original PNG is kept unchanged. Only the bottom
40 rows containing the tagline are cropped. Icons preserve the mark's aspect
ratio, with transparent padding to make square Windows resources.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / '.github/assets/connect/windows'
OFFICIAL = ROOT / '.github/assets/connect/official'


def magick(*args):
    values = list(map(str, args))
    subprocess.run(['magick', *values[:-1], '-strip', values[-1]], check=True)


def render(size, destination):
    magick(OFFICIAL / 'logo-sem-legenda.png', '-resize', f'{size}x{size}',
           '-background', 'none', '-gravity', 'center', '-extent', f'{size}x{size}', destination)


def main():
    magick(OFFICIAL / 'logo-original.png', '-crop', '300x160+0+0', '+repage',
           OFFICIAL / 'logo-sem-legenda.png')
    render(256, ASSETS / 'icon.png')
    render(64, ASSETS / 'tray-icon.png')
    for name, size in [('32x32', 32), ('64x64', 64), ('128x128', 128), ('128x128@2x', 256)]:
        render(size, ASSETS / f'{name}.png')
    for name, sizes in [('icon', '256,128,64,48,32,24,20,16'),
                        ('window-icon', '64,48,32,24,20,16')]:
        magick(ASSETS / 'icon.png', '-define', f'icon:auto-resize={sizes}', ASSETS / f'{name}.ico')
    magick(ASSETS / 'icon.png', '-define', 'icon:auto-resize=64,48,32,24,20,16',
           ASSETS / 'tray-icon.ico')


if __name__ == '__main__':
    main()
