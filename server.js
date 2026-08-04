const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const fs = require('fs'); // Módulo nativo para escribir archivos

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*" } });

let motorizadosDisponibles = {}; 
const ARCHIVO_HISTORIAL = './historial_viajes.json';

// Inicializar el archivo de historial si no existe
if (!fs.existsSync(ARCHIVO_HISTORIAL)) {
    fs.writeFileSync(ARCHIVO_HISTORIAL, JSON.stringify([], null, 2));
}

function calcularDistanciaKM(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon/2) * Math.sin(dLon/2);
    return R * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))); 
}

// Función para guardar el viaje en el archivo JSON
function guardarEnHistorial(viajeFinalizado) {
    try {
        const datosActuales = JSON.parse(fs.readFileSync(ARCHIVO_HISTORIAL, 'utf8'));
        datosActuales.push(viajeFinalizado);
        fs.writeFileSync(ARCHIVO_HISTORIAL, JSON.stringify(datosActuales, null, 2), 'utf8');
        console.log(`[HISTORIAL] Viaje #${viajeFinalizado.id} guardado exitosamente en historial_viajes.json`);
    } catch (error) {
        console.error('[ERROR HISTORIAL]', error);
    }
}

io.on('connection', (socket) => {
    
    socket.on('motorizado_disponible', (datos) => {
        motorizadosDisponibles[socket.id] = { id: datos.id, nombre: datos.nombre, lat: datos.lat, lon: datos.lon };
        console.log(`[DISPONIBLE] ${datos.nombre} listo.`);
    });

    socket.on('solicitar_viaje', (viaje) => {
        console.log(`\n[SISTEMA] Procesando solicitud de ${viaje.cliente}...`);
        const distanciaViajeKM = calcularDistanciaKM(viaje.origen_lat, viaje.origen_lon, viaje.destino_lat, viaje.destino_lon);
        
        // Asignación de Tarifas y Precios Fijos
        let tipoTarifa = "";
        let precioDinero = 0;
        const LIMITE_CORTO_KM = 3.0; 

        if (distanciaViajeKM < LIMITE_CORTO_KM) {
            tipoTarifa = "CORTA";
            precioDinero = 2.00; // $2 Corta
        } else {
            tipoTarifa = "LARGA";
            precioDinero = 4.00; // $4 Larga
        }

        let mejorCandidato = null;
        let distanciaMinima = Infinity;
        for (let socketId in motorizadosDisponibles) {
            let moto = motorizadosDisponibles[socketId];
            let dist = calcularDistanciaKM(moto.lat, moto.lon, viaje.origen_lat, viaje.origen_lon);
            if (dist < distanciaMinima) { distanciaMinima = dist; mejorCandidato = socketId; }
        }

        if (mejorCandidato) {
            let motoAsignada = motorizadosDisponibles[mejorCandidato];
            const nuevoViaje = {
                id: Math.floor(Math.random() * 10000),
                cliente: viaje.cliente,
                motorizado: motoAsignada.nombre,
                distancia_km: distanciaViajeKM.toFixed(2),
                tarifa: tipoTarifa,
                monto: `$${precioDinero.toFixed(2)}`,
                fecha: new Date().toLocaleString()
            };

            console.log(`[TARIFA] ${nuevoViaje.tarifa} -> ${nuevoViaje.monto}`);
            
            // Enviar alerta al motorizado
            io.to(mejorCandidato).emit('alerta_viaje', nuevoViaje);
            
            // Simular que el viaje se completa y se guarda de inmediato
            guardarEnHistorial(nuevoViaje);
        } else {
            socket.emit('error_viaje', { mensaje: 'Sin unidades.' });
        }
    });

    socket.on('disconnect', () => {
        if (motorizadosDisponibles[socket.id]) delete motorizadosDisponibles[socket.id];
    });
});

server.listen(3000, () => {
    console.log(`Servidor Martillos & Ruedas con Historial en puerto 3000`);
});
