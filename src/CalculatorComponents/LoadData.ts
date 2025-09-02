async function loadData() {
  const dealerData = await fetch('/data/dealer.json').then(res => res.json());
  const standData = await fetch('/data/stand.json').then(res => res.json());
  const hitData = await fetch('/data/hit.json').then(res => res.json());
  const doubleData = await fetch('/data/double.json').then(res => res.json());
  const splitData = await fetch('/data/split.json').then(res => res.json());

  return { dealerData, standData, hitData, doubleData, splitData };
}

export default loadData;
