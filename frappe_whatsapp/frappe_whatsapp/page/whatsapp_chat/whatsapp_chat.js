frappe.pages['whatsapp_chat'].on_page_load = function(wrapper) {
	// Create app container
	const appContainer = $('<div id="app" style="width:100%; height:100vh;"></div>');
	$(wrapper).html(appContainer);
	
	// Hide Frappe page chrome for full-screen experience
	$(wrapper).find('.page-head').hide();
	$(wrapper).closest('.page-container').css({
		'margin': '0',
		'padding': '0',
		'max-width': '100%',
		'width': '100%',
		'height': '100vh',
		'overflow': 'hidden'
	});
	$('.layout-main-section').css({'padding': '0', 'border': 'none'});
	$('body').css('overflow', 'hidden');
	
	// Load Vite-built CSS
	if (!$('link[href*="index-B2w67d6c.css"]').length) {
		$('<link rel="stylesheet" href="/assets/frappe_whatsapp/frontend/assets/index-B2w67d6c.css">').appendTo('head');
	}
	
	// Load and execute Vite-built JS
	import('/assets/frappe_whatsapp/frontend/assets/index-D8YXFPHY.js')
		.then(() => {
			console.log('WhatsApp Chat frontend loaded');
		})
		.catch(err => {
			console.error('Failed to load frontend:', err);
			frappe.show_alert({message: 'Failed to load WhatsApp Chat', indicator: 'red'});
		});
};
