// Initialize the map
const map = L.map('map').setView([markersData[0].lat, markersData[0].lon], 10);
console.log('markersData')

// Add a tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Function to get marker color based on status
function getMarkerColor(status) {
    switch (status) {
        case 'active': return 'green';
        case 'inactive': return 'red';
        default: return 'blue';
    }
}

// Loop through markers data and create markers with popups
markersData.forEach(markerData => {
    const marker = L.circleMarker([markerData.lat, markerData.lon], {
        radius: 6,
        color: getMarkerColor(markerData.status),
        fillColor: getMarkerColor(markerData.status),
        fillOpacity: 0.8
    }).addTo(map);

    const popupContent = `
        <b>Details:</b><br>
        ${Object.entries(markerData.tooltip).map(([col, value]) => `${col}: ${value}`).join('<br>')}
        <br><b>Status:</b>
        <select class="status-dropdown" data-latlon="${markerData.lat},${markerData.lon}" data-mapid="${markerData.mapid}">
            <option value="default" ${markerData.status === 'default' ? 'selected' : ''}>Default</option>
            <option value="active" ${markerData.status === 'active' ? 'selected' : ''}>Active</option>
            <option value="inactive" ${markerData.status === 'inactive' ? 'selected' : ''}>Inactive</option>
        </select>
        <br><br><b>Note:</b><br>
        <textarea class="note-field" data-latlon="${markerData.lat},${markerData.lon}" data-mapid="${markerData.mapid}">${markerData.note}</textarea>
    `;

    marker.bindPopup(popupContent);
});

// Event listener to update status and note
document.addEventListener('change', function(event) {
    if (event.target.classList.contains('status-dropdown')) {
        const latlon = event.target.dataset.latlon;
        const newStatus = event.target.value;
        const map_id = event.target.dataset.mapid;
        updateStatus(latlon, newStatus, map_id);
    } else if (event.target.classList.contains('note-field')) {
        const latlon = event.target.dataset.latlon;
        const newNote = event.target.value;
        const map_id = event.target.dataset.mapid;
        updateNote(latlon, newNote, map_id);
    }
});

function updateStatus(latlon, newStatus, mapId) {
    fetch('/update_point', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latlon: latlon, status: newStatus, map_id: mapId })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Status updated', data);
        const [lat, lon] = latlon.split(',').map(parseFloat);
        const marker = getMarkerByLatLon(lat, lon);
        if (marker) {
            marker.setStyle({ color: getMarkerColor(newStatus), fillColor: getMarkerColor(newStatus) });
        }
    });
}

function updateNote(latlon, newNote, map_id) {
    fetch('/update_point', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latlon: latlon, note: newNote, map_id: map_id })
    })
    .then(response => response.json())
    .then(data => console.log('Note updated', data));
}

function getMarkerByLatLon(lat, lon) {
    let foundMarker = null;
    map.eachLayer(layer => {
        if (layer instanceof L.CircleMarker) {
            const markerLatLng = layer.getLatLng();
            if (markerLatLng.lat.toFixed(6) === lat.toFixed(6) && markerLatLng.lng.toFixed(6) === lon.toFixed(6)) {
                foundMarker = layer;
            }
        }
    });
    return foundMarker;
}
