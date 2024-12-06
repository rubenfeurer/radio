const colors = require('tailwindcss/colors')

module.exports = {
  content: [
    './src/**/*.{html,svelte,js,ts}',
    './node_modules/flowbite-svelte/**/*.{html,js,svelte,ts}'
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#71717a',
          600: '#000000',
          700: '#000000',
          800: '#000000',
          900: '#000000',
        }
      }
    }
  },
  plugins: [
    require('flowbite/plugin')
  ],
  darkMode: 'class'
} 