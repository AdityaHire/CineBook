/**
 * static/js/cancel.js
 * Handles customer booking cancellation dialog and API calls.
 */

document.addEventListener('DOMContentLoaded', () => {
  const cancelButtons = document.querySelectorAll('.btn-cancel-booking');
  if (!cancelButtons.length) return;

  cancelButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const ref = btn.dataset.reference;
      const amount = btn.dataset.amount || '0.00';

      const confirmed = window.confirm(
        `Cancel booking ${ref}?\n\nRs ${amount} will be refunded (simulated). This cannot be undone.`
      );

      if (!confirmed) return;

      btn.disabled = true;
      const originalText = btn.innerHTML;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Cancelling…';

      try {
        await api(`/api/bookings/${ref}/cancel/`, { method: 'POST' });
        // Reload page to display updated cancelled state and updated tab counts
        window.location.reload();
      } catch (err) {
        btn.disabled = false;
        btn.innerHTML = originalText;
        alert(err.message || 'Could not cancel booking. Please try again.');
      }
    });
  });
});
