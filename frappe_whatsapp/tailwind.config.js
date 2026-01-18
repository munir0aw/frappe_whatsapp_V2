module.exports = {
	content: [
		"./frappe_whatsapp/public/**/*.{js,vue,html}",
		"./frappe_whatsapp/**/*.{js,vue,html}"
	],
	darkMode: 'class', // Enable class-based dark mode
	theme: {
		extend: {
			colors: {
				'whatsapp-green': '#25D366',
				'whatsapp-teal': '#128C7E',
				'whatsapp-light': '#DCF8C6',
			}
		}
	},
	plugins: []
}
