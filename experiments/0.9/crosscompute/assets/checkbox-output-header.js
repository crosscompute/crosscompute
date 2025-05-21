async function refreshCheckbox(elementId, dataUri, dataValue, dataConfiguration) {
  const x = dataValue, options = dataConfiguration?.['options'], l = document.getElementById(elementId), vs = x !== undefined ? x.split('\n') : [];
  if (options !== undefined) {
    const hs = [], i = l.dataset.variable;
    for (let j = 0; j < options.length; j++) {
      const o = options[j], v = o.value, n = o.name || v, w = vs.includes(v) ? ' checked' : '';
      hs.push(`<div><input type="checkbox" id="${i}-${j}" name="${i}" value="${v}"${w}> <label for="${i}-${j}">${n}</label></div>`);
    }
    l.innerHTML = hs.join('\n');
  } else if (vs.length) {
    for (const g of l.querySelectorAll('input')) {
      g.checked = vs.includes(g.value);
    }
  }
}
