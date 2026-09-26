// Configuración de mapa y geolocalización para San Juan de los Morros
let map, passengerMarker;
const SAN_JUAN_CENTRO = [9.9111, -67.3538];

function inicializarMapa() {
    const mapElement = document.getElementById('map');
    if (!mapElement) return;

    map = L.map('map').setView(SAN_JUAN_CENTRO, 15);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap'
    }).addTo(map);

    obtenerUbicacionGPS();
}

function obtenerUbicacionGPS() {
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                actualizarPosicionPasajero(lat, lng);
            },
            (error) => {
                console.warn("GPS no disponible:", error.message);
                actualizarPosicionPasajero(SAN_JUAN_CENTRO[0], SAN_JUAN_CENTRO[1]);
                alert("No se pudo obtener tu ubicación exactual. Por favor ajusta tu posición en el mapa.");
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    } else {
        actualizarPosicionPasajero(SAN_JUAN_CENTRO[0], SAN_JUAN_CENTRO[1]);
    }
}

function actualizarPosicionPasajero(lat, lng) {
    if (!map) return;
    
    map.setView([lat, lng], 16);

    if (passengerMarker) {
        passengerMarker.setLatLng([lat, lng]);
    } else {
        passengerMarker = L.marker([lat, lng], { draggable: true }).addTo(map);
        passengerMarker.bindPopup("<b>Tu ubicación de recogida</b>").openPopup();
    }

    const latInput = document.getElementById('latitud');
    const lngInput = document.getElementById('longitud');
    if (latInput) latInput.value = lat;
    if (lngInput) lngInput.value = lng;
}

document.addEventListener("DOMContentLoaded", inicializarMapa);
