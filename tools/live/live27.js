// ===================== live layer 27: medicine interactions — the pairs a pharmacist would stop you on, checked on this device =====================
{
const P=SX.p,S=SX.S;
// classes by generic name (matched inside the medicine's name or generic, so "Telma 40", "telmisartan" and "Telmisartan + HCTZ" all count)
const CLASS={
 nsaid:['ibuprofen','diclofenac','naproxen','aceclofenac','etoricoxib','mefenamic','ketorolac','nimesulide','piroxicam','indomethacin','celecoxib'],
 aspirin:['aspirin','ecosprin','acetylsalicylic'],
 anticoag:['warfarin','acenocoumarol','acitrom','rivaroxaban','apixaban','dabigatran'],
 antiplatelet:['clopidogrel','ticagrelor','prasugrel'],
 acei_arb:['enalapril','ramipril','lisinopril','perindopril','captopril','telmisartan','losartan','olmesartan','valsartan','irbesartan','candesartan','azilsartan'],
 potassium:['potassium chloride','spironolactone','eplerenone','amiloride','triamterene'],
 metformin:['metformin'],
 sulfonylurea:['glimepiride','gliclazide','glipizide','glibenclamide','glyburide'],
 insulin:['insulin'],
 statin:['atorvastatin','rosuvastatin','simvastatin','pravastatin','pitavastatin'],
 simva:['simvastatin'],
 macrolide:['clarithromycin','erythromycin'],
 azith:['azithromycin'],
 azole:['fluconazole','itraconazole','ketoconazole','voriconazole'],
 ssri:['sertraline','escitalopram','fluoxetine','paroxetine','citalopram','fluvoxamine','venlafaxine','duloxetine'],
 tramadol:['tramadol'],
 triptan:['sumatriptan','rizatriptan','zolmitriptan'],
 nitrate:['isosorbide','nitroglycerin','glyceryl trinitrate','sorbitrate'],
 pde5:['sildenafil','tadalafil','vardenafil'],
 levothyroxine:['levothyroxine','thyronorm','eltroxin','thyrox'],
 minerals:['calcium','iron','ferrous','zinc','magnesium'],
 antacid:['antacid','gelusil','digene','aluminium hydroxide','magnesium hydroxide'],
 ppi:['pantoprazole','omeprazole','esomeprazole','rabeprazole','lansoprazole'],
 ome:['omeprazole','esomeprazole'],
 quinolone:['ciprofloxacin','levofloxacin','ofloxacin','moxifloxacin','norfloxacin'],
 tetracycline:['doxycycline','minocycline','tetracycline'],
 digoxin:['digoxin'],
 diuretic:['furosemide','torsemide','hydrochlorothiazide','chlorthalidone','indapamide','hctz'],
 methotrexate:['methotrexate'],
 lithium:['lithium'],
 benzo:['alprazolam','clonazepam','diazepam','lorazepam','zolpidem','etizolam'],
 opioid:['tramadol','codeine','morphine','tapentadol'],
 betablocker:['metoprolol','atenolol','propranolol','bisoprolol','carvedilol','nebivolol'],
 ratecalcium:['verapamil','diltiazem'],
 amlodipine:['amlodipine'],
 theophylline:['theophylline','doxofylline'],
 domperidone:['domperidone'],
 ondansetron:['ondansetron'],
 cotrimoxazole:['sulfamethoxazole','cotrimoxazole','co-trimoxazole','septran'],
 paracetamol:['paracetamol','acetaminophen','dolo','crocin','calpol'],
 sedating_ah:['chlorpheniramine','diphenhydramine','promethazine','hydroxyzine','cetirizine'],
 steroid:['prednisolone','prednisone','dexamethasone','methylprednisolone','deflazacort'],
 alpha:['tamsulosin','alfuzosin','prazosin'],
};
// the pairs. lv: stop = do not combine without the doctor; warn = can be combined with care (spacing, monitoring)
const PAIRS=[
 ['anticoag','nsaid','stop','Bleeding risk rises sharply. Use paracetamol for pain unless the doctor said otherwise.'],
 ['anticoag','aspirin','stop','Both thin the blood: serious bleeding risk. Only ever together on a doctor’s instruction.'],
 ['anticoag','antiplatelet','stop','Two blood thinners together: bleeding risk. Only on a cardiologist’s instruction.'],
 ['anticoag','ssri','warn','This antidepressant adds to bleeding risk with a blood thinner. Mention it to the doctor.'],
 ['anticoag','azole','stop','This antifungal can make the blood thinner far stronger (INR shoots up). The doctor must adjust the dose.'],
 ['anticoag','macrolide','warn','This antibiotic can raise the blood thinner’s effect. An INR check during the course is wise.'],
 ['anticoag','cotrimoxazole','stop','Co-trimoxazole can make warfarin much stronger. Ask for a different antibiotic or an INR check.'],
 ['aspirin','nsaid','warn','Aspirin and another painkiller of the same family: stomach bleeding risk, and ibuprofen can block aspirin’s heart benefit. Take paracetamol instead.'],
 ['antiplatelet','nsaid','warn','Clopidogrel-type medicines plus this painkiller: bleeding risk. Prefer paracetamol.'],
 ['antiplatelet','ome','warn','Omeprazole / esomeprazole can weaken clopidogrel. Pantoprazole is the usual swap — ask the doctor.'],
 ['acei_arb','potassium','stop','Both raise potassium; high potassium can stop the heart. Needs a doctor and blood tests, never self-started.'],
 ['acei_arb','nsaid','warn','This painkiller can push up blood pressure and strain the kidneys with this BP medicine — more so with a diuretic. Short courses only, with water.'],
 ['acei_arb','lithium','stop','This BP medicine can raise lithium to toxic levels. The doctor must check levels.'],
 ['diuretic','nsaid','warn','Painkiller plus diuretic strains the kidneys. Keep courses short and drink enough water.'],
 ['diuretic','lithium','stop','Diuretics can raise lithium to toxic levels. Needs the prescribing doctor.'],
 ['diuretic','digoxin','warn','Diuretics lower potassium, which makes digoxin more toxic. Potassium checks are needed.'],
 ['sulfonylurea','quinolone','warn','This antibiotic can swing blood sugar low or high with a sugar tablet. Check sugar more often during the course.'],
 ['insulin','quinolone','warn','This antibiotic can swing blood sugar with insulin. Check sugar more often.'],
 ['sulfonylurea','betablocker','warn','Beta-blockers can hide the warning signs of low sugar (racing heart). Know the other signs: sweating, confusion.'],
 ['statin','macrolide','stop','This antibiotic raises statin levels; muscle damage risk. Pause the statin during the course — ask the doctor.'],
 ['statin','azole','stop','This antifungal raises statin levels; muscle damage risk. Ask the doctor before taking both.'],
 ['simva','amlodipine','warn','Simvastatin above 20 mg with amlodipine raises muscle-damage risk. Ask whether atorvastatin is better.'],
 ['ssri','tramadol','stop','Serotonin syndrome risk (agitation, fever, fast heart). Use a different painkiller.'],
 ['ssri','triptan','warn','Migraine medicine plus this antidepressant can cause serotonin syndrome. Use only as the doctor agreed.'],
 ['ssri','nsaid','warn','Bleeding risk in the stomach rises with this combination. Prefer paracetamol or add stomach protection.'],
 ['nitrate','pde5','stop','Dangerous blood-pressure drop. Never within 24–48 hours of each other.'],
 ['levothyroxine','minerals','warn','Calcium, iron or zinc block thyroid absorption. Take levothyroxine on an empty stomach, 4 hours apart from these.'],
 ['levothyroxine','antacid','warn','Antacids block thyroid absorption. Keep a 4-hour gap.'],
 ['levothyroxine','ppi','warn','Acid-reducers can lower thyroid absorption over time. The doctor may need to check TSH.'],
 ['quinolone','minerals','warn','Calcium, iron or zinc stop this antibiotic from being absorbed. Take them 2 hours apart.'],
 ['quinolone','antacid','warn','Antacids stop this antibiotic from working. Take them 2 hours apart.'],
 ['tetracycline','minerals','warn','Calcium, iron or zinc stop doxycycline being absorbed. Take them 2 hours apart.'],
 ['tetracycline','antacid','warn','Antacids block doxycycline. Take them 2 hours apart.'],
 ['digoxin','ratecalcium','stop','Verapamil / diltiazem raise digoxin levels and slow the heart too much. Doctor-only combination.'],
 ['digoxin','macrolide','warn','This antibiotic can raise digoxin levels. Watch for nausea, vision changes, slow pulse.'],
 ['methotrexate','nsaid','stop','Painkillers of this family can push methotrexate to toxic levels. Ask the prescribing doctor.'],
 ['methotrexate','cotrimoxazole','stop','This antibiotic with methotrexate can suppress the bone marrow. Avoid.'],
 ['lithium','nsaid','stop','Painkillers of this family raise lithium levels. Use paracetamol.'],
 ['benzo','opioid','stop','Sedative plus opioid painkiller: breathing can slow dangerously, especially in older people.'],
 ['benzo','sedating_ah','warn','Two sedating medicines: heavy drowsiness, falls in older people. Avoid driving.'],
 ['opioid','sedating_ah','warn','Extra drowsiness and slowed breathing. Avoid driving; be careful in older people.'],
 ['betablocker','ratecalcium','stop','Both slow the heart; together they can cause a dangerously slow rate or heart block. Specialist-only.'],
 ['theophylline','quinolone','stop','This antibiotic raises theophylline to toxic levels (seizures, racing heart). Ask for another antibiotic.'],
 ['theophylline','macrolide','warn','This antibiotic raises theophylline levels. Levels may need checking.'],
 ['domperidone','azole','stop','Heart-rhythm risk (QT prolongation). Avoid together.'],
 ['domperidone','macrolide','stop','Heart-rhythm risk (QT prolongation). Avoid together.'],
 ['ondansetron','macrolide','warn','Both can affect heart rhythm. Fine for a short course in a healthy heart; ask if there is heart disease.'],
 ['ondansetron','quinolone','warn','Both can affect heart rhythm. Ask if there is heart disease or other QT-prolonging medicine.'],
 ['steroid','nsaid','warn','Steroid plus painkiller: stomach ulcer and bleeding risk. Take with food; ask about stomach protection.'],
 ['metformin','steroid','warn','Steroids push sugar up; metformin may not cover it during the course. Check sugar more often.'],
 ['alpha','pde5','warn','Both lower blood pressure; dizziness on standing. Take at different times of day, as the doctor agrees.'],
 ['paracetamol','paracetamol','warn','Two medicines contain paracetamol. Keep the day’s total under 3 g (6 × 500 mg) — many cold remedies hide it.'],
];
const norm=s=>String(s||'').toLowerCase();
function classesOf(x){const t=norm(x.n)+' '+norm(x.gen)+' '+norm(x.dose);const out=[];for(const k in CLASS)if(CLASS[k].some(g=>t.includes(g)))out.push(k);return out}
SX.medClasses=classesOf;
// every flagged pair among a person's medicines (+ one more being considered)
function check(m,extra,skipId){const list=(S.meds[m.id]||[]).filter(x=>x.id!==skipId).map(x=>({x,c:classesOf(x)}));if(extra)list.push({x:extra,c:classesOf(extra),new:true});
 const out=[],seen=new Set();
 for(let i=0;i<list.length;i++)for(let j=i+1;j<list.length;j++){const A=list[i],B=list[j];
  for(const [a,b,lv,t] of PAIRS){const hit=(A.c.includes(a)&&B.c.includes(b))||(A.c.includes(b)&&B.c.includes(a));if(!hit)continue;if(a===b&&A.x.id===B.x.id)continue;
   const key=[A.x.n,B.x.n,a,b].join('|');if(seen.has(key))continue;seen.add(key);
   out.push({lv,t:`${A.x.n} + ${B.x.n}: ${t}`,a:A.x,b:B.x,involvesNew:!!(A.new||B.new)})}}
 return out.sort((p,q)=>(q.lv==='stop')-(p.lv==='stop'))}
SX.medInteract=(m,name,skipId)=>check(m,{n:name,gen:name},skipId).filter(w=>w.involvesNew);
SX.medPairs=m=>check(m,null);
// the finder and the medicine form already ask SX.medWarn about a catalogue item: add the pairs with what the person already takes
const warn0=SX.medWarn;SX.medWarn=(m,it)=>warn0(m,it).concat(check(m,{n:it.n||it.gen||'',gen:it.gen||''}).filter(w=>w.involvesNew));
// a card on the Medicines page: every pair in the current list
SX.extend('rx',{before(){const m=SX.me(),w=check(m,null);if(!w.length)return '';
 return `<div class="card lv27"><div class="hd"><div><h3>${P('Checks on this list')}</h3><small class="mute">${P('Pairs a pharmacist would ask about. Checked on this device, from the names alone — nothing is sent anywhere.')}</small></div></div>${w.map(x=>`<div class="lv27-w ${x.lv}"><i>${x.lv==='stop'?'!':'i'}</i><div>${E(x.t)}</div></div>`).join('')}<p class="mute sm" style="margin:8px 0 0">${P('This is a safety net, not a verdict: your doctor may have chosen a pair on purpose. Never stop a medicine without asking.')}</p></div>`}});
SX.lv27={check,classesOf,PAIRS,CLASS};
}
