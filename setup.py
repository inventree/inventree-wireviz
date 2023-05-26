# -*- coding: utf-8 -*-

import setuptools

from inventree_wireviz.version import PLUGIN_VERSION

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setuptools.setup(
    name="inventree-wireviz-plugin",
    version=PLUGIN_VERSION,
    author="Oliver Walters",
    author_email="oliver.henry.walters@gmail.com",
    description="Wireviz plugin for InvenTree",
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords="inventree inventory wireviz wiring cable harness",
    url="https://github.com/inventree/inventree-wireviz-plugin",
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
