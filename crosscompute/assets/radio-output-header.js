async function refreshRadio(elementId, dataUri, dataValue, dataConfiguration) {
  const x = dataValue || '', options = dataConfiguration?.['options'] || [], l = document.getElementById(elementId), i = l.dataset.variable, hs = [];
  for (let j = 0; j < options.length; j++) {
    const o = options[j], v = o.value, n = o.name || v, w = v == x ? ' checked' : '';
    hs.push(`<div><input type="radio" id="${i}-${j}" name="${i}" value="${v}"${w}> <label for="${i}-${j}">${n}</label></div>`);
  }
  l.innerHTML = hs.join('\n');
}
