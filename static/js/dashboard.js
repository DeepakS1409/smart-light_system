document.addEventListener("DOMContentLoaded", function () {
    const mapElement = document.getElementById("map");
    if (!mapElement) return;

    // Initialize Leaflet Map (Centered on demonstration city coordinates)
    const map = L.map("map").setView([12.972, 77.595], 14);

    // OpenStreetMap standard tile layer
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Demonstration Data',
        maxZoom: 18
    }).addTo(map);

    // Fetch spatial features from API
    fetch("/dashboard/api/map-data")
        .then(res => res.json())
        .then(data => {
            const markers = [];

            // 1. Render Feeders (Group-Level Substation Boxes)
            data.feeders.forEach(feeder => {
                const isAlertActive = Boolean(feeder.alert_id && feeder.alert_status === "Active");

                // Feeder Icon: Distinct Square with Substation Icon
                const feederIcon = L.divIcon({
                    className: "feeder-marker",
                    html: `
                        <div style="
                            background-color: ${isAlertActive ? '#ef4444' : '#1e40af'};
                            color: white;
                            width: 34px;
                            height: 34px;
                            border-radius: 8px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            box-shadow: 0 0 10px ${isAlertActive ? 'rgba(239, 68, 68, 0.8)' : 'rgba(30, 64, 175, 0.4)'};
                            border: 2px solid white;
                            font-size: 16px;
                            font-weight: bold;
                        ">
                            <i class="bi ${isAlertActive ? 'bi-lightning-fill text-warning' : 'bi-building'}"></i>
                        </div>
                    `,
                    iconSize: [34, 34],
                    iconAnchor: [17, 17]
                });

                const popupContent = `
                    <div style="min-width: 220px; font-family: sans-serif;">
                        <span class="badge ${isAlertActive ? 'bg-danger' : 'bg-primary'} mb-1 text-uppercase">
                            ${isAlertActive ? 'Feeder Alert Active' : 'Feeder Normal'}
                        </span>
                        <h6 style="margin: 4px 0; font-weight: bold;">${feeder.feeder_code} - ${feeder.name}</h6>
                        <div style="font-size: 12px; color: #475569; margin-bottom: 6px;">
                            <strong>Zone:</strong> ${feeder.zone} &bull; <strong>Nominal:</strong> ${feeder.nominal_voltage}V
                        </div>
                        ${isAlertActive ? `
                            <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 6px; border-radius: 4px; font-size: 11px; color: #991b1b; margin-bottom: 8px;">
                                <strong>${feeder.alert_type} (HIGH PRIORITY)</strong><br>
                                Telemetry: ${feeder.alert_voltage}V / ${feeder.alert_current}A<br>
                                <em>${feeder.alert_desc || ''}</em>
                            </div>
                        ` : '<div style="font-size: 12px; color: #16a34a; margin-bottom: 8px;"><i class="bi bi-check-circle"></i> Telemetry normal.</div>'}
                        <a href="/simulator/" class="btn btn-sm btn-outline-dark w-100" style="font-size: 11px; padding: 2px 6px;">
                            Open Feeder Simulator
                        </a>
                    </div>
                `;

                const marker = L.marker([feeder.latitude, feeder.longitude], { icon: feederIcon })
                    .bindPopup(popupContent)
                    .addTo(map);
                markers.push(marker);
            });

            // 2. Render Light Poles
            data.poles.forEach(pole => {
                const hasComplaint = Boolean(pole.complaint_id);
                let color = "#64748b"; // default operational
                let radius = 7;

                if (hasComplaint) {
                    radius = 9;
                    if (pole.priority === "HIGH") color = "#dc2626";
                    else if (pole.priority === "MEDIUM") color = "#d97706";
                    else color = "#2563eb";
                }

                const poleMarker = L.circleMarker([pole.latitude, pole.longitude], {
                    radius: radius,
                    fillColor: color,
                    color: "#ffffff",
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.9
                });

                const navUrl = `https://www.google.com/maps/dir/?api=1&destination=${pole.latitude},${pole.longitude}`;

                const polePopup = `
                    <div style="min-width: 220px; font-family: sans-serif;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <strong style="font-size: 14px;">Pole ${pole.pole_code}</strong>
                            <span class="badge bg-secondary">${pole.zone}</span>
                        </div>
                        <div style="font-size: 12px; color: #64748b; margin-bottom: 6px;">
                            ${pole.landmark}
                        </div>
                        ${pole.is_high_risk ? `
                            <div style="background: #fee2e2; color: #991b1b; padding: 3px 6px; border-radius: 4px; font-size: 11px; margin-bottom: 6px;">
                                <i class="bi bi-exclamation-triangle-fill"></i> High Risk: ${pole.high_risk_reason}
                            </div>
                        ` : ''}
                        ${hasComplaint ? `
                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 6px; border-radius: 4px; font-size: 12px; margin-bottom: 8px;">
                                <strong>Ticket:</strong> ${pole.reference_no} (${pole.status})<br>
                                <strong>Fault:</strong> ${pole.category}<br>
                                <strong>Priority:</strong> <span style="font-weight: bold; color: ${color};">${pole.priority}</span><br>
                                ${pole.worker_name ? `<strong>Assigned:</strong> ${pole.worker_name}` : '<em class="text-muted">Unassigned</em>'}
                            </div>
                        ` : '<div style="font-size: 12px; color: #16a34a; margin-bottom: 8px;"><i class="bi bi-lightbulb"></i> Operational &bull; No active complaints</div>'}
                        <div style="display: flex; gap: 4px;">
                            <a href="${navUrl}" target="_blank" rel="noopener" class="btn btn-sm btn-primary w-100" style="font-size: 11px; padding: 3px 6px;">
                                <i class="bi bi-geo-alt-fill text-warning"></i> Navigate (Google Maps)
                            </a>
                            <a href="/complaint/report/${pole.pole_code}" class="btn btn-sm btn-outline-secondary w-100" style="font-size: 11px; padding: 3px 6px;">
                                Citizen Report
                            </a>
                        </div>
                    </div>
                `;

                poleMarker.bindPopup(polePopup).addTo(map);
                markers.push(poleMarker);
            });

            // Adjust bounds if markers exist
            if (markers.length > 0) {
                const group = new L.featureGroup(markers);
                map.fitBounds(group.getBounds().pad(0.1));
            }
        })
        .catch(err => console.error("Error loading map data:", err));

    // 3. Table Filtering Logic
    const searchInput = document.getElementById("tableSearch");
    const zoneFilter = document.getElementById("zoneFilter");
    const statusFilter = document.getElementById("statusFilter");
    const priorityFilter = document.getElementById("priorityFilter");
    const rows = document.querySelectorAll(".complaint-row");

    function filterTable() {
        const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
        const zone = zoneFilter ? zoneFilter.value : "";
        const status = statusFilter ? statusFilter.value : "";
        const priority = priorityFilter ? priorityFilter.value : "";

        let visibleCount = 0;

        rows.forEach(row => {
            const rowZone = row.getAttribute("data-zone") || "";
            const rowStatus = row.getAttribute("data-status") || "";
            const rowPriority = row.getAttribute("data-priority") || "";
            const rowText = row.innerText.toLowerCase();

            const matchesQuery = !query || rowText.includes(query);
            const matchesZone = !zone || rowZone === zone;
            const matchesStatus = !status || rowStatus === status;
            const matchesPriority = !priority || rowPriority === priority;

            if (matchesQuery && matchesZone && matchesStatus && matchesPriority) {
                row.style.display = "";
                visibleCount++;
            } else {
                row.style.display = "none";
            }
        });

        const emptyMessage = document.getElementById("tableEmptyMessage");
        if (emptyMessage) {
            emptyMessage.style.display = visibleCount === 0 ? "" : "none";
        }
    }

    if (searchInput) searchInput.addEventListener("input", filterTable);
    if (zoneFilter) zoneFilter.addEventListener("change", filterTable);
    if (statusFilter) statusFilter.addEventListener("change", filterTable);
    if (priorityFilter) priorityFilter.addEventListener("change", filterTable);
});
