async function refreshRadio(elementId, dataUri, dataValue, dataConfiguration) {
  const x = dataValue, options = dataConfiguration?.['options'], l = document.getElementById(elementId);
  if (options !== undefined) {
    const hs = [], i = l.dataset.variable;
    for (let j = 0; j < options.length; j++) {
      const o = options[j], v = o.value, n = o.name || v, w = v == x ? ' checked' : '';
      hs.push(`<div><input type="radio" id="${i}-${j}" name="${i}" value="${v}"${w}> <label for="${i}-${j}">${n}</label></div>`);
    }
    l.innerHTML = hs.join('\n');
  } else if (x !== undefined) {
    l.querySelector(`input[value="${x}"]`).checked = true;
  }
}
