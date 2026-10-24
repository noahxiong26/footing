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
      tapCloser: "Zoomed in. Now tap the exact spot.", back: "Back"
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
      legendLow: "Peor", legendHigh: "Mejor", legendUnknown: "Sin datos",
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
      tapCloser: "Acercamos el mapa. Ahora toca el lugar exacto.", back: "Volver"
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
    if (vars) Object.keys(vars).forEach(function (k) { s = s.replace("{" + k + "}", vars[k]); });
    return s;
  }
  root.FootingI18n = { t: t, strings: S, reason: reason, _reasonPart: reasonPart };
})(typeof self !== "undefined" ? self : this);
