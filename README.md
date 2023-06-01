[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/inventree-wireviz-plugin)](https://pypi.org/project/inventree-wireviz-plugin/)
![PEP](https://github.com/inventree/inventree-wireviz/actions/workflows/pep.yaml/badge.svg)

# inventree-wireviz

The **inventree-wireviz** plugin provides direct integration for [wireviz](https://github.com/formatc1702/WireViz), a text-based wiring harness specification tool.

## Functionality

The plugin provides a number of key functions:

### Harness Diagram Generation

This plugin provides server-side generation of a wiring harness diagram from a `.wireviz` file. Uploading a simple [harness file](./demo/harness.wireviz) results in the generation of a wiring diagram:

![](./demo/harness.svg)

Refer to the [wireviz syntax guide](https://github.com/formatc1702/WireViz/blob/master/docs/syntax.md) for a full description of the file format.

The generated harness diagram is available as a `.svg` file.

### BOM Extraction

Bill of Materials (BOM) information can be extracted directly from the harness description file, allowing for a harness assembly to be fully qualified from the template file.

### Report Generation

The generated `.svg` can be used in report templates, for example as a reference diagram in a Build Order Report

## Installation

### Installation Requirements

You must have [graphviz](https://graphviz.org/) installed, and accessible by the InvenTree server.

e.g. `apt-get install graphviz`

If installing in a container environment (e.g. Docker), the dockerfile will need to be extended to install the *graphviz* binaries

### Plugin Installation

The plugin is available [via PIP](https://pypi.org/project/inventree-wireviz-plugin/). Follow the [InvenTree plugin installation guide](https://docs.inventree.org/en/latest/extend/plugins/install/) to install the plugin on your system

### Configuration

Once the plugin is installed, it needs to be enabled before it is available for use. Again, refer to the InvenTree docs for instructions on how to enable the plugin. After the plugin is enabled, the following configuration options are available:

![](./docs/config.png)

| Setting | Description |
| --- | --- |
| Wireviz Upload Path | Directory where wireviz *template* files can be uploaded, and referenced by wireviz. This is an *advanced* option. Refer to the wireviz docs for more information on templates. |
| Delete Old Files | Remove old harness diagram files when a new `.wireviz` file is uploaded |
| Extract BOM Data | Extract BOM data from harness file and generate new BOM entries |
| Clear BOM Data | Remove existing BOM entries first, before creating new ones |
| Add Part Image | Where available, embed part images in the generated harness diagram |

## Operation

### Template Files

**TODO**
### Part Images

**TODO**
## Wireviz Documentation

Documentation on the capabilities of wireviz itself:

- https://github.com/formatc1702/WireViz/blob/master/docs/README.md
- https://github.com/formatc1702/WireViz/blob/master/docs/syntax.md
