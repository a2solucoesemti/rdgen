"""Render the small supported SVG subset without external SVG/font dependencies.

Requires ImageMagick 7 (`magick`). SVG files are the editable sources.
Run from any directory; writes only the checked-in Connect Windows assets.
"""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ASSETS = Path(__file__).resolve().parents[2] / '.github/assets/connect/windows'


def magick(*args):
    values = list(map(str, args))
    subprocess.run(['magick', *values[:-1], '-strip', values[-1]], check=True)


def literal(value):
    if "'" in value or '\n' in value:
        raise ValueError('Unsupported SVG attribute')
    return "'" + value + "'"


def render(source, destination, size):
    svg = ET.parse(source).getroot()
    if svg.attrib['viewBox'] != '0 0 64 64':
        raise ValueError('Expected a 64-unit viewBox')
    commands = ['scale 16,16']
    for node in svg:
        attr = node.attrib
        commands.extend([
            'fill ' + literal(attr.get('fill', 'none')),
            'stroke ' + literal(attr.get('stroke', 'none')),
            'stroke-width ' + attr.get('stroke-width', '1'),
            'stroke-linecap ' + attr.get('stroke-linecap', 'round'),
            'stroke-linejoin ' + attr.get('stroke-linejoin', 'round'),
        ])
        tag = node.tag.split('}')[-1]
        if tag == 'rect':
            x, y = float(attr['x']), float(attr['y'])
            right, bottom = x + float(attr['width']), y + float(attr['height'])
            radius = attr.get('rx', '0')
            commands.append(f'roundrectangle {x},{y} {right},{bottom} {radius},{radius}')
        elif tag == 'path':
            commands.append('path ' + literal(attr['d']))
        else:
            raise ValueError(f'Unsupported SVG element: {tag}')
    magick('-size', '1024x1024', 'xc:none', '-draw', ' '.join(commands),
           '-resize', f'{size}x{size}', destination)


def main():
    render(ASSETS / 'icon.svg', ASSETS / 'icon.png', 256)
    render(ASSETS / 'tray-icon.svg', ASSETS / 'tray-icon.png', 64)
    for name, size in [('32x32', 32), ('64x64', 64), ('128x128', 128), ('128x128@2x', 256)]:
        magick(ASSETS / 'icon.png', '-resize', f'{size}x{size}', ASSETS / f'{name}.png')
    for name, sizes in [('icon', '256,128,64,48,32,24,20,16'),
                        ('window-icon', '64,48,32,24,20,16')]:
        magick(ASSETS / 'icon.png', '-define', f'icon:auto-resize={sizes}', ASSETS / f'{name}.ico')
    magick(ASSETS / 'tray-icon.png', '-define', 'icon:auto-resize=64,48,32,24,20,16',
           ASSETS / 'tray-icon.ico')


if __name__ == '__main__':
    main()
