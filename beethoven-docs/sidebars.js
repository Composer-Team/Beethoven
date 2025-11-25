// @ts-check

/**
 * Sidebars configuration for Beethoven documentation.
 *
 * @type {import('@docusaurus/plugin-content-docs').SidebarsConfig}
 */
const sidebars = {
  beethoven: [
    'getting-started',
    {
      type: 'category',
      label: 'Hardware Stack',
      collapsed: false,
      link: {
        type: 'doc',
        id: 'hardware/overview',
      },
      items: [
        'hardware/overview',
        'hardware/memory',
        'hardware/verilog',
        'hardware/asic-memory-compiler',
        'hardware/cross-core',
      ],
    },
    {
      type: 'category',
      label: 'Software Stack',
      collapsed: false,
      link: {
        type: 'doc',
        id: 'software/overview',
      },
      items: [
        'software/overview',
        'software/cmake',
      ],
    },
    {
      type: 'category',
      label: 'Platforms',
      collapsed: false,
      items: [
        'platforms/kria',
        'platforms/aws-f2',
        'platforms/custom-platform',
      ],
    },
    {
      type: 'category',
      label: 'IDE Integration',
      collapsed: true,
      items: [
        'ide/overview',
      ],
    },
    'links',
  ],
};

export default sidebars;
