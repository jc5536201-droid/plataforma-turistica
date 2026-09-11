function combinarTramos(tramos) {
    const puntos_ruta = [], nodos_ruta = [], segmentos = [];
    let distancia_km = 0, tiempo_min = 0, costo = 0;
    let tiempo_conduccion_min = 0;
    let todasOsrm = true;
    let factorHolgura = 1.0;

    tramos.forEach((tramo, i) => {
        const puntos = i === 0 ? tramo.puntos_ruta : tramo.puntos_ruta.slice(1);
        puntos_ruta.push(...puntos);
        const nodos = i === 0 ? tramo.nodos_ruta : tramo.nodos_ruta.slice(1);
        nodos_ruta.push(...nodos);
        segmentos.push(...(tramo.segmentos || []));
        distancia_km += Number(tramo.distancia_km) || 0;
        tiempo_min += Number(tramo.tiempo_min) || 0;
        tiempo_conduccion_min += Number(tramo.tiempo_conduccion_min) || 0;
        costo += Number(tramo.costo) || 0;
        factorHolgura = Number(tramo.factor_holgura) || factorHolgura;
        if ((tramo.fuente_metricas || 'osrm') !== 'osrm') todasOsrm = false;
    });

    return {
        exito: true, puntos_ruta, nodos_ruta, segmentos,
        distancia_km, tiempo_min, tiempo_conduccion_min, costo,
        factor_holgura: factorHolgura,
        criterio: criterioActual,
        fuente_metricas: todasOsrm ? 'osrm' : 'haversine'
    };
}
