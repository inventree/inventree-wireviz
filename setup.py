# -*- coding: utf-8 -*-

import importlib
import importlib.util
import os
import setuptools


"""Read the plugin version from the source code."""
module_path = os.path.join(
    os.path.dirname(__file__), "inventree_wireviz", "__init__.py"
)
spec = importlib.util.spec_from_file_location("inventree_wireviz", module_path)
inventree_wireviz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventree_wireviz)

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setuptools.setup(
    name="inventree-wireviz-plugin",
    version=inventree_wireviz.PLUGIN_VERSION,
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
        'wireviz>=0.4.1',
        'pint>=0.24.4',
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
