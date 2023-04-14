async function refreshCheckbox(elementId, dataUri) {
  let d;
  try {
    const r = await fetch(dataUri + '.json');
    d = await r.json();
  } catch {
    return;
  }
  const l = document.getElementById(elementId), i = l.dataset.variable, hs = [], { options } = d.configuration, vs = d.value.split('\n');
  for (let j = 0; j < options.length; j++) {
    const option = options[j], v = option.value, n = option.name || v, x = vs.includes(v) ? ' checked' : '';
    hs.push(`<div><input type="checkbox" id="${i}-${j}" name="${i}" value="${v}"${x}> <label for="${i}-${j}">${n}</label></div>`);
  }
  l.innerHTML = hs.join('\n');
}
