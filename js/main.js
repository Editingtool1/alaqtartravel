document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav');
  const tripRadios = document.querySelectorAll('input[name="trip"]');
  const returnField = document.querySelector('.return-field');
  const year = document.getElementById('year');

  if (year) year.textContent = new Date().getFullYear();

  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
      toggle.textContent = open ? '✕' : '☰';
    });
    nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
      nav.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.textContent = '☰';
    }));
  }

  tripRadios.forEach(radio => radio.addEventListener('change', () => {
    const oneWay = document.querySelector('input[name="trip"]:checked')?.value === 'oneway';
    if (returnField) returnField.style.display = oneWay ? 'none' : 'flex';
  }));
});
