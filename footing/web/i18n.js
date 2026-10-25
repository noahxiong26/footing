/* Strings for the globe screens, English + Spanish. Plain words, short sentences (about a 6th-grade level). */
(function (root) {
  "use strict";
  var S = {
    en: {
      title: "Where could you land?",
      lede: "Every state, scored for you: what help you can use, what rent costs, how full shelters are, and how safe the laws are for you.",
      start: "Tell us about you",
      skip: "Show the map first",
      privacy: "Your answers stay on this phone. They are never sent anywhere.",
      hide: "Hide this page", hideShort: "Hide", hideLong: "Leave fast: opens a weather page and clears this screen",
      lang: "Español",
      list: "List", map: "Map",
      aboutYou: "About you", editAboutYou: "Edit about you",
      statusQ: "What are your immigration papers right now?",
      statusHelp: "This changes which programs you can use. Pick 'Prefer not to say' and we will only show help that is open to everyone.",
      whoQ: "Who is with you?",
      kids: "Kids", pregnant: "Pregnant", partner: "Partner", pets: "Pets", mixed: "Some family are U.S. citizens",
      situationQ: "What fits your situation?",
      tonight: "I need a place tonight", car: "I have a car", no_id: "No ID right now", veteran: "Veteran", disability: "Disability",
      ageQ: "Age", age18: "18-24", age25: "25-49", age50: "50-61", age62: "62+",
      priQ: "What matters most to you?",
      priHelp: "Move things up or down. The top item counts the most. The numbers show how much each one counts.",
      up: "Move up", down: "Move down",
      showMap: "Show my map", forget: "Forget my answers",
      forgot: "Your answers were deleted from this phone.",
      c_access: "Help you can use", c_affordability: "Rent you can afford", c_shelter: "Shelter space",
      c_safety: "Safety from immigration enforcement", c_criminalization: "Laws against sleeping outside", c_community: "What people here say",
      layer: "Color the map by", l_fit: "Fit for you", l_community: "Ratings", l_shelter: "Shelter space", l_affordability: "Rent", l_safety: "Enforcement laws",
      legendLow: "Poor fit", legendHigh: "Good fit", legendUnknown: "No data",
      lo_community: "Bad", hi_community: "Good", lo_shelter: "Most outside", hi_shelter: "Most inside",
      lo_affordability: "Costly", hi_affordability: "Affordable", lo_safety: "Harsh laws", hi_safety: "Protective",
      fit: "Fit for you", rank: "Rank", of: "of", confidence: "How sure we are",
      conf_high: "high", conf_medium: "medium", conf_low: "low",
      rankRange: "In 90% of reasonable weightings it ranks between #{a} and #{b}.", rankFixed: "In 90% of reasonable weightings it stays at #{a}.", rangeShort: "usually #{a}–#{b}", fixedShort: "steady at #{a}",
      why: "Why this score", unknownWhy: "Unknown",
      programs: "What you can use here",
      yes: "Yes", limited: "Some", no: "No", varies: "Check",
      flyIn: "Zoom in", openReceipt: "Open the {town} receipt", rateHere: "Rate a place here",
      rateTitle: "How was it here?", rateHelp: "Your rating is filed under a 1 km square, not your exact spot. No names, no text.",
      overall: "Overall", safe: "I felt safe", respect: "People treated me with respect", help: "I could get help",
      tags: "Anything true about this place?",
      tag_shelter_full: "Shelter was full", tag_shelter_had_beds: "Shelter had beds", tag_police_moved_people: "Police moved people along",
      tag_welcoming_immigrants: "Welcoming to immigrants", tag_spanish_spoken: "Spanish spoken", tag_pets_ok: "Pets OK",
      tag_quiet_place_to_rest: "Quiet place to rest", tag_outlets_wifi: "Outlets or Wi-Fi", tag_clean_restrooms: "Clean restrooms",
      tag_free_meals_nearby: "Free meals nearby",
      send: "Send rating", sent: "Thanks. Your rating is on the map.", sentLocal: "Saved on this device only. Shared ratings need a signed-in viewer with access.", pickSpot: "Tap the map to choose the spot you are rating.",
      rateNeedsServer: "Ratings need a connection. Try again when you have signal.",
      noWebgl: "This phone can't draw the 3D map, so here is the list instead.",
      loading: "Loading the map...",
      offlineTiles: "No signal: showing the saved map. Satellite photos load when you're back online.",
      demoTown: "Real data recorded for {town}",
      call211: "Talk to a person: call 211", call211short: "Call 211", nearMe: "Help near me now",
      legal: "Free legal help: immigrationadvocates.org/legaldirectory",
      sources: "Sources", asOf: "as of",
      top: "Best fits for you", allStates: "All states",
      noRatings: "No ratings yet. Ratings appear here after people who have been somewhere share how it went.",
      caution: "Before you apply",
      // ---- Virginia (session 4) ----
      langName: "English",
      title_va: "Where in Virginia could you land?",
      lede_va: "All 133 Virginia cities and counties, scored for you: shelter space, rent, help nearby and local laws. Every number shows where it came from.",
      vaOnly: "Footing covers Virginia only for now.",
      outsideTap: "That spot is outside Virginia. Footing covers Virginia only for now.", waterTap: "That spot is on open water or right on a border. Tap on land inside a Virginia city or county.",
      scope_va: "Virginia", scope_us: "All states (beta)",
      c_rent: "Rent you can afford", c_services: "Help nearby", c_laws: "Local laws on sleeping outside", c_crime: "Reported crime",
      l_rent: "Rent", l_services: "Help nearby", l_laws: "Local laws", l_crime: "Reported crime",
      lo_rent: "Costly", hi_rent: "Affordable", lo_services: "Little help", hi_services: "Lots of help",
      lo_laws: "Bans", hi_laws: "No ban", lo_crime: "More reports", hi_crime: "Fewer reports",
      bedroomsQ: "How many bedrooms do you need?", bedAuto: "Pick for me", bed0: "Studio", bed1: "1", bed2: "2", bed3: "3", bed4: "4",
      crimeQ: "Count reported crime?",
      crimeHelp: "Off unless you turn it on. Crime reports show where police write reports, not only where danger is. People without homes are more often victims than offenders.",
      crimeOn: "Count it", crimeOff: "Leave it out",
      county: "County", city: "Independent city (separate from any county)",
      howBuilt: "How the score adds up",
      mosaicHelp: "Wider means it matters more to you. Taller means this place does better. Striped parts have no data, so they are left out.",
      notCounted: "Not counted: no data yet",
      weightOf: "{w}% of your score",
      confLine: "Based on {k} of {n} parts. Missing or older data lowers this.",
      helpHere: "Help places mapped here", helpNone: "No help places are mapped here yet. Call 211 to reach a person who knows the area.",
      k_clinic: "Clinic", k_shelter: "Shelter", k_food_bank: "Food bank", k_day_center: "Day center", k_soup_kitchen: "Free meals",
      back: "Back", tapZoom: "Zoomed in. Now tap the exact spot.", changeSpot: "Tap the map again to move the spot.",
      search: "Search a city or county", allPlaces: "All 133 places", noMatch: "No city or county matches that.",
      details: "Details", detailsEn: "Details (in English)",
      machine: "Machine translation. Not yet checked by a native speaker.",
      sz0: "studio", sz1: "1-bedroom", sz2: "2-bedroom", sz3: "3-bedroom", sz4: "4-bedroom",
      line_rent: "{rent} a month for a {size}: {hours} hours of minimum-wage work a week",
      line_shelter: "{pct}% of people without homes slept outside. {beds} shelter beds for {people} people.",
      line_shelter_kids: "{pct}% of people without homes slept outside. {beds} family shelter beds for {people} people in families.",
      line_services: "{groc} grocery stores take EBT. {help} help places mapped.",
      line_transit: "Buses are free.",
      law_0: "Sleeping outside on public land is banned here.", law_35: "Sleeping outside is limited here.", law_60: "The city closes some camps.",
      law_null: "Local rules not checked yet.",
      safe_10: "Local police work with ICE (287(g) task force).", safe_40: "The jail can hold people for ICE (287(g)).", safe_80: "No local ICE agreement is listed.",
      line_crime: "{x} violent crimes reported per 1,000 people (2025).", crime_null: "No reliable crime data for 2025.",
      line_community: "{n} ratings from people who were here.", community_null: "No ratings yet.",
      topVa: "Best fits in Virginia", programsVa: "What you can use in Virginia",
      statewide: "These are the same everywhere in Virginia.",
      rankOf: "#{r} of {n}", sourceWord: "Source", seeAll: "See all 133",
      rateHelpVa: "Tap the map where you were. Your rating is filed under a 1 km square, not your exact spot. No names, no text.",
      ratedThanks: "Thanks. Your rating counts toward {place}.",
      phone: "Phone", hours: "Hours",
      partOf: "Part of the {coc} count.",
      unknownParts: "Left out of this score",
      _end: ""
    },
    es: {
      title: "¿Dónde podrías llegar?",
      lede: "Cada estado, calificado para ti: qué ayuda puedes usar, cuánto cuesta la renta, qué tan llenos están los albergues y qué tan seguras son las leyes para ti.",
      start: "Cuéntanos sobre ti",
      skip: "Ver el mapa primero",
      privacy: "Tus respuestas se quedan en este teléfono. Nunca se envían.",
      hide: "Ocultar esta página", hideShort: "Ocultar", hideLong: "Salir rápido: abre una página del clima y borra esta pantalla",
      lang: "English",
      list: "Lista", map: "Mapa",
      aboutYou: "Sobre ti", editAboutYou: "Cambiar mis respuestas",
      statusQ: "¿Qué papeles de inmigración tienes ahora?",
      statusHelp: "Esto cambia los programas que puedes usar. Elige 'Prefiero no decir' y solo mostraremos ayuda abierta a todos.",
      whoQ: "¿Quién está contigo?",
      kids: "Niños", pregnant: "Embarazada", partner: "Pareja", pets: "Mascotas", mixed: "Algunos familiares son ciudadanos",
      situationQ: "¿Qué describe tu situación?",
      tonight: "Necesito dónde dormir hoy", car: "Tengo carro", no_id: "No tengo identificación", veteran: "Veterano/a", disability: "Discapacidad",
      ageQ: "Edad", age18: "18-24", age25: "25-49", age50: "50-61", age62: "62+",
      priQ: "¿Qué es lo más importante para ti?",
      priHelp: "Mueve las cosas hacia arriba o abajo. Lo de arriba cuenta más. Los números muestran cuánto cuenta cada una.",
      up: "Subir", down: "Bajar",
      showMap: "Ver mi mapa", forget: "Borrar mis respuestas",
      forgot: "Tus respuestas se borraron de este teléfono.",
      c_access: "Ayuda que puedes usar", c_affordability: "Renta que puedes pagar", c_shelter: "Espacio en albergues",
      c_safety: "Seguridad ante inmigración", c_criminalization: "Leyes contra dormir afuera", c_community: "Lo que dice la gente",
      layer: "Colorear el mapa por", l_fit: "Para ti", l_community: "Opiniones", l_shelter: "Albergues", l_affordability: "Renta", l_safety: "Leyes de inmigración",
      legendLow: "Poco adecuado", legendHigh: "Muy adecuado", legendUnknown: "Sin datos",
      lo_community: "Mal", hi_community: "Bien", lo_shelter: "Más afuera", hi_shelter: "Más adentro",
      lo_affordability: "Cara", hi_affordability: "Accesible", lo_safety: "Leyes duras", hi_safety: "Protectoras",
      fit: "Para ti", rank: "Puesto", of: "de", confidence: "Qué tan seguros estamos",
      conf_high: "alta", conf_medium: "media", conf_low: "baja",
      rankRange: "En 90% de los pesos razonables queda entre el #{a} y el #{b}.", rankFixed: "En 90% de los pesos razonables se queda en el #{a}.", rangeShort: "casi siempre #{a}–#{b}", fixedShort: "fijo en el #{a}",
      why: "Por qué esta calificación", unknownWhy: "Sin datos",
      programs: "Lo que puedes usar aquí",
      yes: "Sí", limited: "Algo", no: "No", varies: "Verificar",
      flyIn: "Acercar", openReceipt: "Abrir el recibo de {town}", rateHere: "Calificar un lugar aquí",
      rateTitle: "¿Cómo te fue aquí?", rateHelp: "Tu calificación se guarda en un cuadro de 1 km, no en tu lugar exacto. Sin nombres ni texto.",
      overall: "En general", safe: "Me sentí seguro/a", respect: "Me trataron con respeto", help: "Pude conseguir ayuda",
      tags: "¿Algo de esto es cierto aquí?",
      tag_shelter_full: "El albergue estaba lleno", tag_shelter_had_beds: "El albergue tenía camas", tag_police_moved_people: "La policía movía a la gente",
      tag_welcoming_immigrants: "Acogedor con inmigrantes", tag_spanish_spoken: "Hablan español", tag_pets_ok: "Aceptan mascotas",
      tag_quiet_place_to_rest: "Lugar tranquilo para descansar", tag_outlets_wifi: "Enchufes o Wi-Fi", tag_clean_restrooms: "Baños limpios",
      tag_free_meals_nearby: "Comidas gratis cerca",
      send: "Enviar calificación", sent: "Gracias. Tu calificación está en el mapa.", sentLocal: "Guardada solo en este dispositivo. Para compartir, abre la página con una cuenta con acceso.", pickSpot: "Toca el mapa para elegir el lugar que calificas.",
      rateNeedsServer: "Calificar necesita conexión. Intenta de nuevo cuando tengas señal.",
      noWebgl: "Este teléfono no puede dibujar el mapa 3D; aquí está la lista.",
      loading: "Cargando el mapa...",
      offlineTiles: "Sin señal: mostrando el mapa guardado. Las fotos satelitales cargan cuando vuelva la conexión.",
      demoTown: "Datos reales grabados para {town}",
      call211: "Habla con una persona: llama al 211", call211short: "Llamar al 211", nearMe: "Ayuda cerca ahora",
      legal: "Ayuda legal gratis: immigrationadvocates.org/legaldirectory",
      sources: "Fuentes", asOf: "al",
      top: "Lo mejor para ti", allStates: "Todos los estados",
      noRatings: "Todavía no hay calificaciones. Aparecen aquí cuando la gente que estuvo en un lugar cuenta cómo le fue.",
      caution: "Antes de solicitar",
      langName: "Español",
      title_va: "¿Dónde en Virginia podrías llegar?",
      lede_va: "Las 133 ciudades y condados de Virginia, calificados para ti: albergues, renta, ayuda cercana y leyes locales. Cada número dice de dónde viene.",
      vaOnly: "Por ahora, Footing cubre solo Virginia.",
      outsideTap: "Ese lugar está fuera de Virginia. Por ahora, Footing cubre solo Virginia.", waterTap: "Ese lugar está en aguas abiertas o justo en un límite. Toque tierra dentro de una ciudad o condado de Virginia.",
      scope_va: "Virginia", scope_us: "Todos los estados (beta)",
      c_rent: "Renta que puedes pagar", c_services: "Ayuda cercana", c_laws: "Leyes locales sobre dormir afuera", c_crime: "Delitos reportados",
      l_rent: "Renta", l_services: "Ayuda cercana", l_laws: "Leyes locales", l_crime: "Delitos reportados",
      lo_rent: "Cara", hi_rent: "Accesible", lo_services: "Poca ayuda", hi_services: "Mucha ayuda",
      lo_laws: "Prohíbe", hi_laws: "Sin prohibición", lo_crime: "Más reportes", hi_crime: "Menos reportes",
      bedroomsQ: "¿Cuántas recámaras necesitas?", bedAuto: "Elige por mí", bed0: "Estudio", bed1: "1", bed2: "2", bed3: "3", bed4: "4",
      crimeQ: "¿Contar los delitos reportados?",
      crimeHelp: "Apagado a menos que lo actives. Los reportes muestran dónde la policía hace reportes, no solo dónde hay peligro. Las personas sin hogar son víctimas más a menudo que agresores.",
      crimeOn: "Contarlos", crimeOff: "No contarlos",
      county: "Condado", city: "Ciudad independiente (separada de cualquier condado)",
      howBuilt: "Cómo se suma la calificación",
      mosaicHelp: "Más ancho: te importa más. Más alto: a este lugar le va mejor. Las partes rayadas no tienen datos y no cuentan.",
      notCounted: "No cuenta: aún no hay datos",
      weightOf: "{w}% de tu calificación",
      confLine: "Basado en {k} de {n} partes. Los datos que faltan o son viejos la bajan.",
      helpHere: "Lugares de ayuda en el mapa", helpNone: "Aún no hay lugares de ayuda en el mapa aquí. Llama al 211 para hablar con alguien que conoce la zona.",
      k_clinic: "Clínica", k_shelter: "Albergue", k_food_bank: "Banco de comida", k_day_center: "Centro de día", k_soup_kitchen: "Comidas gratis",
      back: "Atrás", tapZoom: "Acercamos el mapa. Ahora toca el lugar exacto.", changeSpot: "Toca el mapa otra vez para mover el punto.",
      search: "Busca una ciudad o condado", allPlaces: "Los 133 lugares", noMatch: "Ninguna ciudad o condado coincide.",
      details: "Detalles", detailsEn: "Detalles (en inglés)",
      machine: "Traducción automática. Aún no la revisa un hablante nativo.",
      sz0: "estudio", sz1: "1 recámara", sz2: "2 recámaras", sz3: "3 recámaras", sz4: "4 recámaras",
      line_rent: "{rent} al mes por un {size}: {hours} horas de trabajo a salario mínimo por semana",
      line_shelter: "{pct}% de las personas sin hogar durmieron afuera. {beds} camas de albergue para {people} personas.",
      line_shelter_kids: "{pct}% de las personas sin hogar durmieron afuera. {beds} camas familiares para {people} personas en familias.",
      line_services: "{groc} tiendas aceptan EBT. {help} lugares de ayuda en el mapa.",
      line_transit: "Los autobuses son gratis.",
      law_0: "Aquí está prohibido dormir afuera en lugares públicos.", law_35: "Aquí se limita dormir afuera.", law_60: "La ciudad cierra algunos campamentos.",
      law_null: "Aún no revisamos las reglas locales.",
      safe_10: "La policía local trabaja con ICE (287(g), fuerza de tarea).", safe_40: "La cárcel puede retener personas para ICE (287(g)).", safe_80: "No aparece un acuerdo local con ICE.",
      line_crime: "{x} delitos violentos reportados por cada 1,000 personas (2025).", crime_null: "No hay datos confiables de delitos para 2025.",
      line_community: "{n} calificaciones de personas que estuvieron aquí.", community_null: "Aún no hay calificaciones.",
      topVa: "Lo mejor para ti en Virginia", programsVa: "Lo que puedes usar en Virginia",
      statewide: "Esto es igual en toda Virginia.",
      rankOf: "#{r} de {n}", sourceWord: "Fuente", seeAll: "Ver los 133",
      rateHelpVa: "Toca el mapa donde estuviste. Tu calificación se guarda en un cuadro de 1 km, no en tu lugar exacto. Sin nombres ni texto.",
      ratedThanks: "Gracias. Tu calificación cuenta para {place}.",
      phone: "Teléfono", hours: "Horario",
      partOf: "Parte del conteo de {coc}.",
      unknownParts: "No cuenta en esta calificación",
      _end: ""
    }
  };
  /* Spanish for the "why" sentences fit.js builds. fit.js stays English so it matches fit.py exactly
     (tests/test_fit.py); translation happens only at display time. Notes copied from source documents
     (KFF, NILC, statutes) are not translated; they keep their English wording and are marked "(en inglés)". */
  var ES_FIXED = {
    "SNAP: yes": "SNAP: sí", "SNAP: no": "SNAP: no califica", "SNAP: limited": "SNAP: en parte", "SNAP: varies": "SNAP: depende",
    "SNAP: yes (disability exemption from the 5-year wait)": "SNAP: sí (la discapacidad te exime de la espera de 5 años)",
    "SNAP: children can get it now; adults wait 5 years": "SNAP: los niños pueden recibirlo ya; los adultos esperan 5 años",
    "SNAP: U.S.-citizen children in the family can get it": "SNAP: los niños ciudadanos de la familia pueden recibirlo",
    "ER care, health centers and emergency Medicaid only": "Solo sala de emergencias, centros de salud y Medicaid de emergencia",
    "Medicaid expansion state: low-income adults qualify": "Estado con expansión de Medicaid: los adultos de bajos ingresos califican",
    "No Medicaid expansion; kids, pregnancy or disability can still qualify": "Sin expansión de Medicaid; niños, embarazo o discapacidad aún pueden calificar",
    "No Medicaid expansion: most adults without kids fall in the coverage gap": "Sin expansión de Medicaid: la mayoría de los adultos sin hijos se quedan sin cobertura",
    "Many states cover lawfully residing kids and pregnant people now": "Muchos estados cubren ya a niños y embarazadas con residencia legal",
    "5-year Medicaid wait; Marketplace tax credits available": "Espera de 5 años para Medicaid; hay créditos fiscales del Marketplace",
    "State covers children regardless of status": "El estado cubre a los niños sin importar su estatus",
    "Many states cover lawfully residing children": "Muchos estados cubren a niños con residencia legal",
    "Many states cover lawfully residing pregnant people": "Muchos estados cubren a embarazadas con residencia legal",
    "No Medicaid for adults since Oct 1, 2026; limited Marketplace help": "Sin Medicaid para adultos desde el 1 de oct. de 2026; poca ayuda del Marketplace",
    "Emergency Medicaid covers labor and delivery": "El Medicaid de emergencia cubre el parto",
    "Most states license people with a pending case and work permit": "La mayoría de los estados dan licencia si tienes caso pendiente y permiso de trabajo",
    "Can get a state ID or license with your documents": "Puedes sacar identificación o licencia estatal con tus documentos",
    "State requires proof of lawful presence for a license": "El estado pide prueba de presencia legal para la licencia",
    "You chose not to say your status, so this part is not scored. Help that is open to everyone is listed below.":
      "Elegiste no decir tu estatus, así que esta parte no se califica. Abajo está la ayuda abierta a todos.",
    "Add your status (it stays on this phone) to see which programs you can use here.":
      "Agrega tu estatus (se queda en este teléfono) para ver qué programas puedes usar aquí.",
    "Shown only if your status could be affected by immigration enforcement.": "Solo se muestra si tu estatus podría verse afectado por la aplicación de leyes de inmigración.",
    "Not checked: we have not confirmed a statewide camping law either way.": "Sin revisar: no hemos confirmado si hay o no una ley estatal sobre acampar.",
    "No ratings yet. Be the first to rate a place here.": "Todavía no hay calificaciones. Sé la primera persona en calificar un lugar aquí."
  };
  var ES_LABEL = {
    "Most protective": "La más protectora", "Broad sanctuary protections": "Amplias protecciones de santuario",
    "Meaningful, more limited protections": "Protecciones reales pero más limitadas", "Smaller steps": "Pasos más pequeños",
    "No law either way": "Sin ley en ningún sentido", "Mandates participation or bans sanctuary policies": "Obliga a colaborar o prohíbe políticas de santuario",
    "Broad anti-sanctuary law": "Ley amplia contra santuarios", "Fairly comprehensive anti-immigrant law": "Ley antiinmigrante bastante amplia",
    "Most far-reaching enforcement laws": "Las leyes de control más duras",
    "license": "licencia", "limited-purpose license": "licencia de uso limitado", "driving privilege card": "tarjeta de privilegio de manejo",
    "driver authorization card": "tarjeta de autorización para manejar", "privilege card": "tarjeta de privilegio",
    "open": "abierto", "limited": "limitado", "closed": "cerrado"
  };
  var EN_NOTE = " (en inglés)";
  var ES_PATTERNS = [
    [/^State food program: (.*)$/, function (m) { return "Programa estatal de comida: " + m[1] + (m[1] ? EN_NOTE : ""); }],
    [/^State program for adults: (\w+)\. (.*)$/, function (m) { return "Programa estatal para adultos: " + (ES_LABEL[m[1]] || m[1]) + ". " + m[2] + (m[2] ? EN_NOTE : ""); }],
    [/^State issues a (.+) regardless of status$/, function (m) { return "El estado da " + (ES_LABEL[m[1]] || m[1]) + " sin importar el estatus"; }],
    [/^([\d.]+) hours\/week at the \$([\d.]+) minimum wage to afford a 2-bedroom \(\$([\d.]+)\/hr needed\)$/,
      function (m) { return m[1] + " horas por semana con el salario mínimo de $" + m[2] + " para pagar 2 recámaras (se necesitan $" + m[3] + "/hora)"; }],
    [/^(\d+)% of ([\d,]+) people without homes slept outside \(Jan 2025 count\)$/,
      function (m) { return "El " + m[1] + "% de " + m[2] + " personas sin hogar durmió afuera (conteo de enero de 2025)"; }],
    [/^State law: (.+) \(tier (\d) of 9\)$/, function (m) { return "Ley estatal: " + (ES_LABEL[m[1]] || m[1]) + " (nivel " + m[2] + " de 9)"; }],
    [/^Statewide camping law: (.*)$/, function (m) { return "Ley estatal contra acampar: " + m[1] + EN_NOTE; }],
    [/^State law pushes cities to enforce camping bans: (.*)$/, function (m) { return "Una ley estatal presiona a las ciudades para aplicar prohibiciones de acampar: " + m[1] + EN_NOTE; }],
    [/^Statewide camping law in court: (.*)$/, function (m) { return "Ley estatal contra acampar, en los tribunales: " + m[1] + EN_NOTE; }],
    [/^(\d+) ratings? from people who have been here$/, function (m) { return m[1] + (m[1] === "1" ? " calificación" : " calificaciones") + " de gente que estuvo aquí"; }]
  ];
  function matchPattern(text) {
    for (var i = 0; i < ES_PATTERNS.length; i++) {
      var m = text.match(ES_PATTERNS[i][0]);
      if (m) return ES_PATTERNS[i][1](m);
    }
    return null;
  }
  function known(text) { return ES_FIXED.hasOwnProperty(text) || matchPattern(text) !== null; }
  /** Translate one sentence; null when we have no Spanish for it. */
  function reasonPart(text) { return ES_FIXED.hasOwnProperty(text) ? ES_FIXED[text] : matchPattern(text); }
  /** Translate a fit.js reason for display. English passes through unchanged.
      Reasons are joined with "; " by fit.js, but fixed sentences and quoted source notes can contain "; " too,
      so join the longest run of pieces that is a known sentence, and let a quoted note run until the next
      piece that is a known sentence on its own. */
  function reason(lang, text) {
    if (lang !== "es" || !text) return text;
    var parts = text.split("; "), out = [], i = 0;
    while (i < parts.length) {
      var done = false;
      for (var j = parts.length; j > i && !done; j--) {
        var joined = parts.slice(i, j).join("; ");
        if (ES_FIXED.hasOwnProperty(joined)) { out.push(ES_FIXED[joined]); i = j; done = true; }
      }
      if (done) continue;
      if (matchPattern(parts[i]) !== null) {
        var k = i + 1;
        while (k < parts.length && !known(parts[k]) && !ES_FIXED.hasOwnProperty(parts.slice(k, k + 2).join("; "))) k++;
        var tr = matchPattern(parts.slice(i, k).join("; "));
        out.push(tr !== null ? tr : parts.slice(i, k).join("; "));
        i = k; continue;
      }
      out.push(parts[i]); i++;
    }
    return out.join("; ");
  }
  function t(lang, key, vars) {
    var s = (S[lang] && S[lang][key]) || S.en[key] || key;
    if (vars) s = s.replace(/\{(\w+)\}/g, function (match, k) {
      return Object.prototype.hasOwnProperty.call(vars, k) ? String(vars[k]) : match;
    });
    return s;
  }
  /** Virginia component -> plain text runs. Quote runs carry lang=en for screen readers.
   * Use textContent/HTML escaping at the call site. No returned text is safe HTML.
   * Fail on missing templates/metadata instead of silently leaking English into Details.
   */
  function vaReasonParts(lang, component) {
    if (lang === "en") return [{ text: component.reason, lang: "en", kind: "translation" }];
    var data = component.reason_data, tables = root.FootingI18n.vaReasonTemplates;
    if (!data || data.version !== 1 || !Array.isArray(data.segments)) throw new Error("Missing Virginia reason_data v1");
    var table = tables && tables[lang];
    if (!table) throw new Error("Unsupported Virginia reason language: " + lang);
    var runs = [];
    data.segments.forEach(function (segment) {
      var template = table[segment.key], values = segment.vars || {};
      if (typeof template !== "string") throw new Error("Missing Virginia reason template: " + lang + "/" + segment.key);
      if (segment.key === "recorded_note") {
        runs.push({ text: template, lang: lang, kind: "quote_label" });
        runs.push({ text: "“" + values.text + "”", lang: "en", kind: "quote" });
        return;
      }
      var text = template.replace(/\{(\w+)\}/g, function (_, key) {
        if (!Object.prototype.hasOwnProperty.call(values, key)) throw new Error("Missing Virginia reason value: " + key);
        if (segment.key === "rent" && key === "size") {
          var size = S[lang] && (S[lang]["sz" + values.size] ||
            (values.size > 4 && S[lang].szMany ? S[lang].szMany.replace("{n}", values.size) : null));
          if (!size) throw new Error("Missing Virginia bedroom translation");
          return size;
        }
        return String(values[key]);
      });
      runs.push({ text: text, lang: lang, kind: "translation" });
    });
    return runs;
  }
  function vaReason(lang, component) {
    return vaReasonParts(lang, component).map(function (run) { return run.text; }).join(" ");
  }
  root.FootingI18n = { t: t, strings: S, reason: reason, _reasonPart: reasonPart,
    vaReason: vaReason, vaReasonParts: vaReasonParts };
})(typeof self !== "undefined" ? self : this);
