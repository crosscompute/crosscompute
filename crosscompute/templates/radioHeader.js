async function refreshRadio(elementId, dataUri) {
  const r = await fetch(dataUri + '.json'), { status } = r;
  if (status != 200) {
    throw { status };
  }
  const d = await r.json(), hs = [], { options } = d.configuration, value = d.value;
  const e = document.getElementById(elementId), i = e.dataset.variable;
  for (let j = 0; j < options.length; j++) {
    const option = options[j], v = option.value, n = option.name || v, x = v == value ? ' checked' : '';
    hs.push(`<div><input type="radio" id="${i}-${j}" name="${i}" value="${v}"${x}> <label for="${i}-${j}">${n}</label></div>`);
  }
  e.innerHTML = hs.join('\n');
  return e;
}
