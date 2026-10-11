# -*- coding: utf-8 -*-
"""
Información turística detallada de los 29 nodos (ficha por sitio).

NOTA PARA LA TESIS: las descripciones son orientativas. Horarios, tarifas de
entrada y teléfonos cambian con frecuencia y NO se incluyen como dato fijo para
no publicar información desactualizada: la plataforma enlaza a Google Maps y
muestra "Confirmar antes de visitar". Si verificas un dato en campo, agrégalo
en el campo "horario" o "tarifa" de la ficha correspondiente (con fuente/fecha).
"""

SITIOS_INFO = {
    1: dict(distrito="Antón", resumen="Playa del Pacífico coclesano, muy visitada por familias panameñas.",
            detalle="Extensa playa de arena clara y oleaje moderado en la costa de Antón, con oferta de alojamiento y comida de mar cercana. Es una de las playas más conocidas del corredor Río Hato–Farallón.",
            actividades=["Baño y caminatas en la orilla", "Comida de mar en la zona", "Deportes de playa"],
            duracion="2-4 horas", mejor_epoca="Diciembre a abril (época seca)", consejo="Llevar protector solar y agua; la marea afecta el área de baño."),
    2: dict(distrito="Antón", resumen="Playa de arena dorada junto a la zona turística de Farallón.",
            detalle="Playa de olas moderadas, cercana a complejos turísticos de la costa de Coclé. Buena parada para combinar con Santa Clara y Playa Blanca en el mismo día.",
            actividades=["Baño de mar", "Caminata al atardecer", "Pesca deportiva en la zona"],
            duracion="2-3 horas", mejor_epoca="Diciembre a abril", consejo="Verificar acceso: parte de la costa pertenece a complejos privados."),
    3: dict(distrito="Aguadulce", resumen="Playa tranquila cercana a las salinas de Aguadulce.",
            detalle="Playa de ambiente local, útil para combinar con las Salinas de Aguadulce y el casco urbano. Zona de mareas amplias.",
            actividades=["Paseo por la costa", "Observación de aves", "Gastronomía local"],
            duracion="1-2 horas", mejor_epoca="Diciembre a abril", consejo="Consultar la tabla de mareas antes de ir."),
    4: dict(distrito="Antón", resumen="Playa de arena blanca en el corredor costero de Antón.",
            detalle="Playa con arena clara y entorno de complejos turísticos. Se recorre fácilmente en cadena con Farallón por la vía costera.",
            actividades=["Baño", "Descanso en la playa", "Fotografía de paisaje"],
            duracion="2-3 horas", mejor_epoca="Diciembre a abril", consejo="Llegar temprano en fines de semana y feriados."),
    5: dict(distrito="Antón", resumen="Comunidad costera con playa y oferta de mariscos.",
            detalle="Poblado pesquero en la costa de Antón. Destaca por el ambiente de comunidad de pescadores y la gastronomía de productos del mar.",
            actividades=["Almuerzo de mariscos", "Paseo en la orilla", "Observación de la actividad pesquera"],
            duracion="1-2 horas", mejor_epoca="Diciembre a abril", consejo="Acordar precios de platos y lanchas antes de consumir."),
    6: dict(distrito="Antón", resumen="Mercado de artesanías del Valle de Antón.",
            detalle="Mercado artesanal del Valle de Antón (caldera de un volcán extinto) con artesanías, plantas y productos locales. Suele tener más movimiento los fines de semana.",
            actividades=["Compra de artesanías", "Degustación de productos locales", "Caminata por el pueblo"],
            duracion="1-2 horas", mejor_epoca="Todo el año (fines de semana con más ambiente)", consejo="Confirmar los días de mercado antes de planificar la visita."),
    7: dict(distrito="Antón", resumen="Exhibición de serpientes y reptiles en el Valle de Antón.",
            detalle="Atractivo educativo de fauna ubicado en el Valle de Antón, cerca del mercado y del mariposario.",
            actividades=["Visita guiada o recorrido de exhibición", "Fotografía de fauna"],
            duracion="45-90 minutos", mejor_epoca="Todo el año", consejo="Atractivo de pago; confirmar horario y tarifa."),
    8: dict(distrito="Penonomé", resumen="Museo histórico en Penonomé dedicado a la familia Arias Madrid.",
            detalle="Museo ubicado en Penonomé, vinculado a la historia política y familiar de los hermanos Arias Madrid, figuras importantes de la vida pública panameña.",
            actividades=["Visita al museo", "Recorrido por el casco histórico de Penonomé"],
            duracion="1 hora", mejor_epoca="Todo el año", consejo="Combinar con Museo de Penonomé e Iglesia San Juan Bautista (Día 2)."),
    9: dict(distrito="La Pintada", resumen="Parque nacional de bosque nuboso con senderos ecológicos.",
            detalle="Área protegida de montaña en la cordillera central de Coclé, con bosque húmedo y nuboso, alta biodiversidad y senderos. Ruta de mayor exigencia del itinerario.",
            actividades=["Senderismo", "Observación de aves", "Fotografía de naturaleza"],
            duracion="3-4 horas", mejor_epoca="Diciembre a abril (menos lluvia)", consejo="Llevar calzado de montaña e impermeable; el camino es largo y el clima cambia rápido."),
    10: dict(distrito="Natá", resumen="Parque arqueológico de la cultura Gran Coclé.",
             detalle="Sitio arqueológico con tumbas de élite precolombinas y museo de sitio, importante para entender la cultura Gran Coclé y su orfebrería.",
             actividades=["Visita al museo de sitio", "Recorrido de las excavaciones", "Fotografía histórica"],
             duracion="1.5-2 horas", mejor_epoca="Todo el año", consejo="Confirmar horario y tarifa; sitio educativo con guía recomendado."),
    11: dict(distrito="Aguadulce", resumen="Museo regional con historia de la sal y de Aguadulce.",
             detalle="Museo en Aguadulce que recoge historia y patrimonio de la región, incluyendo la tradición salinera.",
             actividades=["Visita al museo", "Paseo por el centro de Aguadulce"],
             duracion="1 hora", mejor_epoca="Todo el año", consejo="Combinar con Salinas de Aguadulce (Día 6)."),
    12: dict(distrito="Penonomé", resumen="Templo histórico del centro de Penonomé.",
             detalle="Iglesia principal de Penonomé, parte del recorrido histórico del casco urbano.",
             actividades=["Visita exterior e interior (según horario de culto)", "Fotografía arquitectónica"],
             duracion="30-45 minutos", mejor_epoca="Todo el año", consejo="Respetar horarios de misa y vestimenta adecuada."),
    13: dict(distrito="La Pintada", resumen="Cascada en la zona de montaña de La Pintada.",
             detalle="Cascada rodeada de vegetación en el entorno del Parque Nacional Omar Torrijos, atractivo central del Día 3.",
             actividades=["Caminata corta", "Baño según condiciones del caudal", "Fotografía"],
             duracion="1.5-2 horas", mejor_epoca="Diciembre a abril; en lluvias el acceso es más difícil", consejo="Evitar bañarse con crecidas; llevar calzado antideslizante."),
    14: dict(distrito="Penonomé", resumen="Balneario de río cerca de Penonomé.",
             detalle="Balneario natural de ambiente familiar a pocos kilómetros del centro de Penonomé.",
             actividades=["Baño en el río", "Picnic familiar"],
             duracion="1.5-2 horas", mejor_epoca="Diciembre a abril", consejo="Revisar el caudal del río antes de entrar al agua."),
    15: dict(distrito="Penonomé", resumen="Capital de la provincia de Coclé y base de todos los itinerarios.",
             detalle="Centro administrativo y de servicios de Coclé; punto de salida y regreso de cada día del proyecto. Concentra hoteles, restaurantes, comercio y estaciones de combustible.",
             actividades=["Pernoctar y abastecerse", "Gastronomía local", "Visitar museos del casco urbano"],
             duracion="Base de operaciones", mejor_epoca="Todo el año", consejo="Ideal como hospedaje base para recorrer toda la provincia."),
    16: dict(distrito="Aguadulce", resumen="Ciudad conocida por su tradición salinera y azucarera.",
             detalle="Ciudad costera del oeste de Coclé, con fuerte identidad ligada a la sal y a la caña de azúcar.",
             actividades=["Recorrido urbano", "Gastronomía local", "Visita a museo y salinas"],
             duracion="1-2 horas", mejor_epoca="Todo el año", consejo="Punto de partida del Día 6."),
    17: dict(distrito="Antón", resumen="Ciudad puerta de entrada a las playas y al Valle de Antón.",
             detalle="Núcleo urbano que articula la salida hacia las playas del Pacífico y el Valle de Antón.",
             actividades=["Paso de abastecimiento", "Gastronomía local"],
             duracion="30-60 minutos", mejor_epoca="Todo el año", consejo="Parada útil para combustible y compras antes de las playas."),
    18: dict(distrito="La Pintada", resumen="Pueblo artesanal, cuna del tradicional sombrero pintao.",
             detalle="Localidad de montaña asociada a la artesanía tradicional y a la ruta hacia El Copé y el Parque Nacional Omar Torrijos.",
             actividades=["Compra de artesanías", "Paseo por el pueblo", "Punto de partida hacia la montaña"],
             duracion="1 hora", mejor_epoca="Todo el año", consejo="Cercano a Mercado, Parroquia y Balneario Los Algarrobos (nodos a menos de 1.2 km)."),
    19: dict(distrito="Natá", resumen="Ciudad histórica fundada en el período colonial temprano.",
             detalle="Natá es una de las poblaciones más antiguas de Panamá; su centro conserva la iglesia colonial y el legado histórico regional.",
             actividades=["Recorrido histórico", "Visita a la iglesia", "Gastronomía local"],
             duracion="1 hora", mejor_epoca="Todo el año", consejo="Combinar con El Caño, Santiago Apóstol y Ecoparque (Día 4)."),
    20: dict(distrito="La Pintada", resumen="Iglesia histórica del centro de La Pintada.",
             detalle="Parroquia del casco urbano de La Pintada, parte del circuito cultural de la zona.",
             actividades=["Visita arquitectónica", "Fotografía"],
             duracion="30 minutos", mejor_epoca="Todo el año", consejo="Respetar horarios de culto."),
    21: dict(distrito="Antón", resumen="Monumento natural y mirador del Valle de Antón.",
             detalle="Cerro del entorno del Valle de Antón con senderos y vistas panorámicas del cráter del volcán extinto.",
             actividades=["Senderismo", "Miradores", "Fotografía de paisaje"],
             duracion="2-3 horas", mejor_epoca="Diciembre a abril", consejo="Salir temprano; llevar agua y calzado de senderismo."),
    22: dict(distrito="Penonomé", resumen="Museo histórico del centro de Penonomé.",
             detalle="Museo local del casco urbano de Penonomé; se recorre a pie junto con el Museo Arias Madrid y la iglesia.",
             actividades=["Visita al museo", "Caminata urbana"],
             duracion="45-60 minutos", mejor_epoca="Todo el año", consejo="A menos de 1 km de la Iglesia San Juan Bautista."),
    23: dict(distrito="La Pintada", resumen="Mercado de artesanías de La Pintada.",
             detalle="Punto de venta de artesanías locales, incluido el sombrero pintao, en el centro de La Pintada.",
             actividades=["Compra de artesanías", "Conversar con artesanos"],
             duracion="45 minutos", mejor_epoca="Todo el año", consejo="Pedir factura o confirmar precios antes de comprar."),
    24: dict(distrito="La Pintada", resumen="Balneario natural junto a La Pintada.",
             detalle="Balneario de río cercano al casco urbano de La Pintada, de acceso sencillo.",
             actividades=["Baño", "Picnic"],
             duracion="1-2 horas", mejor_epoca="Diciembre a abril", consejo="Vigilar el nivel del río en época lluviosa."),
    25: dict(distrito="Natá", resumen="Iglesia colonial, una de las más antiguas del país.",
             detalle="Templo colonial de Natá, de alto valor histórico y arquitectónico para la ruta arqueológica del Día 4.",
             actividades=["Visita arquitectónica", "Fotografía histórica"],
             duracion="30-45 minutos", mejor_epoca="Todo el año", consejo="A solo 1.4 km del centro de Natá."),
    26: dict(distrito="Natá", resumen="Parque ecológico cerca de Natá.",
             detalle="Espacio natural cercano a Natá con enfoque ecológico y recreativo.",
             actividades=["Caminata", "Observación de naturaleza", "Actividades familiares"],
             duracion="1-2 horas", mejor_epoca="Diciembre a abril", consejo="Confirmar horario y tarifas."),
    27: dict(distrito="Aguadulce", resumen="Salinas tradicionales de Aguadulce.",
             detalle="Extensiones de producción artesanal de sal marina, símbolo de la identidad de Aguadulce.",
             actividades=["Observar la producción de sal", "Fotografía de paisaje", "Compra de sal local"],
             duracion="1 hora", mejor_epoca="Época seca (diciembre a abril), cuando hay más producción", consejo="Mejor luz para fotos al amanecer o atardecer."),
    28: dict(distrito="Antón", resumen="Jardín de mariposas en el Valle de Antón.",
             detalle="Atractivo de naturaleza con mariposas tropicales, a menos de 1 km del mercado artesanal.",
             actividades=["Recorrido del jardín", "Fotografía macro"],
             duracion="45-60 minutos", mejor_epoca="Mañanas soleadas", consejo="Las mariposas están más activas con sol."),
    29: dict(distrito="Antón", resumen="Tirolesa y aventura en el Valle de Antón.",
             detalle="Parque de aventura con tirolesas sobre el bosque del Valle de Antón; el atractivo de adrenalina del Día 5.",
             actividades=["Tirolesa (canopy)", "Vistas del bosque"],
             duracion="1.5-2 horas", mejor_epoca="Todo el año (evitar lluvia fuerte)", consejo="Verificar restricciones de edad/peso y reservar con anticipación."),
}


def ficha_completa(nid, atractivo):
    """Une datos base del atractivo con su ficha turística."""
    f = dict(SITIOS_INFO.get(nid, {}))
    f.setdefault("distrito", "")
    f.setdefault("resumen", atractivo.get("descripcion", ""))
    f.setdefault("detalle", atractivo.get("descripcion", ""))
    f.setdefault("actividades", [])
    f.setdefault("duracion", "")
    f.setdefault("mejor_epoca", "")
    f.setdefault("consejo", "")
    f.setdefault("horario", "Confirmar antes de visitar")
    f.setdefault("tarifa", "Confirmar antes de visitar")
    f.update({
        "id": nid, "nombre": atractivo["nombre"], "cod": atractivo["cod"],
        "tipo": atractivo["tipo"], "lat": atractivo["lat"], "lng": atractivo["lng"],
        "google_maps": f"https://www.google.com/maps/search/?api=1&query={atractivo['lat']},{atractivo['lng']}",
    })
    return f
