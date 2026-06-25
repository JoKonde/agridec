/**
 * AgriDec — Géolocalisation HTML5
 * Remplit automatiquement latitude / longitude dans le formulaire culture.
 */
(function () {
  'use strict';

  const latInput = document.getElementById('id_latitude');
  const lonInput = document.getElementById('id_longitude');
  const statusEl = document.getElementById('gps-status');
  const statusText = document.getElementById('gps-status-text');
  const coordsEl = document.getElementById('gps-coords');
  const latDisplay = document.getElementById('gps-lat-display');
  const lonDisplay = document.getElementById('gps-lon-display');
  const submitBtn = document.getElementById('submit-btn');

  if (!latInput || !lonInput) return;

  function setStatus(type, message) {
    if (!statusEl || !statusText) return;
    statusEl.className = 'gps-status gps-status--' + type;
    statusText.textContent = message;
    const spinner = statusEl.querySelector('.gps-spinner');
    if (spinner) {
      spinner.hidden = type !== 'loading';
    }
  }

  function enableSubmit() {
    if (submitBtn) submitBtn.disabled = false;
  }

  function disableSubmit() {
    if (submitBtn) submitBtn.disabled = true;
  }

  function showCoords(lat, lon) {
    if (coordsEl) coordsEl.hidden = false;
    if (latDisplay) latDisplay.textContent = lat.toFixed(6);
    if (lonDisplay) lonDisplay.textContent = lon.toFixed(6);
  }

  function onSuccess(position) {
    const lat = position.coords.latitude;
    const lon = position.coords.longitude;
    latInput.value = lat.toFixed(6);
    lonInput.value = lon.toFixed(6);
    setStatus('success', 'Localisation détectée ✓');
    showCoords(lat, lon);
    enableSubmit();
  }

  function onError(error) {
    let message = 'Impossible d\'obtenir votre position.';

    switch (error.code) {
      case error.PERMISSION_DENIED:
        message = 'Accès à la localisation refusé. Autorisez le GPS dans votre navigateur.';
        break;
      case error.POSITION_UNAVAILABLE:
        message = 'Position indisponible. Vérifiez que le GPS est activé.';
        break;
      case error.TIMEOUT:
        message = 'Délai dépassé. Réessayez ou vérifiez votre connexion.';
        break;
    }

    setStatus('error', message);
    disableSubmit();
  }

  // Si les champs sont déjà remplis (erreur de validation serveur), réactiver le bouton
  if (latInput.value && lonInput.value) {
    const lat = parseFloat(latInput.value);
    const lon = parseFloat(lonInput.value);
    setStatus('success', 'Localisation détectée ✓');
    showCoords(lat, lon);
    enableSubmit();
    return;
  }

  if (!navigator.geolocation) {
    setStatus('error', 'Votre navigateur ne supporte pas la géolocalisation.');
    disableSubmit();
    return;
  }

  disableSubmit();
  navigator.geolocation.getCurrentPosition(onSuccess, onError, {
    enableHighAccuracy: true,
    timeout: 15000,
    maximumAge: 0,
  });
})();
