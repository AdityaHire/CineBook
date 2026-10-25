/**
 * static/js/countdown.js
 * 5-minute hold countdown timer with server time drift correction and hold release
 */

document.addEventListener('DOMContentLoaded', () => {
  const timerBadge = document.getElementById('hold-timer-badge');
  const timerDisplay = document.getElementById('hold-timer-display');
  const payBtn = document.getElementById('pay-button');
  const changeSeatsBtn = document.getElementById('change-seats-btn');
  const expiredAlert = document.getElementById('hold-expired-alert');

  if (!timerDisplay) return;

  const expiresAtStr = timerDisplay.dataset.expiresAt;
  const serverTimeStr = timerDisplay.dataset.serverTime;
  const showId = timerDisplay.dataset.showId;

  if (!expiresAtStr) return;

  const expiryTime = new Date(expiresAtStr).getTime();
  const serverTime = serverTimeStr ? new Date(serverTimeStr).getTime() : Date.now();
  const clientOffset = serverTime - Date.now();

  function updateTimer() {
    const adjustedNow = Date.now() + clientOffset;
    const diffMs = expiryTime - adjustedNow;

    if (diffMs <= 0) {
      // Hold has expired
      timerDisplay.textContent = '00:00';
      if (timerBadge) {
        timerBadge.classList.add('urgent');
      }
      if (payBtn) {
        payBtn.disabled = true;
      }
      if (expiredAlert) {
        expiredAlert.style.display = 'block';
      }
      clearInterval(timerInterval);
      return;
    }

    const totalSeconds = Math.floor(diffMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    const formatted = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    timerDisplay.textContent = formatted;

    // Turn red/amber under 60 seconds
    if (totalSeconds <= 60) {
      if (timerBadge) {
        timerBadge.classList.add('urgent');
      }
    }
  }

  const timerInterval = setInterval(updateTimer, 1000);
  updateTimer();

  // Change seats handler - release holds before leaving
  if (changeSeatsBtn) {
    changeSeatsBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        await api(`/api/shows/${showId}/holds/`, { method: 'DELETE' });
      } catch (err) {
        console.warn('Could not release hold:', err);
      }
      window.location.href = `/shows/${showId}/seats/`;
    });
  }
});
