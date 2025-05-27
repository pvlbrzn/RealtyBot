let allHouses = [];
let filteredHouses = [];
let currentPage = 1;
const perPage = 10;

const houseList = document.getElementById("house-list");
const searchInput = document.getElementById("search-input");
const sortBy = document.getElementById("sort-by");
const sortOrder = document.getElementById("sort-order");
const pageNumber = document.getElementById("page-number");
const prevPageBtn = document.getElementById("prev-page");
const nextPageBtn = document.getElementById("next-page");

let map;
let markersLayer;

async function fetchHouses() {
    const response = await fetch("/houses");
    const data = await response.json();
    allHouses = data;
    initMap(); // инициализируем карту после загрузки данных
    applyFilters();
}

function applyFilters() {
    const search = searchInput.value.toLowerCase();
    const field = sortBy.value;
    const order = sortOrder.value;

    filteredHouses = allHouses
        .filter(h => h.position?.toLowerCase().includes(search))
        .sort((a, b) => {
            let valA = a[field] || "";
            let valB = b[field] || "";

            if (field.includes("date")) {
                valA = new Date(valA);
                valB = new Date(valB);
            } else {
                valA = valA.toString().toLowerCase();
                valB = valB.toString().toLowerCase();
            }

            return order === "asc" ? (valA > valB ? 1 : -1) : (valA < valB ? 1 : -1);
        });

    currentPage = 1;
    renderPage();
}

function renderPage() {
    const start = (currentPage - 1) * perPage;
    const end = start + perPage;
    const pageHouses = filteredHouses.slice(start, end);

    houseList.innerHTML = "";
    pageHouses.forEach(house => {
        const div = document.createElement("div");
        div.className = "house-card";
        div.innerHTML = `
            <h3>${house.position}</h3>
            <p><strong>Статус:</strong> ${house.state_type || "—"}</p>
            <p><strong>Дата:</strong> ${house.state_date || "—"}</p>
            <a href="${house.link}" target="_blank">Подробнее</a>
        `;
        houseList.appendChild(div);
    });

    pageNumber.textContent = currentPage;
    prevPageBtn.disabled = currentPage === 1;
    nextPageBtn.disabled = end >= filteredHouses.length;

    updateMapMarkers(pageHouses);
}

// Инициализация карты
function initMap() {
    map = L.map('map').setView([53.9, 27.56], 8); // Центр Минской области

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
    }).addTo(map);

    markersLayer = L.layerGroup().addTo(map);
}

// Обновление маркеров на карте
function updateMapMarkers(houses) {
    markersLayer.clearLayers();

    const bounds = [];

    houses.forEach(house => {
        if (house.latitude && house.longitude) {
            const marker = L.marker([house.latitude, house.longitude])
                .bindPopup(`<b>${house.position}</b><br><a href="${house.link}" target="_blank">Подробнее</a>`);
            markersLayer.addLayer(marker);
            bounds.push([house.latitude, house.longitude]);
        }
    });

    if (bounds.length) {
        map.fitBounds(bounds, { padding: [50, 50] });
    }
}

// События
searchInput.addEventListener("input", applyFilters);
sortBy.addEventListener("change", applyFilters);
sortOrder.addEventListener("change", applyFilters);

prevPageBtn.addEventListener("click", () => {
    if (currentPage > 1) {
        currentPage--;
        renderPage();
    }
});

nextPageBtn.addEventListener("click", () => {
    if (currentPage * perPage < filteredHouses.length) {
        currentPage++;
        renderPage();
    }
});

document.addEventListener("DOMContentLoaded", () => {
    fetchHouses();
});
