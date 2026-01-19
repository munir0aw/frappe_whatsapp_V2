frappe.pages['whatsapp_chat'].on_page_load = function(wrapper) {
	// Create app container
	const appContainer = $('<div id="app" style="width:100%; height:100vh;"></div>');
	$(wrapper).html(appContainer);
	
	// Hide ALL Frappe UI chrome for true full-screen experience
	$('.navbar').hide();
	$('.page-head').hide();
	$('.page-title').hide();
	$('.page-actions').hide();
	$('.layout-side-section').hide();
	
	// Reset all padding/margins for full-screen
	$(wrapper).closest('.page-container').css({
		'margin': '0 !important',
		'padding': '0 !important',
		'max-width': '100%',
		'width': '100%',
		'height': '100vh',
		'overflow': 'hidden'
	});
	
	$('.layout-main-section').css({
		'padding': '0 !important',
		'border': 'none',
		'margin': '0 !important'
	});
	
	$('.layout-main-section-wrapper').css({
		'padding': '0 !important',
		'margin': '0 !important'
	});
	
	$('body').css('overflow', 'hidden');
	
	// Dynamically load Vite assets from manifest
	fetch('/assets/frappe_whatsapp/frontend/.vite/manifest.json')
		.then(res => res.json())
		.then(manifest => {
			// Load CSS
			const cssFile = manifest['src/main.js']?.css?.[0] || manifest['index.html']?.css?.[0];
			if (cssFile && !$(`link[href*="${cssFile}"]`).length) {
				$(`<link rel="stylesheet" href="/assets/frappe_whatsapp/frontend/${cssFile}">`).appendTo('head');
			}
			
			// Load JS
			const jsFile = manifest['src/main.js']?.file || manifest['index.html']?.file;
			if (jsFile) {
				return import(`/assets/frappe_whatsapp/frontend/${jsFile}`);
			}
		})
		.then(() => {
			console.log('WhatsApp Chat frontend loaded');
		})
		.catch(err => {
			console.error('Failed to load frontend:', err);
			// Fallback: try to load latest files directly
			import('/assets/frappe_whatsapp/frontend/assets/index-BCHr-Ib7.js')
				.then(() => {
					$('<link rel="stylesheet" href="/assets/frappe_whatsapp/frontend/assets/index-DliS8rQe.css">').appendTo('head');
					console.log('WhatsApp Chat frontend loaded (fallback)');
				})
				.catch(err2 => {
					console.error('Failed to load frontend (fallback):', err2);
					frappe.show_alert({message: 'Failed to load WhatsApp Chat', indicator: 'red'});
				});
		});
};
