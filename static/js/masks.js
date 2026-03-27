function applyPhoneMask(value) {
  value = value.replace(/\D/g, '').slice(0, 11);
  if (value.length <= 10) {
    return value.replace(/(\d{0,2})(\d{0,4})(\d{0,4})/, function(_, a, b, c) {
      let out = '';
      if (a) out += '(' + a;
      if (a.length === 2) out += ') ';
      if (b) out += b;
      if (c) out += '-' + c;
      return out;
    });
  }
  return value.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
}

function applyDocMask(value) {
  value = value.replace(/\D/g, '').slice(0, 14);
  if (value.length <= 11) {
    return value.replace(/(\d{3})(\d{3})(\d{3})(\d{0,2})/, function(_, a, b, c, d) {
      let out = a;
      if (b) out += '.' + b;
      if (c) out += '.' + c;
      if (d) out += '-' + d;
      return out;
    });
  }
  return value.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{0,2})/, function(_, a, b, c, d, e) {
    let out = a;
    if (b) out += '.' + b;
    if (c) out += '.' + c;
    if (d) out += '/' + d;
    if (e) out += '-' + e;
    return out;
  });
}

document.addEventListener('input', function(e) {
  if (e.target.classList.contains('mask-phone')) {
    e.target.value = applyPhoneMask(e.target.value);
  }
  if (e.target.classList.contains('mask-doc')) {
    e.target.value = applyDocMask(e.target.value);
  }
  if (e.target.classList.contains('mask-card-number')) {
    e.target.value = applyCardNumberMask(e.target.value);
  }
  if (e.target.classList.contains('mask-card-expiration')) {
    e.target.value = applyCardExpirationMask(e.target.value);
  }
  if (e.target.classList.contains('mask-card-cvv')) {
    e.target.value = applyCardCvvMask(e.target.value);
  }
});


function applyCardNumberMask(value) {
  value = value.replace(/\D/g, '').slice(0, 16);
  return value.replace(/(\d{4})(?=\d)/g, '$1 ').trim();
}

function applyCardExpirationMask(value) {
  value = value.replace(/\D/g, '').slice(0, 4);
  if (value.length <= 2) return value;
  return value.slice(0, 2) + '/' + value.slice(2);
}

function applyCardCvvMask(value) {
  return value.replace(/\D/g, '').slice(0, 4);
}
