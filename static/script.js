let allHouses = [];
let filteredHouses = [];

const houseList = document.getElementById("house-list");
const searchInput = document.getElementById("search-input");
const sortBy = document.getElementById("sort-by");
const sortOrder = document.getElementById("sort-order");

let map;
let markersLayer;

// Получение данных
async function fetchHouses() {
    const response = await fetch("/houses");
    const data = await response.json();
    allHouses = data;
    if (!map) initMap(); // инициализируем карту один раз
    applyFilters();
}

// Фильтрация и сортировка
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

    renderHouses();
}

// Отображение списка домов
function renderHouses() {
    houseList.innerHTML = "";

    filteredHouses.forEach(house => {
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

    updateMapMarkers(filteredHouses);
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

// События фильтрации
searchInput.addEventListener("input", applyFilters);
sortBy.addEventListener("change", applyFilters);
sortOrder.addEventListener("change", applyFilters);

// Кнопка обновления данных
const runBtn = document.getElementById("run-tasks-btn");
if (runBtn) {
    runBtn.addEventListener("click", async () => {
        runBtn.disabled = true;
        const originalText = runBtn.innerHTML;
        runBtn.innerHTML = `<span class="spinner"></span> Обновляется... (обновление может занять несколько минут, подождите⌛)`;

        try {
            const res = await fetch("/run-tasks", { method: "POST" });
            const data = await res.json();
            if (data.status === "ok") {
                runBtn.innerHTML = "✅ Обновлено";
                await fetchHouses();
            } else {
                runBtn.innerHTML = "⚠️ Ошибка";
            }
        } catch {
            runBtn.innerHTML = "❌ Сбой сети";
        }

        setTimeout(() => {
            runBtn.disabled = false;
            runBtn.innerHTML = originalText;
        }, 3000);
    });
}

// Загрузка при старте
document.addEventListener("DOMContentLoaded", () => {
    fetchHouses();
});
