// Display-only panel placement. Never modifies coordinates or entity identity.
function makePanelLayout(entities, comparison, width, height) {
  const groups = new Map();
  entities.forEach((entity, index) => {
    const supplied = entity.comparison_slot;
    const key = !comparison ? 'overlay' : Number.isInteger(supplied) && supplied >= 0 ? 'slot:' + supplied : 'entity:' + index;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(entity);
  });
  if (!groups.size) groups.set('empty', []);
  const columns = comparison && groups.size > 1 ? 2 : 1;
  const rows = Math.ceil(groups.size / columns), byRef = new Map();
  const panels = [...groups.values()].map((items, index) => {
    const panel = {x: index % columns * width / columns, y: Math.floor(index / columns) * height / rows,
      w: width / columns, h: height / rows, items, title: comparison ? items.map(e => e.display_name).join(' + ') : ''};
    items.forEach(e => byRef.set(e.entity_ref, panel));
    return panel;
  });
  return {panels, byRef, rows, columns};
}
