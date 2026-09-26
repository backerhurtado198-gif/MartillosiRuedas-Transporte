// Configuración de Íconos Personalizados Leaflet
const motoIcon = L.icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/3198/3198336.png',
    iconSize: [38, 38],
    iconAnchor: [19, 19],
    popupAnchor: [0, -15]
});

const passengerIcon = L.icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/684/684908.png',
    iconSize: [35, 35],
    iconAnchor: [17, 35]
});

// Cálculo de distancia entre dos puntos (Fórmula de Haversine en Km)
function calcularDistanciaKm(lat1, lon1, lat2, lon2) {
    const R = 6371; 
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// Función de tarifa fija: 1$ o 2$
function obtenerTarifaFija(distanciaKm) {
    if (distanciaKm <= 2.5) {
        return { tipo: "Carrera Corta", monto: 1 };
    } else {
        return { tipo: "Carrera Larga", monto: 2 };
    }
}

// Activar radar de búsqueda
function activarRadarBusqueda(map, lat, lng) {
    const radarMarker = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'radar-pulse',
            iconSize: [20, 20]
        })
    }).addTo(map);
    return radarMarker;
}
