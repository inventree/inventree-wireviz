import { renderPanel } from './WirevizPanel.tsx'

/**
 * Demo for rendering the Wireviz panel with some sample content
 */
renderPanel(
  document.getElementById('root'),
  {
    context: {
      // Some example data, this would normally be loaded from the server
      "part": 123,
      "wireviz_svg_file": "/media/attachments/part/123/wireviz_harness.svg",
      "wireviz_source_file": "/media/attachments/part/123/harness.wireviz",
      "wireviz_bom_data": [
          {
              "pn": null,
              "idx": 1,
              "mpn": null,
              "spn": null,
              "unit": "m",
              "quantity": 0.2,
              "sub_part": null,
              "description": "Cable, 3 x 0.25 mm² shielded",
              "designators": "W1"
          },
          {
              "pn": null,
              "idx": 2,
              "mpn": null,
              "spn": null,
              "unit": null,
              "quantity": 1.0,
              "sub_part": null,
              "description": "Connector, D-Sub, female, 9 pins",
              "designators": "X1"
          },
          {
              "pn": null,
              "idx": 3,
              "mpn": null,
              "spn": null,
              "unit": null,
              "quantity": 1.0,
              "sub_part": null,
              "description": "Connector, Molex KK 254, female, 3 pins",
              "designators": "X2"
          }
      ],
      "wireviz_warnings": [
        "Warning: No part number specified for BOM item 1",
        "Warning: No part number specified for BOM item 2",
      ],
      "wireviz_errors": [
        "Error: An unexpected error occurred while processing the wireviz file",
      ]
    }
  }
);
