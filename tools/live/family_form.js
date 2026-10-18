function memberForm(m){const nw=!m;m=m||{name:'',rel:'Other',age:'',sex:'',w:'',h:'',dob:'',ph:''};const mid=nw?{}:SX.midOf(m.id),tm=SX.today(),BL=['A+','A-','B+','B-','AB+','AB-','O+','O-'];
 return `<div class="card wide lv2-mf"><div class="hd"><h3>${nw?'Add a family member':'Edit '+E(m.name)}</h3>${nw?'':`<button class="btn s sm" data-sx="fedit:">Cancel</button>`}</div>
 <form class="form" data-sxf="fsave:${nw?'':m.id}" novalidate><label class="full">Full name<input name="name" required maxlength="60" value="${E(m.name)}" autocomplete="off"></label>
 <label>Relation to you<select name="rel">${RELS.filter(r=>r!=='You'||m.rel==='You').map(r=>`<option ${m.rel===r?'selected':''}>${r}</option>`).join('')}</select></label>
 <label>Date of birth<input name="dob" type="date" required max="${tm}" min="1900-01-01" value="${E(m.dob||'')}"></label>
 <fieldset class="full lv-sex"><legend>Sex</legend><label class="lv-opt"><input type="radio" name="sex" value="female" ${m.sex==='female'&&(m.sexOk||!nw)?'checked':''} required><span><b>♀ Female</b></span></label><label class="lv-opt"><input type="radio" name="sex" value="male" ${m.sex==='male'&&(m.sexOk||!nw)?'checked':''}><span><b>♂ Male</b></span></label></fieldset>
 <label>Blood group<select name="blood"><option value="">Not known yet</option>${BL.map(b=>`<option ${mid.blood===b?'selected':''}>${b}</option>`).join('')}</select></label>
 <label>Mobile number <small>optional</small><input name="ph" inputmode="tel" maxlength="16" placeholder="98765 43210" value="${E((m.ph||'').replace(/^\+91/,''))}" autocomplete="off"></label>
 <label>Weight (kg) <small>optional</small><input name="w" type="number" min="2" max="300" step="0.1" value="${E(m.w||'')}" inputmode="decimal"></label>
 <label>Height (cm) <small>optional</small><input name="h" type="number" min="30" max="250" step="1" value="${E(m.h||'')}" inputmode="numeric"></label>
 <p class="full lv-err" role="alert" hidden></p>
 <div class="full" style="display:flex;gap:8px;flex-wrap:wrap;justify-content:space-between"><span>${!nw&&m.rel!=='You'?`<button class="btn s" type="button" data-sx="fdel:${m.id}" style="color:var(--red)">Remove member…</button>`:''}</span><button class="btn p" type="submit">${nw?'Add member':'Save changes'}</button></div></form>
 <p class="mute sm" style="margin:10px 0 0">Date of birth and sex set the right 3D body and the healthy ranges for results. Each person gets their own health card. For a child, you manage their records as a guardian.</p></div>`}
