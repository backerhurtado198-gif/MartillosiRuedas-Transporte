const { io } = require("socket.io-client");

const socketMotorizado = io("http://localhost:3000");
const socketCliente = io("http://localhost:3000");

socketMotorizado.on("connect", () => {
    socketMotorizado.emit("motorizado_disponible", {
        id: 101,
        nombre: "Carlos Mendoza",
        lat: 9.9123,  
        lon: -67.3542
    });
});

socketMotorizado.on("alerta_viaje", (viaje) => {
    console.log(`\n⚡ [MOTO-ALERTA] ¡Nuevo Viaje Entrante!`);
    console.log(`   Cliente: ${viaje.cliente}`);
    console.log(`   Distancia de Ruta: ${viaje.distancia_total_km} KM`);
    console.log(`   🔴 TARIFA ASIGNADA: TARIFA ${viaje.tarifa}`);
    console.log(`===================================================`);
    process.exit(0);
});

socketCliente.on("connect", () => {
    setTimeout(() => {
        console.log("\n[CLIENTE] Solicitando viaje de 3.5 KM para probar el nuevo límite...");
        socketCliente.emit("solicitar_viaje", {
            cliente: "Andrés Silva",
            tipo_servicio: "Moto-Taxi",
            origen_lat: 9.9125, 
            origen_lon: -67.3540,
            // Coordenadas calculadas a ~3.5 KM de distancia
            destino_lat: 9.9350, 
            destino_lon: -67.3240
        });
    }, 1500);
});
