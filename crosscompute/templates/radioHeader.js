async function refreshRadio(elementId, dataUri) {
  let d;
  try {
    const r = await fetch(dataUri + '.json');
    d = await r.json();
  } catch {
    return;
  }
  const l = document.getElementById(elementId), i = l.dataset.variable, hs = [], { options } = d.configuration, value = d.value;
  for (let j = 0; j < options.length; j++) {
    const o = options[j], v = o.value, n = o.name || v, x = v == value ? ' checked' : '';
    hs.push(`<div><input type="radio" id="${i}-${j}" name="${i}" value="${v}"${x}> <label for="${i}-${j}">${n}</label></div>`);
  }
  l.innerHTML = hs.join('\n');
}
