// ===================== live layer 38: who checked your prescription =====================
// A named, registered pharmacist now signs off every prescription order before it is packed. The family
// should be told who that was. A pharmacy registration number is a public professional credential, and
// showing it is most of what separates a pharmacy from a website that posts medicines through a letterbox.
{
const P = SX.p, E = SX.E || (s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
const St = () => SX.S || {};

SX.addPhrases({
  'Checked by': ['जाँच की', 'తనిఖీ చేసినవారు'],
  'Pharmacist': ['फार्मासिस्ट', 'ఫార్మసిస్ట్'],
  'Reg': ['रजि', 'రిజి'],
});

function line(o) {
  const c = o.checkedBy;
  if (!c) return '';
  const who = `${P('Checked by')} ${E(c.name)}`;
  const reg = c.regNo ? ` · ${P('Pharmacist')} ${E(c.regNo)}` : ` · ${P('Pharmacist')}`;
  return `<small class="lv38">✓ ${who}${reg}</small>`;
}

SX.extend('orders', {
  mounted() {
    const orders = (St().liveOrders || []).filter(o => o.kind === 'medicine' && o.checkedBy);
    if (!orders.length) return;
    const rows = [...document.querySelectorAll('.sx-lo')];
    orders.forEach(o => {
      // Same way layer 10 finds a row: the order id is printed in its <small>. There is no data attribute
      // on these rows and adding one would mean editing the main renderer from a layer, which is how the
      // two get out of step.
      const row = rows.find(el => el.textContent.includes(o.id));
      if (!row || row.querySelector('.lv38')) return;
      const head = row.querySelector('.sx-lo1');
      if (head) head.insertAdjacentHTML('afterend', line(o));
    });
  }
});
}
