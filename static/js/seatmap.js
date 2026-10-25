/**
 * static/js/seatmap.js
 * Interactive seat selection map with pan/zoom, instant feedback,
 * 8-seat limit, conflict detection, keyboard navigation, and atomic holds.
 */

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('seat-map-container');
  if (!container) return;

  const showId = parseInt(container.dataset.showId, 10);
  const ticketPrice = parseFloat(container.dataset.ticketPrice);
  const maxSeats = parseInt(container.dataset.maxSeats, 10) || 8;

  const canvas = document.getElementById('seat-map-canvas');
  const scrollArea = document.getElementById('seat-map-scroll-area');
  const selectedListEl = document.getElementById('selected-seats-list');
  const selectedCountEl = document.getElementById('selected-seats-count');
  const totalPriceEl = document.getElementById('total-price-display');
  const selectionSheet = document.getElementById('selection-sheet');
  const continueBtn = document.getElementById('continue-to-summary-btn');
  const alertContainer = document.getElementById('seat-map-alert');
  const zoomInBtn = document.getElementById('zoom-in-btn');
  const zoomOutBtn = document.getElementById('zoom-out-btn');
  const zoomResetBtn = document.getElementById('zoom-reset-btn');

  // Selected seats: Map(seat_id => { label, row, number })
  const selectedSeats = new Map();

  // Cache seat elements: Map(seat_id => { targetEl, boxEl, data })
  const seatElements = new Map();

  let zoomLevel = 1.0;
  let isSubmitting = false;
  let refreshTimer = null;

  // ── Show notification message ──────────────────────────────────────────────
  function showBanner(message, type = 'danger') {
    if (!alertContainer) return;
    alertContainer.innerHTML = `
      <div class="cb-alert cb-alert-${type} mb-3" role="alert">
        <i class="bi bi-exclamation-triangle-fill"></i>
        <div>${message}</div>
      </div>
    `;
    alertContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function clearBanner() {
    if (alertContainer) alertContainer.innerHTML = '';
  }

  // ── Update Selection UI ────────────────────────────────────────────────────
  function updateSelectionUI() {
    const count = selectedSeats.size;
    const total = (count * ticketPrice).toFixed(2);

    if (selectionSheet) {
      selectionSheet.classList.toggle('is-visible', count > 0);
      selectionSheet.setAttribute('aria-hidden', String(count === 0));
    }

    if (selectedCountEl) {
      selectedCountEl.textContent = `${count} seat${count === 1 ? '' : 's'}`;
    }
    if (totalPriceEl) {
      totalPriceEl.textContent = `Rs ${total}`;
    }

    if (selectedListEl) {
      if (count === 0) {
        selectedListEl.innerHTML = '<span class="text-secondary" style="font-size:0.875rem;">No seats selected</span>';
      } else {
        const sortedLabels = Array.from(selectedSeats.values())
          .sort((a, b) => a.row.localeCompare(b.row) || a.number - b.number)
          .map(s => `<span class="cb-badge cb-badge-accent me-1 mb-1">${s.label}</span>`)
          .join('');
        selectedListEl.innerHTML = sortedLabels;
      }
    }

    if (continueBtn) {
      continueBtn.disabled = count === 0 || isSubmitting;
    }
  }

  // ── Toggle Seat Selection ──────────────────────────────────────────────────
  function toggleSeat(seatId, seatData) {
    if (isSubmitting) return;

    if (selectedSeats.has(seatId)) {
      // Deselect
      selectedSeats.delete(seatId);
      const entry = seatElements.get(seatId);
      if (entry) {
        entry.boxEl.className = 'seat-box available';
        entry.boxEl.textContent = entry.data.number;
        entry.targetEl.setAttribute('aria-checked', 'false');
      }
      clearBanner();
    } else {
      // Check limit
      if (selectedSeats.size >= maxSeats) {
        showBanner(`You can select up to ${maxSeats} seats per booking.`, 'warning');
        return;
      }

      // Select
      selectedSeats.set(seatId, seatData);
      const entry = seatElements.get(seatId);
      if (entry) {
        entry.boxEl.className = 'seat-box selected';
        entry.boxEl.innerHTML = '<i class="bi bi-check-lg"></i>';
        entry.targetEl.setAttribute('aria-checked', 'true');
      }
      clearBanner();
    }

    updateSelectionUI();
  }

  // ── Render Seat Map ────────────────────────────────────────────────────────
  function renderSeatMap(data) {
    canvas.innerHTML = '';
    seatElements.clear();

    const grid = document.createElement('div');
    grid.className = 'seat-grid';
    grid.setAttribute('role', 'grid');
    grid.setAttribute('aria-label', 'Cinema seat map');

    data.rows.forEach(rowGroup => {
      const rowEl = document.createElement('div');
      rowEl.className = 'seat-row';
      rowEl.setAttribute('role', 'row');

      // Row letter label
      const labelEl = document.createElement('div');
      labelEl.className = 'seat-row-label';
      labelEl.textContent = rowGroup.row;
      labelEl.setAttribute('aria-hidden', 'true');
      rowEl.appendChild(labelEl);

      rowGroup.seats.forEach(seat => {
        const targetBtn = document.createElement('button');
        targetBtn.type = 'button';
        targetBtn.className = 'seat-target';
        targetBtn.id = `seat-btn-${seat.seat_id}`;
        targetBtn.setAttribute('role', 'gridcell');
        targetBtn.setAttribute('aria-label', `Seat ${seat.label}, ${seat.status}`);
        targetBtn.dataset.seatId = seat.seat_id;

        const boxEl = document.createElement('div');
        boxEl.className = `seat-box ${seat.status}`;
        boxEl.id = `seat-box-${seat.seat_id}`;

        if (seat.status === 'selected') {
          // Previously held by user
          selectedSeats.set(seat.seat_id, { label: seat.label, row: seat.row, number: seat.number });
          boxEl.innerHTML = '<i class="bi bi-check-lg"></i>';
          targetBtn.setAttribute('aria-checked', 'true');
        } else if (seat.status === 'booked') {
          boxEl.innerHTML = '&times;';
          targetBtn.disabled = true;
          targetBtn.setAttribute('aria-disabled', 'true');
        } else if (seat.status === 'held') {
          boxEl.textContent = '~';
          targetBtn.disabled = true;
          targetBtn.setAttribute('aria-disabled', 'true');
        } else {
          boxEl.textContent = seat.number;
          targetBtn.setAttribute('aria-checked', 'false');
        }

        targetBtn.appendChild(boxEl);

        // Click / Touch listener
        if (seat.status === 'available' || seat.status === 'selected') {
          targetBtn.addEventListener('click', () => {
            toggleSeat(seat.seat_id, { label: seat.label, row: seat.row, number: seat.number });
          });
        }

        rowEl.appendChild(targetBtn);
        seatElements.set(seat.seat_id, { targetEl: targetBtn, boxEl: boxEl, data: seat });
      });

      grid.appendChild(rowEl);
    });

    canvas.appendChild(grid);
    updateSelectionUI();
  }

  // ── Poll and Refresh Map ───────────────────────────────────────────────────
  async function refreshSeatMap() {
    try {
      const data = await api(`/api/shows/${showId}/seats/`);
      if (!data || !data.rows) return;

      const lostSeats = [];

      data.rows.forEach(rowGroup => {
        rowGroup.seats.forEach(seat => {
          const entry = seatElements.get(seat.seat_id);
          if (!entry) return;

          // If user currently has this seat selected in UI
          if (selectedSeats.has(seat.seat_id)) {
            // Check if another user took it
            if (seat.status === 'booked' || (seat.status === 'held' && entry.data.status !== 'selected')) {
              lostSeats.push(seat.label);
              selectedSeats.delete(seat.seat_id);
              entry.boxEl.className = `seat-box ${seat.status} pulse-conflict`;
              entry.targetEl.disabled = true;
            }
          } else {
            // Update visual state if not selected
            if (entry.boxEl.className !== `seat-box ${seat.status}`) {
              entry.boxEl.className = `seat-box ${seat.status}`;
              if (seat.status === 'available') {
                entry.boxEl.textContent = seat.number;
                entry.targetEl.disabled = false;
              } else if (seat.status === 'booked') {
                boxEl.innerHTML = '&times;';
                entry.targetEl.disabled = true;
              } else if (seat.status === 'held') {
                entry.boxEl.textContent = '~';
                entry.targetEl.disabled = true;
              }
            }
          }
          entry.data = seat;
        });
      });

      if (lostSeats.length > 0) {
        showBanner(`Seat ${lostSeats.join(', ')} is no longer available. Please choose another.`, 'danger');
        updateSelectionUI();
      }
    } catch (err) {
      console.warn('Seat map refresh failed:', err);
    }
  }

  // ── Initial Load ───────────────────────────────────────────────────────────
  async function init() {
    try {
      const data = await api(`/api/shows/${showId}/seats/`);
      renderSeatMap(data);

      // Start 10-second polling
      refreshTimer = setInterval(refreshSeatMap, 10000);
    } catch (err) {
      showBanner(err.message || 'Unable to load seat map. Please refresh the page.', 'danger');
    }
  }

  // ── Pan & Zoom ─────────────────────────────────────────────────────────────
  function applyZoom(newZoom) {
    zoomLevel = Math.max(0.7, Math.min(2.0, newZoom));
    canvas.style.transform = `scale(${zoomLevel})`;
  }

  if (zoomInBtn) {
    zoomInBtn.addEventListener('click', () => applyZoom(zoomLevel + 0.15));
  }
  if (zoomOutBtn) {
    zoomOutBtn.addEventListener('click', () => applyZoom(zoomLevel - 0.15));
  }
  if (zoomResetBtn) {
    zoomResetBtn.addEventListener('click', () => applyZoom(1.0));
  }

  // Pointer Events direct manipulation: fluid 1:1 tracking with pointer capture
  let isPanning = false;
  let startX = 0, startY = 0;
  let scrollStartX = 0, scrollStartY = 0;

  scrollArea.addEventListener('pointerdown', (e) => {
    // Only pan if not clicking a seat button
    if (e.target.closest('button')) return;
    isPanning = true;
    startX = e.clientX;
    startY = e.clientY;
    scrollStartX = scrollArea.scrollLeft;
    scrollStartY = scrollArea.scrollTop;
    try {
      scrollArea.setPointerCapture(e.pointerId);
    } catch (_) {}
  });

  scrollArea.addEventListener('pointermove', (e) => {
    if (!isPanning) return;
    e.preventDefault();
    // 1:1 direct manipulation tracking
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    scrollArea.scrollLeft = scrollStartX - dx;
    scrollArea.scrollTop = scrollStartY - dy;
  });

  const stopPanning = (e) => {
    if (!isPanning) return;
    isPanning = false;
    try {
      scrollArea.releasePointerCapture(e.pointerId);
    } catch (_) {}
  };

  scrollArea.addEventListener('pointerup', stopPanning);
  scrollArea.addEventListener('pointercancel', stopPanning);

  // ── Continue to Summary (Place Hold) ───────────────────────────────────────
  if (continueBtn) {
    continueBtn.addEventListener('click', async () => {
      if (selectedSeats.size === 0 || isSubmitting) return;

      const seatIds = Array.from(selectedSeats.keys());
      isSubmitting = true;
      continueBtn.disabled = true;
      const originalText = continueBtn.innerHTML;
      continueBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Holding seats…';

      try {
        await api(`/api/shows/${showId}/holds/`, {
          method: 'POST',
          body: { seat_ids: seatIds },
        });

        // Navigate to summary page
        window.location.href = `/shows/${showId}/summary/`;
      } catch (err) {
        isSubmitting = false;
        continueBtn.disabled = false;
        continueBtn.innerHTML = originalText;

        if (err.code === 'SEAT_UNAVAILABLE') {
          const conflicting = err.details?.seats || [];
          conflicting.forEach(label => {
            // Find and pulse conflicting seats
            for (const [sId, entry] of seatElements.entries()) {
              if (entry.data.label === label) {
                entry.boxEl.classList.add('pulse-conflict');
                selectedSeats.delete(sId);
              }
            }
          });
          showBanner(err.message, 'danger');
          refreshSeatMap();
        } else {
          showBanner(err.message || 'Could not place seat hold. Please try again.', 'danger');
        }
      }
    });
  }

  // Cleanup on unload
  window.addEventListener('beforeunload', () => {
    if (refreshTimer) clearInterval(refreshTimer);
  });

  init();
});
