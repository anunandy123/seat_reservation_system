const grid = document.querySelector('#seat-grid');
const selectedList = document.querySelector('#selected-list');
const count = document.querySelector('#selected-count');
const reserveButton = document.querySelector('#reserve-button');
const checkoutButton = document.querySelector('#checkout-button');
const feedback = document.querySelector('#feedback');
const syncStatus = document.querySelector('#sync-status');
const timer = document.querySelector('#timer');
let selected = new Set();
let token = null;
let expiresAt = null;

function csrfToken() { return document.cookie.split('; ').find((row) => row.startsWith('csrftoken='))?.split('=')[1]; }
function renderSelection() { count.textContent = selected.size; selectedList.replaceChildren(...[...selected].map((label) => { const pill = document.createElement('span'); pill.className = 'pill'; pill.textContent = label; return pill; })); reserveButton.disabled = !selected.size || token; }
function renderSeats(seats) { grid.innerHTML = ''; seats.forEach((seat) => { const button = document.createElement('button'); button.dataset.id = seat.id; button.className = `seat ${seat.state} ${selected.has(seat.label) ? 'selected' : ''}`; button.textContent = seat.label; button.disabled = seat.state !== 'available' && !selected.has(seat.label); button.onclick = () => { selected.has(seat.label) ? selected.delete(seat.label) : selected.add(seat.label); renderSelection(); renderSeats(seats); }; grid.appendChild(button); }); }
async function refresh() { const response = await fetch('/api/availability/'); const data = await response.json(); if (!token) renderSeats(data.seats); syncStatus.textContent = `Updated ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`; }
reserveButton.onclick = async () => { feedback.textContent = ''; const ids = [...selected].map((label) => [...document.querySelectorAll('.seat')].find((button) => button.textContent === label)?.dataset.id).filter(Boolean); const response = await fetch('/api/reservation/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify({ seat_ids: ids }) }); const data = await response.json(); if (!response.ok) { feedback.textContent = data.error; selected.clear(); renderSelection(); refresh(); return; } token = data.token; expiresAt = new Date(data.expires_at); timer.hidden = false; checkoutButton.hidden = false; reserveButton.hidden = true; feedback.textContent = 'Seats held. Complete booking before the timer ends.'; startTimer(); };
checkoutButton.onclick = async () => { const response = await fetch('/api/reservation/checkout/', { method: 'POST', headers: { 'X-Reservation-Token': token, 'X-CSRFToken': csrfToken() } }); const data = await response.json(); feedback.textContent = response.ok ? 'Booking confirmed.' : data.error; if (response.ok || response.status === 409) { token = null; selected.clear(); checkoutButton.hidden = true; timer.hidden = true; reserveButton.hidden = false; renderSelection(); refresh(); } };
function startTimer() { const tick = () => { const seconds = Math.max(0, Math.floor((expiresAt - new Date()) / 1000)); timer.querySelector('strong').textContent = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`; if (seconds) setTimeout(tick, 1000); else { token = null; selected.clear(); timer.hidden = true; checkoutButton.hidden = true; reserveButton.hidden = false; feedback.textContent = 'Your hold expired. Select seats again.'; renderSelection(); refresh(); } }; tick(); }
refresh(); setInterval(refresh, 5000); renderSelection();