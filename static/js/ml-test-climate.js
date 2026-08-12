/**
 * Curseur climat : saison des pluies (0) ↔ saison sèche (100).
 * Met à jour humidité, pluie, proba pluie, température (+ mois typique aux extrêmes).
 */
(function () {
  'use strict';

  // Profils climatiques (valeurs indicatives type RDC / zone tropicale)
  var PLUIES = {
    humidite: 85,
    pluie_mm: 18,
    probabilite_pluie: 80,
    temperature: 26,
    mois: 11, // novembre — souvent pluvieux autour de Kinshasa
  };

  var SECHE = {
    humidite: 42,
    pluie_mm: 0,
    probabilite_pluie: 5,
    temperature: 30,
    mois: 8, // août — saison sèche typique
  };

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function round1(n) {
    return Math.round(n * 10) / 10;
  }

  function setNumber(id, value, asInt) {
    var el = document.getElementById(id);
    if (!el) return;
    el.value = asInt ? String(Math.round(value)) : String(round1(value));
    // Déclenche input pour que d'autres scripts éventuels réagissent
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function setSelectMois(mois) {
    var el = document.getElementById('id_mois');
    if (!el) return;
    el.value = String(mois);
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function seasonLabel(t) {
    if (t <= 0.2) return 'Saison des pluies';
    if (t >= 0.8) return 'Saison sèche';
    if (t < 0.45) return 'Transition (encore humide)';
    if (t > 0.55) return 'Transition (vers le sec)';
    return 'Intermédiaire';
  }

  function applyClimate(t) {
    // t = 0 pluies → 1 sèche
    setNumber('id_humidite', lerp(PLUIES.humidite, SECHE.humidite, t), true);
    setNumber('id_pluie_mm', lerp(PLUIES.pluie_mm, SECHE.pluie_mm, t), false);
    setNumber('id_probabilite_pluie', lerp(PLUIES.probabilite_pluie, SECHE.probabilite_pluie, t), true);
    setNumber('id_temperature', lerp(PLUIES.temperature, SECHE.temperature, t), false);

    // Aux extrêmes, aligne aussi le mois (le ML s'appuie beaucoup sur le mois)
    if (t <= 0.15) {
      setSelectMois(PLUIES.mois);
    } else if (t >= 0.85) {
      setSelectMois(SECHE.mois);
    }

    var label = document.getElementById('ml-season-label');
    var pct = document.getElementById('ml-season-pct');
    if (label) label.textContent = seasonLabel(t);
    if (pct) pct.textContent = Math.round(t * 100) + ' % vers le sec';
  }

  function init() {
    var slider = document.getElementById('ml-climate-slider');
    if (!slider) return;

    function onSlide() {
      var t = Number(slider.value) / 100;
      applyClimate(t);
    }

    slider.addEventListener('input', onSlide);
    slider.addEventListener('change', onSlide);

    // Applique une fois au chargement selon la position du curseur
    onSlide();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
