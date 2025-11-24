// @ts-check
// `@type` JSDoc annotations allow editor autocompletion and type checking
// (when paired with `@ts-check`).
// There are various equivalent ways to declare your Docusaurus config.
// See: https://docusaurus.io/docs/api/docusaurus-config

import {themes as prismThemes} from 'prism-react-renderer';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Beethoven',
  tagline: '',
  favicon: 'img/favicon.png',

  // Set the production url of your site here
  url: 'https://composer-team.github.io',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/Beethoven-Docs/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'Composer-Team', // Usually your GitHub org/user name.
  projectName: 'Beethoven-Docs', // Usually your repo name.

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: false,
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      // Replace with your project's social card
      image: 'img/docusaurus-social-card.jpg',
      navbar: {
        title: 'Beethoven',
        logo: {
          alt: 'My Site Logo',
          src: 'img/favicon.png',
        },
        items: [
          {to: '/Beethoven', label: 'Getting Started', position: 'left'},
          {
            position: 'left',
            label: 'Beethoven Project Template',
            to: 'https://github.com/Composer-Team/Beethoven-Template'
          },
          {
            href: 'https://github.com/Composer-Team/Beethoven-Hardware',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Documentation',
            items: [
              {
                label: 'Getting Started',
                to: '/Beethoven',
              },
              {
                label: 'Hardware Stack',
                to: '/Beethoven/HW',
              },
              {
                label: 'Software Stack',
                to: '/Beethoven/SW',
              },
            ],
          },
          {
            title: 'Platforms',
            items: [
              {
                label: 'Kria/Zynq',
                to: '/Beethoven/Platform/Kria',
              },
              {
                label: 'AWS F2',
                to: '/Beethoven/Platform/AWSF',
              },
              {
                label: 'New Platform Guide',
                to: '/Beethoven/Platform/NewPlatform',
              },
            ],
          },
          {
            title: 'Resources',
            items: [
              {
                label: 'Beethoven Hardware',
                href: 'https://github.com/Composer-Team/Beethoven-Hardware',
              },
              {
                label: 'Beethoven Software',
                href: 'https://github.com/Composer-Team/Beethoven-Software',
              },
              {
                label: 'Project Template',
                href: 'https://github.com/Composer-Team/Beethoven-Template',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Composer Team. Built with Docusaurus.`,
      },
      prism: {
	additionalLanguages: ['verilog', 'java'],
      },
    }),
};

export default config;
