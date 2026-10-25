/**
 * static/js/pay.js
 * Handles checkout payment simulation, idempotency key generation, and booking confirmation.
 */

document.addEventListener('DOMContentLoaded', () => {
  const payBtn = document.getElementById('pay-button');
  const timerDisplay = document.getElementById('hold-timer-display');
  const summaryCard = document.getElementById('booking-summary-card');

  if (!payBtn || !timerDisplay) return;

  const showId = timerDisplay.dataset.showId;

  // Generate or retrieve idempotency key for this show checkout session
  const storageKey = `cenebook_idempotency_${showId}`;
  let idempotencyKey = sessionStorage.getItem(storageKey);
  if (!idempotencyKey) {
    idempotencyKey = (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : 'cnb-idemp-' + Date.now() + '-' + Math.random().toString(36).substring(2, 10);
    sessionStorage.setItem(storageKey, idempotencyKey);
  }

  let isPaying = false;

  function showSummaryAlert(message, type = 'danger') {
    let alertEl = document.getElementById('pay-alert-banner');
    if (!alertEl) {
      alertEl = document.createElement('div');
      alertEl.id = 'pay-alert-banner';
      summaryCard.parentNode.insertBefore(alertEl, summaryCard);
    }
    alertEl.innerHTML = `
      <div class="cb-alert cb-alert-${type} mb-4" role="alert">
        <i class="bi bi-exclamation-circle-fill"></i>
        <div>${message}</div>
      </div>
    `;
    alertEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  payBtn.addEventListener('click', async () => {
    if (isPaying) return;

    isPaying = true;
    payBtn.disabled = true;
    const originalText = payBtn.innerHTML;
    payBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Processing payment…';

    try {
      const res = await api(`/api/shows/${showId}/bookings/`, {
        method: 'POST',
        body: { idempotency_key: idempotencyKey },
      });

      // Clear idempotency key on success
      sessionStorage.removeItem(storageKey);

      // Navigate to confirmation page
      window.location.href = res.confirmation_url || `/bookings/${res.booking_reference}/confirmation/`;

    } catch (err) {
      isPaying = false;
      payBtn.disabled = false;
      payBtn.innerHTML = originalText;

      if (err.code === 'PAYMENT_FAILED') {
        showSummaryAlert('Payment failed. Your seats are still held. Please try again.', 'danger');
      } else if (err.code === 'HOLD_EXPIRED') {
        showSummaryAlert('Your seat hold has expired. <a href="/shows/' + showId + '/seats/" class="alert-link">Select seats again</a>.', 'danger');
        payBtn.disabled = true;
      } else if (err.code === 'SEAT_UNAVAILABLE') {
        showSummaryAlert('One or more seats are no longer available. <a href="/shows/' + showId + '/seats/" class="alert-link">Pick other seats</a>.', 'danger');
        payBtn.disabled = true;
      } else {
        showSummaryAlert(err.message || 'Connection problem. Please check My Bookings before retrying.', 'danger');
      }
    }
  });
});
