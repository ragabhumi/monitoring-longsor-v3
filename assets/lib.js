function getColor(d) {
	return d == 1 ? '#00FF00' :
		d == 2 ? '#FFFF00' :
				d == 0 ? '#FF0000' :
					'#FF0000';
}

function getStatus(d) {
	return d == 1 ? 'Normal' :
		d == 2 ? 'Warning' :
				d == 0 ? 'Offline' :
					'Offline';
}

function getIcon(d) {
	return d == 1 ? 'assets/normal.png' :
		d == 2 ? 'assets/warning.gif' :
				d == 0 ? 'assets/offline.png' :
					'assets/offline.png';
}


window.myLD = Object.assign({}, window.myLD, {  
    myMarkerLD: { 
        pointToLayer: function(feature, latlng, context) { 
			// return L.circleMarker(latlng, {
			// 	radius: 6,
			// 	fillColor: getColor(feature.properties.status),
			// 	color: '#000000',
			// 	weight: 1,
			// 	opacity: 1,
			// 	fillOpacity: 0.8
			// }); 
			let icon = L.icon({
				iconUrl: getIcon(feature.properties.status),  // Mendapatkan path ikon
				iconSize: [30, 30],  // Ukuran ikon
				iconAnchor: [15, 15],  // Titik jangkar (anchor) dari ikon
				popupAnchor: [0, -15]  // Lokasi pembukaan popup relatif terhadap ikon
			});

			// Mengembalikan marker menggunakan ikon yang telah dibuat
			return L.marker(latlng, { icon: icon });
        },
		bindPopup: function(feature, layer) {
			var popupContent = "<b>" + feature.properties["stasiun"] + "</b><p>Bujur : " + feature.properties.lon + "</br>Lintang : " + feature.properties.lat + "</br>Status : " + getStatus(feature.properties.status) + "</p>";
            layer.bindPopup(JSON.stringify(popupContent).replace(/"/g, ''))
        },
    },
});

// Plate Tectonic style

window.myFault = Object.assign({}, window.myFault, {  
	myConf_Fault: {  
		style: function(feature) {  
			return {
				color: 'red',
				weight: 2
			}; 
        	}, 			
		
        	bindPopup: function(feature, layer) {
			var popupContent = "<p>Sesar " + feature.properties["Name"] + "</p>";
			layer.bindPopup(JSON.stringify(popupContent).replace(/"/g, ''))
		},
	},
	myConf_Fold: {  
		style: function(feature) {  
			return {
				color: 'blue',
				weight: 2
			}; 
        	}, 			
		
        	bindPopup: function(feature, layer) {
			var popupContent = "<p>Sesar " + feature.properties["Name"] + "</p>";
			layer.bindPopup(JSON.stringify(popupContent).replace(/"/g, ''))
		},
	},
	myConf_Normal: {  
		style: function(feature) {  
			return {
				color: 'green',
				weight: 2
			}; 
        	}, 			
		
        	bindPopup: function(feature, layer) {
			var popupContent = "<p>Sesar " + feature.properties["Name"] + "</p>";
			layer.bindPopup(JSON.stringify(popupContent).replace(/"/g, ''))
		},
	},
	myConf_Thrust: {  
		style: function(feature) {  
			return {
				color: 'yellow',
				weight: 2
			}; 
        	}, 			
		
        	bindPopup: function(feature, layer) {
			var popupContent = "<p>Sesar " + feature.properties["Name"] + "</p>";
			layer.bindPopup(JSON.stringify(popupContent).replace(/"/g, ''))
		},
	},
	myInf_Fault: {  
		style: function(feature) {
			return {
				color: 'red',  // Warna merah
				weight: 2,  // Ketebalan garis
				dashArray: '5, 5',  // Garis putus-putus (5px garis, 5px spasi)
				opacity: 1  // Opaque (tidak transparan)
			};
		}, 			
	    	bindPopup: function(feature, layer) {
			var popupContent = "<p>Sesar " + feature.properties["Name"] + "</p>";
			layer.bindPopup(JSON.stringify(popupContent).replace(/"/g, ''))
		},
	},
	myInf_Normal: {  
		style: function(feature) {
			return {
				color: 'green',  // Warna merah
				weight: 2,  // Ketebalan garis
				dashArray: '5, 5',  // Garis putus-putus (5px garis, 5px spasi)
				opacity: 1  // Opaque (tidak transparan)
			};
		}, 			
	    	bindPopup: function(feature, layer) {
			var popupContent = "<p>Sesar " + feature.properties["Name"] + "</p>";
			layer.bindPopup(JSON.stringify(popupContent).replace(/"/g, ''))
		},
	},
	myInf_Thrust: {  
		style: function(feature) {
			return {
				color: 'yellow',  // Warna merah
				weight: 2,  // Ketebalan garis
				dashArray: '5, 5',  // Garis putus-putus (5px garis, 5px spasi)
				opacity: 1  // Opaque (tidak transparan)
			};
		}, 			
	    	bindPopup: function(feature, layer) {
			var popupContent = "<p>Sesar " + feature.properties["Name"] + "</p>";
			layer.bindPopup(JSON.stringify(popupContent).replace(/"/g, ''))
		},
	},
});
