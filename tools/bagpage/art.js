function mix(h,t,a){const p=x=>parseInt(x,16);const c=[p(h.slice(1,3)),p(h.slice(3,5)),p(h.slice(5,7))],d=t==="w"?[255,255,255]:[0,0,0];return "#"+c.map((v,i)=>Math.round(v+(d[i]-v)*a).toString(16).padStart(2,"0")).join("")}
let UID=0;

/* ---------------- product art (SVG, shaded) ---------------- */
function art(kind,col){
  const u="a"+(++UID),L=mix(col,"w",.5),D=mix(col,"b",.1),DD=mix(col,"b",.22);
  const g=`<defs><linearGradient id="${u}" x1="0" y1="0" x2=".9" y2="1"><stop offset="0" stop-color="${L}"/><stop offset=".55" stop-color="${col}"/><stop offset="1" stop-color="${D}"/></linearGradient><radialGradient id="${u}h" cx=".3" cy=".2" r=".7"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>`;
  const F=`url(#${u})`,H=`url(#${u}h)`;
  const sh=`<ellipse cx="60" cy="113" rx="34" ry="4.5" fill="#000" opacity=".09"/>`;
  const K={
  dress:`<path d="M44 12h32l6 14 14 8-8 16-8-4 6 64H34l6-64-8 4-8-16 14-8z" fill="${F}"/><path d="M44 12h32l6 14 14 8-8 16-8-4 6 64H34l6-64-8 4-8-16 14-8z" fill="${H}"/><path d="M48 12c2 9 22 9 24 0" fill="none" stroke="#fff" stroke-width="2.6" opacity=".85"/><path d="M60 22v86" stroke="${D}" stroke-width="1.6" opacity=".5"/>${[34,47,60,73].map(y=>`<circle cx="60" cy="${y}" r="2.6" fill="#fff"/>`).join("")}<path d="M38 58c8 3 36 3 44 0" stroke="${DD}" stroke-width="1.4" opacity=".35" fill="none"/>`,
  pack:`<rect x="22" y="16" width="76" height="92" rx="15" fill="${F}"/><rect x="22" y="16" width="76" height="92" rx="15" fill="${H}"/><path d="M28 30h64" stroke="${DD}" stroke-width="2" opacity=".25"/><rect x="32" y="48" width="56" height="38" rx="11" fill="#fff" opacity=".95"/><rect x="40" y="58" width="40" height="4" rx="2" fill="${DD}" opacity=".45"/><rect x="40" y="67" width="26" height="4" rx="2" fill="${DD}" opacity=".25"/><rect x="28" y="22" width="9" height="80" rx="4.5" fill="#fff" opacity=".28"/>`,
  fold:`<rect x="14" y="72" width="92" height="26" rx="11" fill="${D}"/><rect x="18" y="50" width="88" height="27" rx="11" fill="${F}"/><rect x="22" y="28" width="84" height="27" rx="11" fill="${F}"/><rect x="22" y="28" width="84" height="27" rx="11" fill="${H}"/><path d="M22 41h84M18 63h88" stroke="${DD}" stroke-width="1.2" opacity=".18"/>`,
  vest:`<path d="M40 16c6 9 34 9 40 0l17 13-8 15-9-4v64H40V40l-9 4-8-15z" fill="${F}"/><path d="M40 16c6 9 34 9 40 0l17 13-8 15-9-4v64H40V40l-9 4-8-15z" fill="${H}"/><path d="M50 28c7 15 7 32 0 48" fill="none" stroke="#fff" stroke-width="2.6"/><path d="M50 52l11 4M50 52l10-7" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/><path d="M40 98h40" stroke="#fff" stroke-width="2" opacity=".6"/>`,
  bottle:`<path d="M64 20l13-17" stroke="#2C2C2E" stroke-width="3.2" stroke-linecap="round"/><rect x="44" y="14" width="32" height="22" rx="8" fill="#2C2C2E"/><rect x="47" y="17" width="8" height="15" rx="4" fill="#fff" opacity=".18"/><rect x="37" y="32" width="46" height="80" rx="18" fill="${F}"/><rect x="37" y="32" width="46" height="80" rx="18" fill="${H}"/><rect x="44" y="44" width="8" height="58" rx="4" fill="#fff" opacity=".5"/><rect x="37" y="66" width="46" height="13" fill="#fff" opacity=".3"/>`,
  pouch:`<path d="M15 46q0-13 13-13h64q13 0 13 13v46q0 17-17 17H32q-17 0-17-17z" fill="${F}"/><path d="M15 46q0-13 13-13h64q13 0 13 13v46q0 17-17 17H32q-17 0-17-17z" fill="${H}"/><path d="M17 47h86" stroke="${DD}" stroke-opacity=".45" stroke-width="3" stroke-dasharray="3 3"/><rect x="84" y="40" width="9" height="20" rx="4.5" fill="#2C2C2E"/><rect x="24" y="56" width="10" height="44" rx="5" fill="#fff" opacity=".32"/>`,
  power:`<path d="M30 80c-22 11-16 31 6 28s24 6 38 2" fill="none" stroke="${col}" stroke-width="4.5" stroke-linecap="round"/><rect x="38" y="12" width="50" height="86" rx="15" fill="#2C2C2E"/><rect x="38" y="12" width="50" height="86" rx="15" fill="url(#${u}h)" opacity=".5"/><rect x="44" y="20" width="6" height="68" rx="3" fill="#fff" opacity=".14"/>${[0,1,2,3].map(i=>`<circle cx="${52+i*8}" cy="82" r="2.8" fill="${col}" opacity="${1-i*.22}"/>`).join("")}`,
  folder:`<path d="M17 30q0-9 9-9h24l8 9h36q9 0 9 9v61q0 9-9 9H26q-9 0-9-9z" fill="${F}"/><path d="M17 30q0-9 9-9h24l8 9h36q9 0 9 9v61q0 9-9 9H26q-9 0-9-9z" fill="${H}"/><rect x="29" y="40" width="56" height="42" rx="8" fill="#fff"/><rect x="35" y="47" width="15" height="15" rx="2.5" fill="#1D1D1F"/><rect x="38.5" y="50.5" width="8" height="8" fill="#fff"/><rect x="41" y="53" width="3" height="3" fill="#1D1D1F"/><rect x="56" y="48" width="23" height="4" rx="2" fill="#1D1D1F" opacity=".55"/><rect x="56" y="56" width="16" height="4" rx="2" fill="#1D1D1F" opacity=".3"/><rect x="35" y="70" width="44" height="4" rx="2" fill="#C8385F" opacity=".7"/><path d="M17 76h86v24q0 9-9 9H26q-9 0-9-9z" fill="${D}" opacity=".9"/>`,
  roll:`<rect x="10" y="40" width="94" height="58" rx="29" fill="${F}"/><circle cx="76" cy="69" r="29" fill="${L}"/><path d="M76 69m-4 0a4 4 0 1 1 8 0a10 10 0 1 1-18-4a16 16 0 1 1 27 14" fill="none" stroke="${D}" stroke-width="3" stroke-linecap="round" opacity=".8"/><rect x="24" y="48" width="36" height="7" rx="3.5" fill="#fff" opacity=".4"/>`
  };
  return `<svg class="art" viewBox="0 0 120 120" role="img" aria-hidden="true" style="overflow:visible">${g}${sh}${K[kind]}</svg>`;
}

/* hospital bag (peeks show what was added last) */
function bagSVG(){
  const u="bg"+(++UID);
  const pk=S.recent.slice(-3).map(id=>ITEMS.find(i=>i.id===id)).filter(Boolean);
  const spots=[[70,34,-10],[146,20,3],[214,32,12]];
  const peeks=pk.map((it,i)=>{const[x,y,r]=spots[i];return `<g transform="translate(${x} ${y}) rotate(${r} 35 40) scale(.6)">${art(it.kind,it.col).replace(/<svg[^>]*>|<\/svg>/g,"")}</g>`}).join("");
  return `<svg viewBox="0 0 340 300" width="100%" height="100%" role="img" aria-label="Your hospital bag" style="overflow:visible">
  <defs>
   <linearGradient id="${u}a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FBF9F6"/><stop offset="1" stop-color="#ECE7E0"/></linearGradient>
   <linearGradient id="${u}b" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".07"/><stop offset=".22" stop-color="#000" stop-opacity="0"/><stop offset=".8" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".09"/></linearGradient>
   <radialGradient id="${u}s" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#000" stop-opacity=".18"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
  </defs>
  <ellipse cx="170" cy="290" rx="150" ry="12" fill="url(#${u}s)"/>
  <path d="M106 98 C106 26 234 26 234 98" fill="none" stroke="#2B2B2D" stroke-width="11" stroke-linecap="round"/>
  ${peeks}
  <path d="M40 96 H300 L288 264 Q285 286 260 286 H80 Q55 286 52 264 Z" fill="url(#${u}a)"/>
  <path d="M40 96 H300 L288 264 Q285 286 260 286 H80 Q55 286 52 264 Z" fill="url(#${u}b)"/>
  <path d="M40 96 H300 L298 116 H42 Z" fill="#E4DED5"/>
  <path d="M50 124 H290" stroke="#000" stroke-opacity=".06" stroke-width="1.5" stroke-dasharray="4 5"/>
  <rect x="134" y="176" width="72" height="28" rx="6" fill="#C8385F"/>
  <text x="170" y="194.5" text-anchor="middle" font-family="-apple-system,Inter,sans-serif" font-size="7.6" font-weight="600" letter-spacing="1" fill="#fff">URBAN HEALTH</text>
  </svg>`;
}
