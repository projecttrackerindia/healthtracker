// ===================== live layer 20: mobile codes through Firebase Phone Authentication on the in-app sign-in =====================
{
const loadAuthJs=()=>window.THT&&THT.phone?Promise.resolve():new Promise((res,rej)=>{const sc=document.createElement('script');sc.src='/s/auth.js?v=20';sc.onload=res;sc.onerror=rej;document.head.append(sc)});
// a start answer that says {firebase:true, phone} means Google sends the SMS: arm it before the code screen opens
SX.fbArm=async r=>{if(r&&r.firebase&&r.phone){await loadAuthJs();await THT.phone.send(r.phone)}return r};
// the verify body: our 6-digit code, or the Firebase ID token that stands in for it
SX.fbBody=async(flow,code)=>({flow,code,firebaseToken:(window.THT&&THT.phone&&THT.phone.pending())?await THT.phone.token(code):undefined});
}
