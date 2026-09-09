const MONTHS_FA = ["ژانویه","فوریه","مارس","آوریل","مه","ژوئن","ژوئیه","اوت","سپتامبر","اکتبر","نوامبر","دسامبر"];
const WEEKDAYS_FA = ["یکشنبه","دوشنبه","سه‌شنبه","چهارشنبه","پنجشنبه","جمعه","شنبه"];

const today = new Date();
today.setHours(0, 0, 0, 0);

let selectedMonth = 0;
let selectedCityId = "all";
let activeTour = null;
let livePrices = null;

function pad(n) {
  return String(n).padStart(2, "0");
}

function iso(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function faDate(date) {
  return `${WEEKDAYS_FA[date.getDay()]} ${date.getDate()} ${MONTHS_FA[date.getMonth()]} ${date.getFullYear()}`;
}

function monthLabel(offset) {
  const d = new Date(today.getFullYear(), today.getMonth() + offset, 1);
  const names = ["همین ماه", "ماه بعد", "دو ماه بعد"];
  return {
    offset,
    name: names[offset],
    detail: `${MONTHS_FA[d.getMonth()]} ${d.getFullYear()}`,
    year: d.getFullYear(),
    month: d.getMonth()
  };
}

function cheapStarts(year, month) {
  const last = new Date(year, month + 1, 0).getDate();
  const preferred = [];
  const fallback = [];
  const minDate = new Date(today);
  minDate.setDate(minDate.getDate() + 3);

  for (let day = 1; day <= last; day += 1) {
    const start = new Date(year, month, day);
    if (start < minDate) continue;
    const dow = start.getDay();
    if (dow === 2 || dow === 3) preferred.push(start);
    else if (dow === 1 || dow === 4) fallback.push(start);
  }
  return (preferred.length ? preferred : fallback).slice(0, 4);
}

function cityFromLocation() {
  const params = new URLSearchParams(location.search);
  if (params.get("city")) return params.get("city").toLowerCase();
  const match = location.pathname.match(/\/city\/([a-z0-9-]+)/i);
  return match ? match[1].toLowerCase() : null;
}

function setCityUrl(id) {
  const next = id && id !== "all" ? `/city/${id}` : "/";
  if (`${location.pathname}${location.search}` !== next) {
    history.replaceState({}, "", next);
  }
}

function monthOffer(cityId, offset) {
  return livePrices?.cities?.[cityId]?.months?.find((item) => item.offset === offset) || null;
}

function fallbackPrice(city, start) {
  const seasonal = { 8: 1.06, 9: 0.93, 10: 0.87, 11: 0.9 }[start.getMonth()] || 1;
  const midweek = start.getDay() === 2 || start.getDay() === 3 ? 0.91 : 1;
  const wobble = (city.base + start.getDate() * 17 + start.getMonth() * 11) % 37;
  return Math.max(390, Math.round(city.base * seasonal * midweek - wobble));
}

function priceFor(city, start, offset) {
  return monthOffer(city.id, offset)?.total2p || fallbackPrice(city, start);
}

function toursForMonth(offset) {
  const meta = monthLabel(offset);
  const starts = cheapStarts(meta.year, meta.month);
  const cities = selectedCityId === "all"
    ? window.NOURA_CITIES
    : window.NOURA_CITIES.filter((city) => city.id === selectedCityId);

  const tours = [];
  cities.forEach((city) => {
    const live = monthOffer(city.id, offset);
    if (live) {
      tours.push({
        city,
        start: new Date(`${live.checkIn}T12:00:00`),
        end: new Date(`${live.checkOut}T12:00:00`),
        nights: city.nights,
        people: 2,
        price: live.total2p,
        live: true,
        hotelName: live.hotelName,
        hotelMin: live.hotelMin,
        tourEstimate: live.tourEstimate,
        transferEstimate: live.transferEstimate
      });
      return;
    }
    const ranked = starts
      .map((start) => ({
        city,
        start,
        end: addDays(start, city.nights),
        nights: city.nights,
        people: 2,
        price: fallbackPrice(city, start),
        live: false
      }))
      .sort((a, b) => a.price - b.price);
    if (ranked[0]) tours.push(ranked[0]);
  });
  return tours.sort((a, b) => a.price - b.price);
}

function bookingUrl(tour) {
  const ss = encodeURIComponent(`${tour.city.city}, ${tour.city.country}`);
  return `https://www.booking.com/searchresults.html?ss=${ss}&checkin=${iso(tour.start)}&checkout=${iso(tour.end)}&group_adults=2&no_rooms=1&group_children=0&selected_currency=EUR`;
}

function guideUrl(tour) {
  return `https://www.getyourguide.com/s/?q=${encodeURIComponent(tour.city.city)}&date_from=${iso(tour.start)}&date_to=${iso(tour.end)}`;
}

function flightsUrl(tour) {
  return `https://www.google.com/travel/flights?hl=fa#flt=IKA.${tour.city.city}.${iso(tour.start)}*${tour.city.city}.IKA.${iso(tour.end)}`;
}

function renderHero() {
  const featured = window.NOURA_CITIES.find((city) => city.id === selectedCityId) || window.NOURA_CITIES[0];
  document.getElementById("hero-image").src = featured.image;
  document.getElementById("hero-chip-title").textContent = `${featured.cityFa}، ${featured.countryFa}`;
  const meta = monthLabel(0);
  const start = cheapStarts(meta.year, meta.month)[0] || today;
  document.getElementById("hero-chip-text").textContent = `ارزان‌ترین پنجره همین ماه از ${priceFor(featured, start, 0)} یورو برای دو نفر`;
}

function renderBento() {
  const picks = [0, 7, 13, 3, 16];
  const root = document.getElementById("bento");
  root.innerHTML = picks.map((index, i) => {
    const city = window.NOURA_CITIES[index];
    const cls = i === 0 ? "wide" : i === 4 ? "tall" : "";
    return `<button class="card ${cls}" onclick="openCity('${city.id}')">
      <img src="${city.image}" alt="${city.cityFa}">
      <div class="card-copy">
        <strong>${city.cityFa}</strong>
        <div>${city.vibe}</div>
      </div>
    </button>`;
  }).join("");
}

function renderCities() {
  document.getElementById("city-grid").innerHTML = window.NOURA_CITIES.map((city) => `
    <button class="city-tile" onclick="openCity('${city.id}')">
      <img src="${city.thumb}" alt="${city.cityFa}">
      <div>
        <h3>${city.cityFa}</h3>
        <span>${city.countryFa} · ${city.highlights.join("، ")}</span>
      </div>
    </button>
  `).join("");
}

function renderFilters() {
  const months = [0, 1, 2].map(monthLabel);
  document.getElementById("month-tabs").innerHTML = months.map((month) => `
    <button class="${month.offset === selectedMonth ? "active" : ""}" onclick="setMonth(${month.offset})">
      ${month.name} · ${month.detail}
    </button>
  `).join("");

  document.getElementById("city-filter").innerHTML = `<option value="all">همه شهرها</option>` +
    window.NOURA_CITIES.map((city) => `<option value="${city.id}" ${city.id === selectedCityId ? "selected" : ""}>${city.cityFa}</option>`).join("");
}

function renderPriceStamp() {
  const el = document.getElementById("price-stamp");
  if (!el) return;
  if (livePrices?.updatedAt) {
    const stamp = new Date(livePrices.updatedAt);
    el.textContent = `برآورد پویا · به‌روزرسانی سه‌بار در روز · آخرین بار ${stamp.toLocaleString("fa-IR")}`;
  } else {
    el.textContent = "برآورد پویا هنوز بارگذاری نشده است.";
  }
}

function renderTours() {
  const tours = toursForMonth(selectedMonth).slice(0, selectedCityId === "all" ? 9 : 4);
  document.getElementById("tour-list").innerHTML = tours.map((tour, index) => `
    <article class="tour-card">
      <img src="${tour.city.image}" alt="${tour.city.cityFa}">
      <div class="tour-body">
        <div class="meta">${tour.live ? "برآورد به‌روزشده" : index === 0 ? "ارزان‌ترین برآورد این بازه" : tour.city.countryFa}</div>
        <h3>${tour.city.cityFa}</h3>
        <div class="meta">${faDate(tour.start)} تا ${faDate(tour.end)}</div>
        <div class="price">${tour.price} <small>یورو / دو نفر</small></div>
        <div class="meta">${tour.nights} شب هتل مرکز شهر + تور شهری</div>
        <button class="btn" onclick='openTour(${JSON.stringify({
          id: tour.city.id,
          start: iso(tour.start),
          end: iso(tour.end),
          price: tour.price,
          live: Boolean(tour.live),
          hotelMin: tour.hotelMin || null,
          hotelName: tour.hotelName || null,
          tourEstimate: tour.tourEstimate || null,
          transferEstimate: tour.transferEstimate || null
        })})'>خرید تور</button>
      </div>
    </article>
  `).join("");
}

function setMonth(offset) {
  selectedMonth = offset;
  renderFilters();
  renderTours();
}

function setCity(id) {
  selectedCityId = id;
  setCityUrl(id);
  renderHero();
  renderTours();
}

function openCity(id) {
  selectedCityId = id;
  setCityUrl(id);
  renderHero();
  renderFilters();
  renderTours();
  document.getElementById("tours").scrollIntoView({ behavior: "smooth" });
}

function openTour(payload) {
  const city = window.NOURA_CITIES.find((item) => item.id === payload.id);
  const start = new Date(`${payload.start}T12:00:00`);
  const end = new Date(`${payload.end}T12:00:00`);
  activeTour = { city, start, end, nights: city.nights, people: 2, price: payload.price };
  const hotel = payload.hotelMin || Math.round(payload.price * 0.72);
  const guide = payload.tourEstimate || Math.round(payload.price * 0.18);
  const transfer = payload.transferEstimate || (payload.price - hotel - guide);
  document.getElementById("sheet-image").src = city.image;
  document.getElementById("sheet-title").textContent = `تور دونفره ${city.cityFa}`;
  document.getElementById("sheet-copy").innerHTML = `
    <p>${faDate(start)} تا ${faDate(end)} · ${city.nights} شب · ۲ نفر</p>
    <div class="breakdown">
      ${payload.hotelName ? `هتل: ${payload.hotelName}<br>` : ""}
      هتل ${payload.live ? "زنده" : "برآورد"}: ${hotel} یورو<br>
      تور شهری: ${guide} یورو<br>
      ترانسفر فرودگاهی: ${transfer} یورو<br>
      <strong>جمع برای دو نفر: ${payload.price} یورو</strong>
    </div>
    <p>تاریخ‌ها واقعی تقویم ${MONTHS_FA[start.getMonth()]} ${start.getFullYear()} هستند. خرید نهایی روی سایت‌های رزرو با همین تاریخ باز می‌شود.</p>
  `;
  document.getElementById("book-hotel").href = bookingUrl(activeTour);
  document.getElementById("book-guide").href = guideUrl(activeTour);
  document.getElementById("book-flights").href = flightsUrl(activeTour);
  document.getElementById("modal").classList.add("open");
}

function closeModal() {
  document.getElementById("modal").classList.remove("open");
}

async function loadPrices() {
  try {
    const response = await fetch(`/prices.json?t=${Date.now()}`);
    if (response.ok) livePrices = await response.json();
  } catch (error) {
    livePrices = null;
  }
}

window.setMonth = setMonth;
window.setCity = setCity;
window.openCity = openCity;
window.openTour = openTour;
window.closeModal = closeModal;

document.addEventListener("DOMContentLoaded", async () => {
  const deepCity = cityFromLocation();
  if (deepCity && window.NOURA_CITIES.some((city) => city.id === deepCity)) {
    selectedCityId = deepCity;
  }
  await loadPrices();
  renderHero();
  renderBento();
  renderCities();
  renderFilters();
  renderPriceStamp();
  renderTours();
  document.getElementById("city-filter").addEventListener("change", (event) => setCity(event.target.value));
  document.getElementById("modal").addEventListener("click", (event) => {
    if (event.target.id === "modal") closeModal();
  });
  if (deepCity) {
    document.getElementById("tours").scrollIntoView({ behavior: "smooth" });
  }
});
