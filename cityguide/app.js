// --- STATE & CONFIG ---
let map;
let placesService = null;
let venues = [];
let venueMapboxMarkers = [];
let currentPlaceMarkers = []; 
let selectedVenue = null;
let topPicksByKey = {};
let currentCategory = "pregame";

// NEW EXTENDED CONFIG (Broader radii, new categories mapped to Google APIs)
const TIMELINE_CONFIG = {
  pregame:    { radius: 3000, mbcat: "restaurant",         mbtext: "restaurant" },
  quickbites: { radius: 3000, mbcat: "fast_food",          mbtext: "fast food" },
  recovery:   { radius: 5000, mbcat: "coffee",             mbtext: "coffee shop" },
  afterglow:  { radius: 4000, mbcat: "bar",                mbtext: "bar" },
  photoops:   { radius: 3000, mbcat: "tourist_attraction", mbtext: "tourist attraction" },
  getready:   { radius: 3000, mbcat: "pharmacy",           mbtext: "pharmacy" },
  parking:    { radius: 2500, mbcat: "parking_lot",        mbtext: "parking" },
  transit:    { radius: 3000, mbcat: "train_station",      mbtext: "train station" },
  stay:       { radius: 8000, mbcat: "hotel",              mbtext: "hotel" }
};

// --- MATH & UTILS ---
function makeVenueKey(name, city, state) { 
  return (name + "|" + city + "|" + state).toLowerCase(); 
}

function distanceMeters(lat1, lng1, lat2, lng2) {
  const R = 6371000;
  const toRad = x => (x * Math.PI) / 180;
  const a = Math.sin(toRad(lat2 - lat1) / 2) * Math.sin(toRad(lat2 - lat1) / 2) + 
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(toRad(lng2 - lng1) / 2) * Math.sin(toRad(lng2 - lng1) / 2);
  return R * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
}

function getWalkScore(meters) {
  const minutes = Math.round(meters / 80); 
  if (minutes <= 3) return "📍 Steps away";
  if (minutes <= 20) return `🚶 ${minutes} min walk`;
  return `🚗 ${(meters / 1609.34).toFixed(1)} mi`;
}

// --- INITIALIZE HEADLESS GOOGLE PLACES ---
window.initGoogleAPI = function() {
  const dummyDiv = document.getElementById("googlePlacesBrain");
  if(dummyDiv) {
    placesService = new google.maps.places.PlacesService(dummyDiv);
  }
};

// --- INITIALIZE MAPBOX & APP ---
document.addEventListener("DOMContentLoaded", () => {
  if (!mapboxgl.supported()) {
    console.warn("WebGL not supported. 3D maps may not render.");
  }

  mapboxgl.accessToken = 'pk.eyJ1Ijoiandjb25jZXJ0byIsImEiOiJjbXEydDBmZWYwN3I3MnFvZmN1aHN6bmd6In0.Tr4r5AIYnOdE7VAD_MvH7A';

  map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/light-v11',
    center: [-98.35, 39.5],
    zoom: 3.5,
    pitch: 0, 
    antialias: true
  });

  map.on('load', () => {
    map.addLayer({
      'id': '3d-buildings',
      'source': 'composite',
      'source-layer': 'building',
      'filter': ['==', 'extrude', 'true'],
      'type': 'fill-extrusion',
      'minzoom': 14,
      'paint': {
        'fill-extrusion-color': '#E2E8F0',
        'fill-extrusion-height': ['get', 'height'],
        'fill-extrusion-base': ['get', 'min_height'],
        'fill-extrusion-opacity': 0.8
      }
    });
    
    loadData();
    setupEventListeners();
  });
});

// --- DATA LOADING & MARKERS ---
function loadData() {
  // Ensure absolute paths so it always looks in the root data folder
  fetch("/data/venues.json")
    .then(res => res.json())
    .then(data => {
      venues = data;
      venues.forEach(v => {
        v.key = makeVenueKey(v.name, v.city, v.state);
        
        const el = document.createElement('div');
        el.className = 'venue-marker';
        
        const marker = new mapboxgl.Marker(el)
          .setLngLat([v.lng, v.lat])
          .addTo(map);
          
        el.addEventListener('click', () => {
          document.getElementById("venueSearch").value = v.name;
          document.getElementById("searchResults").classList.remove("visible");
          triggerVenueSelection(v);
          
          // Dynamically update the URL when a user clicks a map marker
          if (v.id) window.history.replaceState({}, '', '#' + v.id);
        });
        
        venueMapboxMarkers.push(marker);
      });
      return fetch("/data/top_picks.json");
    })
    .then(res => res.json())
    .then(tpData => {
      tpData.forEach(entry => topPicksByKey[makeVenueKey(entry.venueName, entry.city, entry.state)] = entry.items);
      
      // --- THE MAGIC LINK CHECKER ---
      const urlParams = new URLSearchParams(window.location.search);
      const incomingQuery = urlParams.get('venue');
      
      // Look for hashes (#madison-square-garden) or paths (/madisonsquaregarden)
      const hashPath = window.location.hash.replace(/^#\/?/, '').toLowerCase(); 
      const urlPath = (window.location.pathname.split('/').filter(Boolean).pop() || '').replace(/\.html$/, '').toLowerCase(); 
      
      let targetVenue = null;

      if (incomingQuery) {
        // Fallback for your old ?venue= links
        targetVenue = venues.find(v => v.name.toLowerCase() === incomingQuery.toLowerCase());
      } else {
        // Strip hyphens and spaces so "/madisonsquaregarden" or "/#madison-square-garden" both match seamlessly
        const searchString = (hashPath || urlPath).replace(/[^a-z0-9]/g, '');
        
        if (searchString && searchString !== 'indexhtml') {
          targetVenue = venues.find(v => {
            const cleanId = (v.id || '').replace(/[^a-z0-9]/g, '');
            const cleanName = v.name.toLowerCase().replace(/[^a-z0-9]/g, '');
            // Matches against the "id" field first, then the "name" field
            return cleanId === searchString || cleanName === searchString;
          });
        }
      }

      if (targetVenue) {
        setTimeout(() => {
          const searchInput = document.getElementById("venueSearch");
          if(searchInput) searchInput.value = targetVenue.name;
          triggerVenueSelection(targetVenue);
          
          // Clean up the URL to show the proper ID format
          if (targetVenue.id) window.history.replaceState({}, '', '#' + targetVenue.id);
        }, 800); 
      }
      // --- END MAGIC LINK CHECKER ---

    })
    .catch(err => {
      console.error("Data load error:", err);
    });
}

function clearPlaceMarkers() {
  currentPlaceMarkers.forEach(m => m.remove());
  currentPlaceMarkers = [];
}

// --- VENUE SELECTION (THE 3D FLYOVER) ---
function triggerVenueSelection(v) {
  selectedVenue = v;
  clearRoute(); 
  
  map.flyTo({
    center: [v.lng, v.lat],
    zoom: 15.5,
    pitch: 60, 
    bearing: 20, 
    duration: 1200, 
    padding: { bottom: 300 } 
  });

  const key = v.key || makeVenueKey(v.name, v.city, v.state);
  const hasTopPicks = topPicksByKey[key] && topPicksByKey[key].length > 0;
  
  document.querySelectorAll(".timeline-pill").forEach(p => p.classList.remove("active"));
  const tpPill = document.getElementById("pill-toppicks");
  
  if (hasTopPicks) {
    tpPill.classList.remove("hidden-pill");
    currentCategory = "toppicks";
    tpPill.classList.add("active");
  } else {
    tpPill.classList.add("hidden-pill");
    currentCategory = "pregame";
    document.getElementById("pill-pregame").classList.add("active");
  }
  
  document.getElementById("guideVenueName").textContent = v.name;
  document.getElementById("guideVenueLocation").textContent = `${v.city}, ${v.state}`;
  document.getElementById("guidePanel").classList.remove("hidden");
  document.querySelector(".timeline-scroller").scrollLeft = 0;
  
  loadPlacesForTimeline(currentCategory);
}

// --- GLOWING WALKING ROUTE ---
async function drawRoute(startLng, startLat, endLng, endLat) {
  const url = `https://api.mapbox.com/directions/v5/mapbox/walking/${startLng},${startLat};${endLng},${endLat}?geometries=geojson&access_token=${mapboxgl.accessToken}`;
  
  try {
    const response = await fetch(url);
    const data = await response.json();
    if(!data.routes || !data.routes[0]) return;
    const route = data.routes[0].geometry;
    
    if (map.getSource('route')) {
      map.getSource('route').setData(route);
    } else {
      map.addSource('route', { 'type': 'geojson', 'data': route });
      
      map.addLayer({
        'id': 'route-glow', 'type': 'line', 'source': 'route',
        'layout': { 'line-join': 'round', 'line-cap': 'round' },
        'paint': { 'line-color': '#C9A84C', 'line-width': 8, 'line-opacity': 0.3, 'line-blur': 4 }
      });
      
      map.addLayer({
        'id': 'route-core', 'type': 'line', 'source': 'route',
        'layout': { 'line-join': 'round', 'line-cap': 'round' },
        'paint': { 'line-color': '#C9A84C', 'line-width': 3 }
      });
    }

    const bounds = new mapboxgl.LngLatBounds([startLng, startLat], [startLng, startLat]);
    bounds.extend([endLng, endLat]);
    map.fitBounds(bounds, { padding: { top: 100, bottom: 400, left: 50, right: 50 }, duration: 1000 });
    
  } catch(e) { console.error("Could not fetch route", e); }
}

function clearRoute() {
  if (map.getSource('route')) {
    map.getSource('route').setData({ type: 'FeatureCollection', features: [] });
  }
}

// --- RENDER GOOGLE PLACES & TOP PICKS ---
function loadPlacesForTimeline(catKey) {
  const resultsEl = document.getElementById("guideResults");
  resultsEl.innerHTML = '<div style="padding: 20px; color: #5E6B86; font-size: 14px;">Curating the timeline...</div>';
  clearPlaceMarkers(); 

  // 1. TOP PICKS RENDERING
  if (catKey === "toppicks") {
    resultsEl.innerHTML = "";
    const picks = topPicksByKey[selectedVenue.key] || [];
    
    picks.forEach(item => {
      const card = document.createElement("div");
      card.className = "place-card top-pick-card";
      if (item.tier === "partner") card.classList.add("is-partner");
      let walkHTML = "";
      
      if (item.lat && item.lng) {
        walkHTML = `<span class="walk-badge">${getWalkScore(distanceMeters(selectedVenue.lat, selectedVenue.lng, item.lat, item.lng))}</span>`;
        const el = document.createElement('div'); el.className = 'place-marker';
        
        // Make Top Pick map markers clickable
        el.addEventListener('click', () => showPlaceDetails(item, true));
        
        const m = new mapboxgl.Marker(el).setLngLat([item.lng, item.lat]).addTo(map);
        currentPlaceMarkers.push(m);
      }

      card.innerHTML = `
        <span class="top-pick-badge">★ ${item.badge || "Concerto Top Pick"}</span>
        <h3 class="place-name">${item.name}</h3>
        <p class="place-meta">${walkHTML} ${item.address || ""}</p>
        <p class="place-meta top-pick-notes">"${item.notes || ""}"</p>
      `;
      // Pass TRUE to signify this is a Top Pick (triggers background geocoding if needed)
      card.addEventListener("click", () => showPlaceDetails(item, true));
      resultsEl.appendChild(card);
    });
    return;
  }

  // 2. STANDARD PLACES RENDERING — Mapbox Search Box (no Google key required).
  //    The map and Top Picks already run on Mapbox; discovery now does too.
  const config = TIMELINE_CONFIG[catKey];
  resultsEl.innerHTML = '<div style="padding: 20px; color: #5E6B86; font-size: 14px;">Finding spots nearby…</div>';

  const _token = mapboxgl.accessToken;
  const _prox = selectedVenue.lng + "," + selectedVenue.lat;
  const _km = (config.radius || 3000) / 1000;
  const _dLat = _km / 111;
  const _dLng = _km / (111 * Math.cos(selectedVenue.lat * Math.PI / 180));
  const _bbox = [selectedVenue.lng - _dLng, selectedVenue.lat - _dLat, selectedVenue.lng + _dLng, selectedVenue.lat + _dLat].join(",");
  const _catUrl = `https://api.mapbox.com/search/searchbox/v1/category/${config.mbcat}?access_token=${_token}&proximity=${_prox}&bbox=${_bbox}&limit=10&language=en`;
  const _fwdUrl = `https://api.mapbox.com/search/searchbox/v1/forward?q=${encodeURIComponent(config.mbtext)}&access_token=${_token}&proximity=${_prox}&types=poi&limit=10&language=en`;

  const _norm = (f) => {
    const c = (f.geometry && f.geometry.coordinates) || [];
    const p = f.properties || {};
    return { name: p.name || "Place", address: p.full_address || p.place_formatted || p.address || "", lng: c[0], lat: c[1] };
  };

  fetch(_catUrl)
    .then(r => r.json())
    .then(data => {
      const feats = (data && data.features) || [];
      if (feats.length) return feats;
      // Category returned nothing — fall back to a text search so the tab still fills.
      return fetch(_fwdUrl).then(r => r.json()).then(d2 => (d2 && d2.features) || []);
    })
    .then(feats => {
      resultsEl.innerHTML = "";
      const places = feats.map(_norm).filter(p => p.lat != null && p.lng != null);
      if (!places.length) {
        resultsEl.innerHTML = '<div style="padding: 20px; color: #5E6B86; font-size: 14px;">No spots found in range. Try another category or zoom the map.</div>';
        return;
      }
      places.sort((a, b) =>
        distanceMeters(selectedVenue.lat, selectedVenue.lng, a.lat, a.lng) -
        distanceMeters(selectedVenue.lat, selectedVenue.lng, b.lat, b.lng)
      );
      places.forEach(place => {
        const card = document.createElement("div");
        card.className = "place-card";

        let walkHTML = "";
        if (place.lat != null && place.lng != null) {
          walkHTML = `<span class="walk-badge">${getWalkScore(distanceMeters(selectedVenue.lat, selectedVenue.lng, place.lat, place.lng))}</span>`;
          const el = document.createElement('div'); el.className = 'place-marker';
          el.addEventListener('click', () => showPlaceDetails(place, false));
          const m = new mapboxgl.Marker(el).setLngLat([place.lng, place.lat]).addTo(map);
          currentPlaceMarkers.push(m);
        }

        card.innerHTML = `
        <h3 class="place-name">${place.name}</h3>
        <p class="place-meta">${walkHTML} ${place.address || ""}</p>
      `;
        card.addEventListener("click", () => showPlaceDetails(place, false));
        resultsEl.appendChild(card);
      });
    })
    .catch(err => {
      console.error("[CityGuide] Mapbox places error:", err);
      resultsEl.innerHTML = '<div style="padding: 20px; color: #5E6B86; font-size: 14px;">Could not load recommendations right now. Please try again.</div>';
    });
}

// --- Placement tap tracking (fire-and-forget; only Top Picks carry a trackingId) ---
function trackTap(trackingId, ev) {
  if (!trackingId || !navigator.sendBeacon) return;
  try {
    navigator.sendBeacon(
      'https://concertocity.com/.netlify/functions/track',
      JSON.stringify({ trackingId: trackingId, event: ev, ts: Date.now() })
    );
  } catch (e) {}
}

// --- RICH DETAILS, SMART ROUTING & POP-UP LOGIC ---
function showPlaceDetails(place, isTopPick) {
  try {
    document.getElementById("guidePanel").classList.add("hidden");
    document.getElementById("placeDetails").classList.remove("hidden");
    
    // 1. Set Base Data
    document.getElementById("detailsName").textContent = place.name || "Location";
    const address = place.vicinity || place.formatted_address || place.address || "";
    document.getElementById("detailsAddress").textContent = address;
    
    const metaBits = [];
    if (place.rating) metaBits.push(`${Number(place.rating).toFixed(1)}★`);
    if (place.notes) metaBits.push(`Concerto Curated`); 
    document.getElementById("detailsMeta").textContent = metaBits.join(" • ");

    // Track engagement the moment a Top Pick detail opens
    if (isTopPick && place.trackingId) trackTap(place.trackingId, 'open');

    // 2. Setup Open in Maps Button
    const routeBtn = document.getElementById("detailsMapsLink");
    let destName = encodeURIComponent((place.name || "") + " " + address);
    let mapsUrl = `https://maps.google.com/maps?daddr=${destName}`;
    routeBtn.href = mapsUrl;
    routeBtn.target = "_system";
    if (isTopPick && place.trackingId) routeBtn.onclick = () => trackTap(place.trackingId, 'maps');

    // 3. Hide Action Buttons by Default
    const phoneBtn = document.getElementById("detailsPhoneBtn");
    const webBtn = document.getElementById("detailsWebsiteBtn");
    if(phoneBtn) phoneBtn.hidden = true; 
    if(webBtn) webBtn.hidden = true;

    // 4. Routing (Mapbox). Geocode only if a Top Pick is missing coordinates.
    if (isTopPick && (!place.lat || !place.lng) && selectedVenue) {
      const _q = encodeURIComponent((place.name || "") + " " + address);
      const _u = `https://api.mapbox.com/search/searchbox/v1/forward?q=${_q}&access_token=${mapboxgl.accessToken}&proximity=${selectedVenue.lng},${selectedVenue.lat}&limit=1&language=en`;
      fetch(_u).then(r => r.json()).then(d => {
        const f = d && d.features && d.features[0];
        if (f && f.geometry && f.geometry.coordinates) {
          drawRoute(selectedVenue.lng, selectedVenue.lat, f.geometry.coordinates[0], f.geometry.coordinates[1]);
        }
      }).catch(() => {});
    } else if (selectedVenue) {
      // Standard place or Top Pick with coordinates
      let pLat = place.lat || (place.geometry ? place.geometry.location.lat() : null);
      let pLng = place.lng || (place.geometry ? place.geometry.location.lng() : null);
      if (pLat && pLng) drawRoute(selectedVenue.lng, selectedVenue.lat, pLng, pLat);
    }

    // --- Helper to fetch Price, Categories, Phone, Web (Removed opening_hours) ---
    function fetchRichDetails(placeId) {
      if(!placesService) return;
      placesService.getDetails({ 
        placeId: placeId, 
        fields: ['price_level', 'types', 'formatted_phone_number', 'website'] 
      }, (details, status) => {
        if (status === 'OK') {
          let updatedMeta = [];
          if (place.rating) updatedMeta.push(`${Number(place.rating).toFixed(1)}★`);
          if (details.price_level) updatedMeta.push('$'.repeat(details.price_level));
          
          if (details.types && details.types.length > 0) {
            let typeStr = details.types[0].replace(/_/g, ' ');
            updatedMeta.push(typeStr.charAt(0).toUpperCase() + typeStr.slice(1));
          }
          
          if (place.notes) {
             updatedMeta.push(`Concerto Curated`);
          }
          
          document.getElementById("detailsMeta").textContent = updatedMeta.join(" • ");

          if(details.formatted_phone_number && phoneBtn) {
            phoneBtn.hidden = false;
            phoneBtn.href = `tel:${details.formatted_phone_number.replace(/\D/g, '')}`;
            if (isTopPick && place.trackingId) phoneBtn.onclick = () => trackTap(place.trackingId, 'call');
          }
          if(details.website && webBtn) {
            webBtn.hidden = false;
            webBtn.href = details.website;
            if (isTopPick && place.trackingId) webBtn.onclick = () => trackTap(place.trackingId, 'website');
          }
        }
      });
    }

    // 5. When Closing Details
    document.getElementById("placeDetailsClose").onclick = () => {
      document.getElementById("placeDetails").classList.add("hidden");
      document.getElementById("guidePanel").classList.remove("hidden");
      clearRoute(); 
      map.flyTo({ center: [selectedVenue.lng, selectedVenue.lat], zoom: 15.5, pitch: 60, duration: 800, padding: {bottom: 300} });
    };

  } catch(e) { console.error(e); }
}

// --- EVENT LISTENERS ---
function setupEventListeners() {
  
  const guidePanel = document.getElementById("guidePanel");
  const dragHandle = document.querySelector(".drag-handle");
  const sheetHeader = document.querySelector(".sheet-header");
  const detailsCard = document.querySelector(".details-card");
  
  // --- HELPER: SMART MAP FRAMING ---
  function togglePanelExpansion(forceExpand = null) {
    const isExpanding = forceExpand !== null ? forceExpand : !guidePanel.classList.contains("expanded");
    
    if (isExpanding) {
      guidePanel.classList.add("expanded");
      // Push map center up so it isn't hidden by the giant panel
      map.easeTo({ padding: { bottom: window.innerHeight * 0.8 }, duration: 400 });
    } else {
      guidePanel.classList.remove("expanded");
      // Restore default map padding
      map.easeTo({ padding: { bottom: 300 }, duration: 400 });
    }
  }

  // 1. Click-to-toggle Main Panel
  dragHandle.addEventListener("click", () => togglePanelExpansion());

  // 2. Swipe-to-toggle Main Panel
  let startY = 0, currentY = 0;
  function handleTouchStart(e) { startY = e.touches[0].clientY; }
  function handleTouchMove(e) { currentY = e.touches[0].clientY; }
  function handleTouchEnd() {
    if (!startY || !currentY) return;
    const deltaY = currentY - startY;

    if (deltaY < -40) togglePanelExpansion(true); // Swiped Up
    else if (deltaY > 40) togglePanelExpansion(false); // Swiped Down
    
    startY = 0; currentY = 0;
  }

  [dragHandle, sheetHeader].forEach(el => {
    el.addEventListener('touchstart', handleTouchStart, { passive: true });
    el.addEventListener('touchmove', handleTouchMove, { passive: true });
    el.addEventListener('touchend', handleTouchEnd);
  });

  // 3. NEW: Swipe-to-Close on Place Details
  let detStartY = 0, detCurrentY = 0;
  detailsCard.addEventListener('touchstart', e => detStartY = e.touches[0].clientY, { passive: true });
  detailsCard.addEventListener('touchmove', e => detCurrentY = e.touches[0].clientY, { passive: true });
  detailsCard.addEventListener('touchend', () => {
    if (!detStartY || !detCurrentY) return;
    if (detCurrentY - detStartY > 50) { // Swiped down
      document.getElementById("placeDetailsClose").click(); // Trigger existing close logic
    }
    detStartY = 0; detCurrentY = 0;
  });

  // 4. NEW: Tap empty map to dismiss expansion
  map.on('click', (e) => {
    // Only trigger if we click the map background, not a marker
    if (guidePanel.classList.contains("expanded")) {
      togglePanelExpansion(false);
    }
  });

  // 5. Existing Close Button Logic
  document.getElementById("closePanelBtn").onclick = () => {
    guidePanel.classList.add("hidden");
    guidePanel.classList.remove("expanded"); 
    clearPlaceMarkers();
    clearRoute();
    map.flyTo({ pitch: 0, zoom: 4, duration: 1500, padding: {bottom: 0} }); 
  };
  
  // 6. Timeline Pills Logic
  document.querySelectorAll(".timeline-pill").forEach(pill => {
    pill.addEventListener("click", (e) => {
      document.querySelectorAll(".timeline-pill").forEach(p => p.classList.remove("active"));
      e.target.classList.add("active");
      loadPlacesForTimeline(e.target.dataset.cat);
    });
  });

  // 7. Search Bar Logic
  const searchInput = document.getElementById("venueSearch");
  const searchResults = document.getElementById("searchResults");
  searchInput.addEventListener("input", () => {
    const q = searchInput.value.trim().toLowerCase();
    searchResults.innerHTML = "";
    if (!q) { searchResults.classList.remove("visible"); return; }
    
    venues.filter(v => v.name.toLowerCase().includes(q) || v.city.toLowerCase().includes(q)).slice(0, 10).forEach(v => {
      const item = document.createElement("div");
      item.className = "search-result-item";
      item.textContent = `${v.name} — ${v.city}`;
      item.onclick = () => {
        searchInput.value = v.name;
        searchResults.classList.remove("visible");
        triggerVenueSelection(v);
      };
      searchResults.appendChild(item);
    });
    searchResults.classList.add("visible");
  });
}
