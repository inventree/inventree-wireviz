# -*- coding: utf-8 -*-

import pathlib
import setuptools
import shutil

from inventree_wireviz.version import PLUGIN_VERSION

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

# Copy the compiled frontend files into the 'static' directory
# Required for MANIFEST.in to work correctly
src_dir = pathlib.Path('frontend/dist/static')
dst_dir = pathlib.Path('inventree_wireviz/static')

# Clean out the destination directory
if dst_dir.exists():
    shutil.rmtree(dst_dir)

shutil.copytree(src_dir, dst_dir)

setuptools.setup(
    name="inventree-wireviz-plugin",
    version=PLUGIN_VERSION,
    author="Oliver Walters",
    author_email="oliver.henry.walters@gmail.com",
    description="Wireviz plugin for InvenTree",
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords="inventree inventory wireviz wiring cable harness",
    url="https://github.com/inventree/inventree-wireviz",
    license="MIT",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=[
        'wireviz',
        'pint',
    ],
    setup_requires=[
        "wheel",
        "twine",
    ],
    python_requires=">=3.9",
    entry_points={
        "inventree_plugins": [
            "WirevizPlugin = inventree_wireviz.wireviz:WirevizPlugin"
        ]
    },
)
