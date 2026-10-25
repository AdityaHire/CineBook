/**
 * static/js/api.js
 * Cenebook API communication client
 */

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[2]) : null;
}

async function api(url, { method = 'GET', body = null } = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  if (method !== 'GET' && method !== 'HEAD') {
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
  }

  const options = {
    method,
    headers,
    credentials: 'same-origin',
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type') || '';
  let data = null;
  if (contentType.includes('application/json')) {
    data = await response.json().catch(() => null);
  }

  if (!response.ok) {
    const err = new Error(data?.error?.message || `Request failed with status ${response.status}`);
    err.status = response.status;
    err.code = data?.error?.code || 'REQUEST_FAILED';
    err.details = data?.error?.details || null;
    throw err;
  }

  return data;
}
