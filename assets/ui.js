/* Versión 10: interfaz pública clásica, formato numérico y flechas de incremento.
 * Se conserva la estructura visual del proyecto crt-vmr-5g-publico.
 */
import {DATA} from './data.js';
import {CONTROLS} from './controls.js';
import {BANDS,initialState,clone,getPath,setPath,inputError,calculateVmr,calculateDiscount,encodeScenario,decodeScenario,csvCell,sum} from './model.js';

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const N = (v,d=0) => Number.isFinite(v) ? new Intl.NumberFormat('es-MX',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v) : '—';
const MXN = (v,d=2) => Number.isFinite(v) ? '$'+N(v,d) : '—';
const MM = v => MXN(v/1000000,2);
const PCT = (v,d=1) => N(v*100,d)+' %';
// Los campos editables muestran 1,234,567.89 (coma para miles, punto decimal).
// Son de tipo text porque input[type=number] prohíbe representar las comas.
// Nunca redondear los números del motor: solamente se formatea la vista.
function numberDisplay(value) {
 if(value===null||value===undefined)return '';
 return groupNumberString(String(value));
}
function groupNumberString(value) {
 const raw=String(value).replace(/,/g,'');
 if(!/^-?(?:\d*(?:\.\d*)?)$/.test(raw))return value;
 const sign=raw.startsWith('-')?'-':'';
 const content=raw.slice(sign.length), dot=content.indexOf('.');
 const whole=dot===-1?content:content.slice(0,dot);
 const tail=dot===-1?'':content.slice(dot); // conservar . y decimales mientras se edita
 return sign+whole.replace(/\B(?=(\d{3})+(?!\d))/g,',')+tail;
}
function parseNumberInput(raw) {
 const clean=raw.trim().replace(/,/g,'');
 if(clean==='')return null;
 if(!/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(clean))return NaN;
 return Number(clean);
}
function formatWhileTyping(el) {
 const old=el.value, oldPos=el.selectionStart;
 const formatted=groupNumberString(old);
 if(old===formatted)return;
 el.value=formatted;
 if(oldPos===null)return;
 // Ajustar la posición del cursor al insertar o quitar separadores de millar.
 const count=old.slice(0,oldPos).replace(/,/g,'').length;
 let position=0, seen=0;
 while(position<formatted.length&&seen<count){if(formatted[position]!==',')seen++;position++;}
 if(formatted[position]===',')position++;
 el.setSelectionRange(position,position);
}
function formatOnBlur(el) {
 if(el.dataset.numberFormat!=='grouped')return;
 // Mantener el texto inválido visible para que el usuario pueda corregirlo.
 if(el.dataset.k&&invalid.has(el.dataset.k))return;
 if(el.dataset.modePart&&invalid.has('discounts.allocations.'+modeIndex()))return;
 const number=parseNumberInput(el.value);
 if(number!==null&&Number.isFinite(number))el.value=numberDisplay(number);
}


// Controles nativos tipo number no muestran comas; flechas accesibles conservan el
// texto con separadores y despachan input para usar las validaciones ya existentes.
function enhanceNumberInputs(){
 document.querySelectorAll('input[data-number-format="grouped"]:not([data-steppers-ready])').forEach(el=>{
  el.dataset.steppersReady='1';
  const wrap=el.closest('.input-wrap');
  if(!wrap){
   const node=document.createElement('span');node.className='number-table-control';
   el.parentNode.insertBefore(node,el);node.append(el);
  }
  const target=wrap||el.closest('.number-table-control');
  const buttons=document.createElement('span');buttons.className='number-steppers';
  const label=el.getAttribute('aria-label')||el.closest('label')?.querySelector('span')?.textContent?.trim()||'valor';
  buttons.innerHTML=`<button class="number-step" type="button" data-step-dir="1" aria-label="Aumentar ${escape(label)}" title="Aumentar"></button><button class="number-step" type="button" data-step-dir="-1" aria-label="Disminuir ${escape(label)}" title="Disminuir"></button>`;
  target.insertBefore(buttons,wrap?.querySelector('.unit')||null);
 });
}
function changeNumberStep(input,direction){
 const current=parseNumberInput(input.value);
 if(current!==null&&!Number.isFinite(current))return;
 const stepAttr=input.getAttribute('step');
 const decimals=(input.value.replace(/,/g,'').split('.')[1]||'').length;
 const step=stepAttr&&stepAttr!=='any'&&Number(stepAttr)>0?Number(stepAttr):Math.pow(10,-Math.min(decimals,8));
 const stepDecimals=(String(step).split('.')[1]||'').length;
 const places=Math.min(10,Math.max(decimals,stepDecimals));
 const minAttr=input.getAttribute('min'),maxAttr=input.getAttribute('max');
 const min=minAttr!==null?Number(minAttr):-Infinity, max=maxAttr!==null?Number(maxAttr):Infinity;
 const start=current===null?(Number.isFinite(min)?min:0):current;
 let next=Number((start+direction*step).toFixed(places));
 next=Math.min(max,Math.max(min,next));
 if(current===next)return;
 input.value=numberDisplay(next);
 input.dispatchEvent(new Event('input',{bubbles:true}));
 input.focus({preventScroll:true});
}

const TABS = ['calc','discounts','region','method','help'];
let S = initialState();
let regionBand=0, regionMode='scenario', vmrResults=null,discountResult=null;
let openCards=[false,false,false], invalid=new Map(), initMessage='', flashTimer;
const defaults = initialState();
const modelModified = () => JSON.stringify(S) !== JSON.stringify(defaults);
const vmrModified = () => JSON.stringify({...S,discounts:null}) !== JSON.stringify({...defaults,discounts:null}) || S.discounts.reduction!==defaults.discounts.reduction;
const withinTolerance = (a,b) => Math.abs(a-b)<Math.max(0.001,Math.abs(b)*1e-10);

function announce(msg, el='#notice') {
 const node=$(el); if(!node)return;
 node.textContent=msg;node.hidden=false;
 if(el==='#notice'){clearTimeout(flashTimer);flashTimer=setTimeout(()=>node.hidden=true,5500);}
}
function field(path,label,unit='',opt={}) {
 const v=getPath(S,path), min=opt.min ?? 0;
 return `<label class="field"><span>${escape(label)}${opt.small?` <small>${escape(opt.small)}</small>`:''}</span><div class="input-wrap"><input data-k="${path}" data-number-format="grouped" type="text" autocomplete="off" min="${min}" ${opt.max!==undefined?`max="${opt.max}"`:''} step="${opt.step??'any'}" inputmode="${opt.step===1?'numeric':'decimal'}" value="${escape(numberDisplay(v))}">${unit?`<span class="unit">${escape(unit)}</span>`:''}</div><span class="err" role="alert"></span></label>`;
}
function select(path,label,items){
 const v=getPath(S,path);
 return `<label class="field"><span>${escape(label)}</span><select data-k="${path}">${items.map(([value,text])=>`<option value="${escape(value)}" ${value===v?'selected':''}>${escape(text)}</option>`).join('')}</select><span class="err" role="alert"></span></label>`;
}
function mini(path,label,opt={}) {
 const v=getPath(S,path);
 return `<input type="text" inputmode="decimal" data-number-format="grouped" autocomplete="off" data-k="${path}" value="${escape(numberDisplay(v))}" min="${opt.min??0}" ${opt.max!==undefined?`max="${opt.max}"`:''} step="${opt.step??'any'}" aria-label="${escape(label)}" title="${escape(label)}">`;
}
// Se conserva el select clásico. Las proporciones personalizadas se guardan por modalidad
// sin alterar los porcentajes oficiales en los datos fuente.
function allowedModes(){
 const i=DATA.operators.indexOf(S.discounts.operator);
 return DATA.modes.filter(m=>i<2||m.allOperators);
}
const modeIndex=()=>DATA.modes.findIndex(m=>m.name===S.discounts.mode);
const modePercent=v=>new Intl.NumberFormat('es-MX',{maximumFractionDigits:2}).format(v)+' %';
function updateModeFeedback(preserveActive=false){
 const index=modeIndex();if(index<0)return;
 const coverage=S.discounts.allocations[index],modern=Math.round((100-coverage)*100)/100;
 const baseline=Math.round(DATA.modes[index].coverage*100);
 const changed=Math.abs(coverage-baseline)>1e-8;
 const summary=$('#modeSummary');
 if(summary)summary.innerHTML=`<strong>Ampliación de cobertura:</strong> ${modePercent(coverage)} · <strong>Modernización:</strong> ${modePercent(modern)}${changed?' <span class="mode-tag">Simulación personalizada</span>':''}`;
 const cover=$('#modeCoverage'),modernEl=$('#modeModern');
 if(cover&&(!preserveActive||document.activeElement!==cover))cover.value=numberDisplay(coverage);
 if(modernEl&&(!preserveActive||document.activeElement!==modernEl))modernEl.value=numberDisplay(modern);
 if(cover)cover.setAttribute('aria-invalid',String(Boolean(invalid.get('discounts.allocations.'+index))));
 if(modernEl)modernEl.setAttribute('aria-invalid',String(Boolean(invalid.get('discounts.allocations.'+index))));
 const msg=$('#modeEditError');if(msg){msg.textContent=invalid.get('discounts.allocations.'+index)||'';msg.hidden=!msg.textContent;}
}
function buildDiscountInputs(){
 const wasOpen=$('#modeEditor')?.open||false;
 const modes=allowedModes();
 const max=DATA.discountMaximum[DATA.operators.indexOf(S.discounts.operator)];
 $('#discountInputs').innerHTML=
  select('discounts.operator','Operador / tipo',DATA.operators.map((op,i)=>[op,`${op} · Tipo ${'ABCDE'[i]}`]))+
  `<div class="mode-select-box">${select('discounts.mode','Modalidad de la obligación',modes.map(m=>[m.name,m.name]))}
   <p class="mode-summary" id="modeSummary" aria-live="polite"></p>
   <details id="modeEditor" class="mode-editor" ${wasOpen?'open':''}>
    <summary>Editar valores de la modalidad</summary>
    <div class="mode-editor-body">
     <div class="mode-ratios">
      <label class="field" for="modeCoverage"><span>Ampliación de cobertura</span><div class="input-wrap"><input id="modeCoverage" data-mode-part="coverage" type="text" data-number-format="grouped" min="0" max="100" inputmode="decimal" autocomplete="off"><span class="unit">%</span></div></label>
      <label class="field" for="modeModern"><span>Modernización</span><div class="input-wrap"><input id="modeModern" data-mode-part="modern" type="text" data-number-format="grouped" min="0" max="100" inputmode="decimal" autocomplete="off"><span class="unit">%</span></div></label>
     </div><p id="modeEditError" class="mode-edit-error" role="alert" hidden></p>
    </div>
   </details></div>`+
  select('discounts.percent','Descuento por obligaciones',Array.from({length:max/10},(_,i)=>[(i+1)*10,`${(i+1)*10} %`]))+
  `<p class="hint">Máximo permitido para este operador: ${max} %. La tabla presenta también los porcentajes que no aplican.</p>`;
 updateModeFeedback();
 buildDiscountAdvanced();
}
function changeModeRatio(el){
 const index=modeIndex();if(index<0)return;
 formatWhileTyping(el);
 const value=parseNumberInput(el.value);
 const key='discounts.allocations.'+index;
 const err=inputError(key,value);
 if(err){invalid.set(key,err);el.setAttribute('aria-invalid','true');const msg=$('#modeEditError');msg.hidden=false;msg.textContent=err;updateErrors();return;}
 invalid.delete(key);
 const coverage=el.dataset.modePart==='coverage'?value:Math.round((100-value)*100)/100;
 S.discounts.allocations[index]=coverage;
 // Dejar el campo que se está editando intacto para no mover el cursor.
 updateModeFeedback(true);updateErrors();render();
}
function buildDiscountAdvanced() {
 const d=S.discounts,i=DATA.operators.indexOf(d.operator);
 $('#discountAdvanced').innerHTML=
 field('discounts.reduction','Reducción general de derechos','%',{max:100})+
 field('discounts.years','Horizonte del descuento','años',{min:1,max:50,step:1})+
 field('discounts.costCoverage','Costo por radiobase de cobertura','MXN',{min:0.001})+
 field('discounts.costModern','Costo por radiobase modernizada','MXN',{min:0.001})+
 field('discounts.modernFactor','Factor de modernización','%',{min:0.0001,max:100})+
 field('discounts.localitiesPerBase','Localidades por radiobase','',{min:1,step:1})+
 field('discounts.populationPerLocality','Habitantes por localidad','hab',{min:1,step:1})+
 field('discounts.populationPerModern','Habitantes por radiobase modernizada','hab',{min:1,step:1})+
 `<div class="band-input plain"><h3>Base anual de ${escape(d.operator)}</h3>`+
 (i<2?field(`discounts.rights.${i}`,'Derechos de referencia','MXN'):
 field(`discounts.minimum.${i}`,'Mínimo del rango anual','MXN')+
 field(`discounts.maximum.${i}`,'Máximo del rango anual','MXN')+
 field('discounts.rangeFactor','Proporción del promedio','%',{max:100}))+'</div>';
 updateErrors();
}
function buildRefEditor() {
 $('#refEditor').innerHTML=`<div class="table-wrap" role="region" tabindex="0" aria-label="Licitaciones nacionales editables"><table class="editor"><thead><tr><th>Licitación</th><th>MHz ponderados</th><th>Monto pagado (MXN)</th><th>INPC de origen</th></tr></thead><tbody>${S.references.map((r,j)=>`<tr><th scope="row">${escape(r.label)}</th><td>${mini(`references.${j}.spectrum`,`MHz ponderados ${r.label}`,{min:0.0000001})}</td><td>${mini(`references.${j}.amount`,`Monto ${r.label}`)}</td><td>${mini(`references.${j}.baseInpc`,`INPC ${r.label}`,{min:0.0001})}</td></tr>`).join('')}</tbody></table></div>`;
}
function buildRegionEditor() {
 const qcol=(band,k)=>`<td>${mini(`q.${band.key}.${k}`,`Cuota ${band.label}, región ${k+1}`)}</td>`;
 $('#editorTable').innerHTML=`<thead><tr><th>Región</th><th>Población</th>${BANDS.map(b=>`<th>Cuota ${b.label}</th>`).join('')}${BANDS.map(b=>`<th>Cobertura ${b.label} (%)</th>`).join('')}</tr></thead><tbody>${S.population.map((_,k)=>`<tr><th scope="row">Región ${k+1}</th><td>${mini(`population.${k}`,`Población región ${k+1}`,{step:1})}</td>${BANDS.map(b=>qcol(b,k)).join('')}${BANDS.map((b,i)=>`<td>${mini(`coverage.${i}.${k}`,`Cobertura ${b.label} región ${k+1}`,{max:100})}</td>`).join('')}</tr>`).join('')}</tbody>`;
}
function buildBenchmarkEditor() {
 const filter=$('#benchmarkFilter').value;
 $('#benchmarkEditor').innerHTML=`<thead><tr><th>País y subasta</th><th>Banda</th><th>MXN/MHz/hab</th><th>Incluir</th></tr></thead><tbody>${DATA.benchmarks.map((b,i)=>filter!=='all'&&b.band!==filter?'':`<tr><th scope="row">${escape(b.label)}</th><td>${escape(b.band)}</td><td>${N(b.value,6)}</td><td><input type="checkbox" data-k="benchmarkIncluded.${i}" ${S.benchmarkIncluded[i]?'checked':''} aria-label="Incluir ${escape(b.label)} en ${escape(b.band)}"></td></tr>`).join('')}</tbody>`;
}
function fillInputs() {
 $$('[data-k]').forEach(el=>{
  const v=getPath(S,el.dataset.k);
  if(el.type==='checkbox')el.checked=Boolean(v);
  else if(v!==undefined)el.value=el.dataset.numberFormat==='grouped'?numberDisplay(v):v;
 });
 updateErrors();
}
function updateErrors() {
 $$('[data-k]').forEach(el=>{
  const err=invalid.get(el.dataset.k)||'';
  el.setAttribute('aria-invalid',err?'true':'false');
  const label=el.closest('.field');if(label){label.classList.toggle('invalid',Boolean(err));const output=label.querySelector('.err');if(output)output.textContent=err;}
  else if(err)el.title=err;
 });
}
function errorsForVmr() {
 return [...invalid].find(([k])=>!k.startsWith('discounts.')||k==='discounts.reduction')?.[1];
}
function discountFieldUsed(path) {
 if(!path.startsWith('discounts.'))return false;
 const i=DATA.operators.indexOf(S.discounts.operator);
 if(/^discounts\.rights\./.test(path))return i<2&&path===`discounts.rights.${i}`;
 if(/^discounts\.(minimum|maximum)\./.test(path))return i>1&&path.endsWith('.'+i);
 if(path==='discounts.rangeFactor')return i>1;
 return true;
}
function errorsForDiscount() {
 return [...invalid].find(([k])=>discountFieldUsed(k))?.[1];
}
function renderBanner() {
 const el=$('#scenarioBanner');
 if(vmrModified()){
  el.className='banner modified';el.innerHTML='<div><strong>Escenario modificado.</strong> Estos resultados son una simulación con supuestos diferentes al modelo base 2026.</div><button class="btn" type="button" data-action="reset-vmr">Restablecer VMR</button>';
 }else{
  el.className='banner base';el.innerHTML='<div><strong>Valores base del modelo VMR 5G 2026.</strong> Puede cambiar los MHz o consultar la pestaña «Descuentos y obligaciones».</div>';
 }
}
function stepRow(label,help,value,key){return `<tr${key?' class="key"':''}><td>${label}${help?`<small>${help}</small>`:''}</td><td>${value}</td></tr>`;}
function cardHtml(x,i){
 const b=BANDS[i],bad=!(x.mp>0),source=x.source==='n'?'Referencia nacional':'Comparación internacional';
 return `<article class="card" style="--band:${b.color}" aria-label="Banda ${b.label}"><div class="card-head"><div><h3>Banda de ${b.label}</h3><div class="sub">${source}</div></div><span class="badge ${bad?'warn':''}">${bad?'Revisar precio unitario':'Cálculo válido'}</span></div>
 <p class="plain">Para <strong>${N(x.mhz,2)} MHz</strong>, el VMR es de:</p><div class="big">${MM(x.vmr)}<small>millones de pesos</small></div><div class="full">${MXN(x.vmr)} MXN</div>
 <dl class="metrics"><div class="metric"><dt>Precio unitario (MHz/pop)</dt><dd>${MXN(x.mp,4)}<small> por MHz y habitante</small></dd></div><div class="metric"><dt>Población cubierta</dt><dd>${N(x.covered)}<small> habitantes</small></dd></div><div class="metric"><dt>Cobertura ponderada</dt><dd>${PCT(x.coverageWeight)}</dd></div></dl>
 <details data-card="${i}" ${openCards[i]?'open':''}><summary>¿Cómo se obtuvo el precio unitario y los derechos?</summary>
 <table class="chain"><tbody>
 ${stepRow('Mediana del benchmark',`${x.observations} observaciones incluidas`,N(x.median,6))}
 ${stepRow('(a) VP del benchmark','Anualidad ordinaria',N(x.a,4))}
 ${stepRow('(b) VP de derechos LFD','Anualidad anticipada',N(x.b,4))}
 ${stepRow('(a) − (b)','Diferencia en pesos por MHz y habitante',N(x.a-x.b,4))}
 ${stepRow('Factor INPC','Redondeado a cuatro decimales',N(x.factor,4))}
 ${stepRow('Benchmark actualizado','',N(x.benchmark,4))}
 ${stepRow('Referencia nacional',i===0?'No aplica':'Monto de licitaciones anteriores',x.national===null?'No aplica':N(x.national,4))}
 ${stepRow('Precio unitario aplicable',source,N(x.mp,4),true)}
 ${stepRow('Derechos anuales base','Antes de reducción general',MXN(x.rights))}
 ${stepRow(`Derechos con reducción ${N(x.reduction*100)} %`,'No reduce el VMR',MXN(x.rightsNet))}
 ${stepRow('Ahorro anual de derechos','Reducción general',MXN(x.saving))}
 ${stepRow('VP derechos base','',MXN(x.rightsPv))}
 ${stepRow('VP derechos con reducción','',MXN(x.rightsNetPv))}
 </tbody></table>${bad?'<p class="hint warn-text">El precio unitario es cero o negativo; considere revisar la fuente.</p>':''}</details>
 <div class="status-line"><span><strong>Espectro:</strong> ${N(x.mhz,2)} MHz</span><span><strong>Población nacional:</strong> ${N(x.population)} hab.</span></div></article>`;
}
function renderVmr(){
 let err='';
 try{vmrResults=calculateVmr(S);}catch(e){err=e.message;vmrResults=null;}
 if(!err&&errorsForVmr())err='Hay campos fuera de rango. Se conservan los últimos valores válidos para el cálculo.';
 $('#vmrError').hidden=!err;$('#vmrError').textContent=err;
 $('#regionError').hidden=!err;$('#regionError').textContent=err;
 $('#cards').innerHTML=vmrResults?vmrResults.map(cardHtml).join(''):'';
 if(!vmrResults)$('#cards').innerHTML='<div class="panel">Revise los parámetros del modelo para mostrar los resultados.</div>';
 renderRegion();
}
function renderBandSelector(){
 $('#bandSelector').innerHTML=BANDS.map((b,i)=>`<button type="button" data-band="${i}" aria-pressed="${i===regionBand}" style="--band:${b.color}">${b.label}</button>`).join('');
 $('#modeSelector').innerHTML=`<button type="button" data-mode="scenario" aria-pressed="${regionMode==='scenario'}">Mi escenario</button><button type="button" data-mode="excel" aria-pressed="${regionMode==='excel'}">Valores base actualizados</button>`;
}
function renderRegion(){
 renderBandSelector();const b=BANDS[regionBand];$('#regionalPanel').style.setProperty('--band',b.color);
 if(!vmrResults){$('#regionTable').innerHTML='';return;}
 const base=regionMode==='excel';let x;
 try{x=base?calculateVmr(initialState())[regionBand]:vmrResults[regionBand];}catch(e){$('#regionError').hidden=false;$('#regionError').textContent=e.message;return;}
 $('#regionNote').textContent=base?'Corresponde a los valores base actualizados, sin aplicar los cambios de su escenario. Las nueve regiones usan las cuotas de su propia banda.':'Usa los MHz, las cuotas y la cobertura de su escenario. Derechos y VMR se muestran separados; las barras comparan las regiones.';
 const highest=Math.max(1,...x.regions.map(r=>Math.max(0,r.vmr)));
 $('#regionTable').innerHTML=`<caption class="sr">VMR de ${b.label} por región celular</caption><thead><tr><th>Región</th><th>Población</th><th>Cobertura</th><th>Proporción LFD</th><th>VMR (MXN)</th><th>Derechos anuales base</th><th>VP derechos base</th><th>Derechos anuales con reducción</th><th>VP derechos reducidos</th></tr></thead><tbody>`+
 x.regions.map(r=>`<tr><th scope="row">Región ${r.region}</th><td>${N(r.population)}</td><td>${PCT(r.coverage)}</td><td>${PCT(r.prop,2)}</td><td>${MXN(r.vmr,2)}<div class="bar" style="width:${Math.max(0,r.vmr)/highest*100}%"></div></td><td>${MXN(r.rights,2)}</td><td>${MXN(r.rightsPv,2)}</td><td>${MXN(r.rightsNet,2)}</td><td>${MXN(r.rightsNetPv,2)}</td></tr>`).join('')+
 `</tbody><tfoot><tr><th scope="row">Total</th><td>${N(x.population)}</td><td>${PCT(x.covered/x.population)}</td><td>${PCT(x.coverageWeight,2)}</td><td>${MXN(x.vmr,2)}</td><td>${MXN(x.rights,2)}</td><td>${MXN(x.rightsPv,2)}</td><td>${MXN(x.rightsNet,2)}</td><td>${MXN(x.rightsNetPv,2)}</td></tr></tfoot>`;
}
function kpi(label,v,unit){return `<div class="metric discount-kpi"><dt>${label}</dt><dd>${v}<small>${unit}</small></dd></div>`;}
function renderDiscountComparison(){
 const table=$('#discountComparison');
 const d=S.discounts, idx=DATA.operators.indexOf(d.operator);
 if(idx<0){table.innerHTML='';return;}
 const max=DATA.discountMaximum[idx];
 $('#discountTableNote').textContent=`${d.operator} · ${d.mode} · Ampliación ${modePercent(d.allocations[modeIndex()])} / Modernización ${modePercent(100-d.allocations[modeIndex()])} · ${d.years} años · Máximo permitido: ${max} %. Se aplican los parámetros vigentes.`;
 const headers=`<caption class="sr">Todos los porcentajes de descuento, montos, radiobases, localidades y habitantes calculados</caption><thead><tr class="group-head"><th scope="col" rowspan="2">Descuento</th><th scope="colgroup" colspan="3">Montos del descuento</th><th scope="colgroup" colspan="4">Ampliación de cobertura</th><th scope="colgroup" colspan="3">Modernización</th></tr><tr><th scope="col">Base anual<br>(MDP)</th><th scope="col">Anual<br>(MDP)</th><th scope="col">Total ${d.years} años<br>(MDP)</th><th scope="col">Monto<br>(MDP)</th><th scope="col">Radiobases</th><th scope="col">Localidades</th><th scope="col">Habitantes</th><th scope="col">Monto<br>(MDP)</th><th scope="col">Radiobases</th><th scope="col">Habitantes</th></tr></thead>`;
 try{
  const rows=Array.from({length:10},(_,i)=>(i+1)*10).map(percent=>{
   const r=calculateDiscount({...d,percent});
   const selected=percent===d.percent;
   const first=`<th scope="row"><button type="button" data-select-discount="${percent}" ${r.available?'':'disabled'} aria-pressed="${selected}">${percent} %${selected?' ✓':''}</button></th>`;
   if(!r.available)return `<tr class="unavailable">${first}<td colspan="10"><strong>No aplica.</strong> ${escape(r.reason)}</td></tr>`;
   const M=v=>N(v/1000000,2);
   return `<tr${selected?' class="selected-discount"':''}>${first}<td>${M(r.annualBase)}</td><td>${M(r.annualDiscount)}</td><td class="discount-total">${M(r.amount)}</td><td>${M(r.coverageBudget)}</td><td>${N(r.coverageBases)}</td><td>${N(r.localities)}</td><td>${N(r.coveragePopulation)}</td><td>${M(r.modernBudget)}</td><td>${N(r.modernBases)}</td><td>${N(r.modernPopulation)}</td></tr>`;
  }).join('');
  table.innerHTML=headers+`<tbody>${rows}</tbody>`;
 }catch(e){table.innerHTML=headers+`<tbody><tr><td colspan="11" class="warn-text">No es posible calcular la tabla: ${escape(e.message)}</td></tr></tbody>`;}
}
function renderDiscounts(){
 let err='';
 try{discountResult=calculateDiscount(S.discounts);if(!discountResult.available){err=discountResult.reason;discountResult=null;}}catch(e){err=e.message;discountResult=null;}
 if(!err&&errorsForDiscount())err='Hay campos fuera de rango. Se conservan los últimos valores válidos para el cálculo.';
 $('#discountError').hidden=!err;$('#discountError').textContent=err;
 const d=S.discounts;
 $('#discountScenario').textContent=`${d.operator} · ${d.mode} · ${d.percent}%${Math.abs(d.allocations[modeIndex()]-DATA.modes[modeIndex()].coverage*100)>1e-8?' · distribución personalizada':''}`;
 renderDiscountComparison();
 if(!discountResult){$('#discountResults').innerHTML='';return;}
 const r=discountResult;
 $('#discountResults').innerHTML=`<article class="card" style="--band:#3f7779"><div class="card-head"><div><h3>Descuento total por obligaciones</h3><div class="sub">${escape(d.operator)} · ${escape(d.mode)} · ${d.years} años</div></div><span class="badge">${d.percent}%</span></div><p class="plain">Descuento nominal del periodo:</p><div class="big">${MM(r.amount)}<small>millones de pesos</small></div><div class="full">${MXN(r.amount)} MXN</div><dl class="metrics">${kpi('Descuento anual',MM(r.annualDiscount),'millones de MXN/año')}${kpi('Base anual para obligaciones',MM(r.annualBase),'millones de MXN/año')}${kpi('Reducción general aplicada',PCT(r.reduction),'')}</dl></article>
 <div class="obligation-grid"><article class="card" style="--band:#7d3f56"><div class="card-head"><h3>Ampliación de cobertura</h3><span class="badge">${modePercent(r.coverageProportion*100)} del monto</span></div><p class="plain">Radiobases por desplegar</p><div class="big">${N(r.coverageBases)}</div><dl class="metrics two">${kpi('Localidades',N(r.localities),'por cubrir')}${kpi('Habitantes',N(r.coveragePopulation),'estimados')}</dl><div class="status-line"><strong>Monto asignado:</strong> ${MXN(r.coverageBudget)} MXN</div></article>
 <article class="card" style="--band:#8b681d"><div class="card-head"><h3>Modernización</h3><span class="badge">${modePercent(r.modernProportion*100)} del monto</span></div><p class="plain">Radiobases por modernizar</p><div class="big">${N(r.modernBases)}</div><dl class="metrics two">${kpi('Habitantes',N(r.modernPopulation),'estimados')}${kpi('Factor de modernización',N(d.modernFactor)+'%','')}</dl><div class="status-line"><strong>Monto asignado:</strong> ${MXN(r.modernBudget)} MXN</div></article></div>`;
}
function renderAudit(){
 const checks=[];
 const add=(name,actual,expected)=>checks.push({name,actual,expected,ok:withinTolerance(actual,expected)});
 try{
  const rs=calculateVmr(initialState());
  rs.forEach((r,i)=>{
   add(`${r.band}: VMR base`,r.vmr,CONTROLS.vmr[i]);
   add(`${r.band}: derechos anuales`,r.rights,CONTROLS.rights[i]);
   add(`${r.band}: VP de derechos`,r.rightsPv,CONTROLS.rightsPv[i]);
   add(`${r.band}: mediana`,r.median,CONTROLS.medians[i]);
   r.regions.forEach((z,j)=>add(`${r.band}, región ${j+1}`,z.vmr,CONTROLS.regions[i][j]));
  });
  CONTROLS.discounts.forEach((c,j)=>{
   const r=calculateDiscount({...initialState().discounts,operator:c.operator,mode:c.mode,percent:c.percent});
   for(const key of ['amount','localities','coveragePopulation','modernBases','modernPopulation'])add(`Descuento ${j+1}: ${key}`,r[key],c[key]);
  });
 }catch(e){$('#auditSummary').textContent='Error en la verificación: '+e.message;return;}
 const ok=checks.filter(c=>c.ok).length,all=ok===checks.length;
 $('#auditSummary').innerHTML=`<strong>${ok} de ${checks.length} verificaciones correctas</strong><span>VMR, derechos, regiones y 90 escenarios de descuentos contrastados con Excel.</span><div class="check ${all?'':'bad'}">${all?'✓ Los resultados base coinciden con el Excel':'✕ Hay diferencias; revise el modelo antes de publicar'}</div>`;
 $('#auditTable').innerHTML=`<caption class="sr">Comprobaciones del modelo base</caption><thead><tr><th>Comprobación</th><th>Calculadora</th><th>Libro fuente</th><th>Estado</th></tr></thead><tbody>${checks.map(c=>`<tr><th scope="row">${escape(c.name)}</th><td>${N(c.actual,4)}</td><td>${N(c.expected,4)}</td><td>${c.ok?'✓ Correcta':'✕ Revisar'}</td></tr>`).join('')}</tbody>`;
}
function render(){renderBanner();renderVmr();renderDiscounts();}
function handleInput(ev){
 const el=ev.target,path=el.dataset?.k;if(!path)return;
 let value;
 if(el.type==='checkbox')value=el.checked;
 else if(el.tagName==='SELECT')value=path==='discounts.percent'?Number(el.value):el.value;
 else {if(el.dataset.numberFormat==='grouped')formatWhileTyping(el);value=parseNumberInput(el.value);}
 const err=typeof value==='number'||value===null?inputError(path,value):'';
 if(err){invalid.set(path,err);updateErrors();return;}
 invalid.delete(path);
 setPath(S,path,value);
 // Al cambiar de operador, ajuste los controles a las modalidades y límites permitidos.
 if(path==='discounts.operator'){
  const choices=allowedModes(),i=DATA.operators.indexOf(value),max=DATA.discountMaximum[i];
  const changed=[];
  if(!choices.some(m=>m.name===S.discounts.mode)){
   S.discounts.mode=choices[0].name;changed.push('modalidad');
  }
  if(S.discounts.percent>max){S.discounts.percent=max;changed.push('porcentaje máximo');}
  buildDiscountInputs();fillInputs();
  if(changed.length)announce(`Se ajustó ${changed.join(' y ')} a las opciones permitidas para ${value}.`);
 } else {
  // No reconstruir formularios mientras se arrastra el control o se escribe.
  for(const other of $$('[data-k]'))if(other!==el&&other.dataset.k===path){if(other.type==='checkbox')other.checked=value;else other.value=other.dataset.numberFormat==='grouped'?numberDisplay(value):value;}
  if(path==='discounts.mode'){for(const k of [...invalid.keys()])if(k.startsWith('discounts.allocations.'))invalid.delete(k);updateModeFeedback();}
 }
 updateErrors();render();
}
function reset(scope='all'){
 const d=initialState();
 if(scope==='discounts') {S.discounts=d.discounts;for(const k of [...invalid.keys()])if(k.startsWith('discounts.'))invalid.delete(k);}
 else if(scope==='vmr') {const discounts=clone(S.discounts);S={...d,discounts:{...discounts,reduction:d.discounts.reduction}};for(const k of [...invalid.keys()])if(!k.startsWith('discounts.')||k==='discounts.reduction')invalid.delete(k);}
 else{S=d;invalid.clear();}
 buildRefEditor();buildRegionEditor();buildDiscountInputs();buildBenchmarkEditor();fillInputs();updateModeFeedback();render();
 history.replaceState(null,'',location.pathname+location.hash);
 announce('Se restablecieron los valores base.');
}
function showTab(name,{focus=false,scroll=false}={}){
 if(!TABS.includes(name))name='calc';
 $$('.nav [data-tab]').forEach(b=>{const on=b.dataset.tab===name;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;if(on&&focus)b.focus();});
 TABS.forEach(t=>{$('#tab-'+t).hidden=t!==name;});
 $('#hero').hidden=name!=='calc';
 if(scroll)window.scrollTo({top:0,behavior:'smooth'});
}
function setupTabs(){
 const tabs=$$('.nav [data-tab]');
 tabs.forEach((b,i)=>{
  b.addEventListener('click',()=>{history.replaceState(null,'',location.pathname+location.search+'#'+b.dataset.tab);showTab(b.dataset.tab,{scroll:true});});
  b.addEventListener('keydown',e=>{const delta={'ArrowRight':1,'ArrowLeft':-1}[e.key];const j=delta!==undefined?(i+delta+tabs.length)%tabs.length:e.key==='Home'?0:e.key==='End'?tabs.length-1:null;if(j===null)return;e.preventDefault();history.replaceState(null,'',location.pathname+location.search+'#'+tabs[j].dataset.tab);showTab(tabs[j].dataset.tab,{focus:true});});
 });
 window.addEventListener('hashchange',()=>showTab(location.hash.slice(1)));
 showTab(location.hash.slice(1));
}
function download(kind){
 if(kind==='discounts'&&!discountResult||kind!=='discounts'&&!vmrResults){announce('Revise los parámetros antes de exportar.');return;}
 const rows=[['Calculadora VMR 5G','Versión 10 · Interfaz pública clásica'],['Datos fuente','Modelo de referencia'],['Parámetros_JSON',JSON.stringify(S)],[]];
 if(kind==='discounts'){
  const r=discountResult,d=S.discounts;
  rows.push(['Operador',d.operator],['Modalidad',d.mode],['Ampliacion_cobertura_pct',r.coverageProportion*100],['Modernizacion_pct',r.modernProportion*100],['Descuento_pct',d.percent],['Horizonte_años',d.years],['Reducción_general_pct',r.reduction*100],['Base_antes_reducción_MXN',r.base],['Base_anual_MXN',r.annualBase],['Descuento_anual_MXN',r.annualDiscount],['Descuento_total_MXN',r.amount],['Presupuesto_cobertura_MXN',r.coverageBudget],['Presupuesto_modernización_MXN',r.modernBudget],['Radiobases_cobertura',r.coverageBases],['Localidades',r.localities],['Habitantes_cobertura',r.coveragePopulation],['Radiobases_modernización',r.modernBases],['Habitantes_modernización',r.modernPopulation],['Costo_radiobase_cobertura_MXN',d.costCoverage],['Costo_radiobase_modernización_MXN',d.costModern],['Factor_modernización_pct',d.modernFactor]);
  rows.push([],['Tabla comparativa por porcentaje (montos en MXN; no valor presente)'],['Porcentaje_pct','Estado','Base_anual_MXN','Descuento_anual_MXN','Descuento_total_MXN','Monto_ampliacion_cobertura_MXN','Radiobases_ampliacion','Localidades','Habitantes_ampliacion','Monto_modernizacion_MXN','Radiobases_modernizacion','Habitantes_modernizacion']);
  for(let percent=10;percent<=100;percent+=10){
   const c=calculateDiscount({...d,percent});
   if(!c.available)rows.push([percent,'No aplica: '+c.reason]);
   else rows.push([percent,'Aplica',c.annualBase,c.annualDiscount,c.amount,c.coverageBudget,c.coverageBases,c.localities,c.coveragePopulation,c.modernBudget,c.modernBases,c.modernPopulation]);
  }
 }else{
  rows.push(['Banda','Región','MHz','Fuente','Población','Cobertura_pct','Proporción_LFD','VMR_MXN','Derechos_anuales_base_MXN','VP_derechos_base_MXN','Reducción_general_pct','Derechos_anuales_reducidos_MXN','VP_derechos_reducidos_MXN']);
  const rs=kind==='region'?[regionMode==='excel'?calculateVmr(initialState())[regionBand]:vmrResults[regionBand]]:vmrResults;
  for(const b of rs){for(const r of b.regions)rows.push([b.band,r.region,b.mhz,b.source,r.population,r.coverage*100,r.prop,r.vmr,r.rights,r.rightsPv,b.reduction*100,r.rightsNet,r.rightsNetPv]);rows.push([b.band,'Total',b.mhz,b.source,b.population,b.covered/b.population*100,b.coverageWeight,b.vmr,b.rights,b.rightsPv,b.reduction*100,b.rightsNet,b.rightsNetPv]);}
 }
 const blob=new Blob(['\ufeff'+rows.map(row=>row.map(csvCell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`crt_vmr_5g_${kind}.csv`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);announce('CSV generado.');
}
async function share(){
 if(invalid.size){announce('Corrija los campos marcados antes de compartir el escenario.');return;}
 const url=new URL(location.href);url.searchParams.set('s',encodeScenario(S));
 const el=location.hash==='#discounts'?'#discountCopyStatus':'#copyStatus';
 try{await navigator.clipboard.writeText(url.href);announce('Enlace copiado.',el);}catch{
  history.replaceState(null,'',url);announce('No se pudo copiar automáticamente; el enlace se colocó en la barra del navegador para copiarlo.',el);
 }
}
function syncStickyOffset(){const h=$('.site-header');if(h)document.documentElement.style.setProperty('--sticky-top',Math.ceil(h.getBoundingClientRect().height+16)+'px');}
const TAB_TITLES={calc:'Valor mínimo de referencia (VMR)',discounts:'Descuentos y obligaciones de despliegue',region:'Resultados por región',method:'Cómo se calcula el VMR',help:'Glosario y preguntas frecuentes'};
const SOURCE_LABEL={b:'Comparación internacional',n:'Referencia nacional'};
function currentTab(){return $('.nav [aria-selected="true"]')?.dataset.tab||'calc';}
function buildPrintHead(){
 const tab=currentTab(),mod=modelModified(),now=new Date();
 const item=(k,v)=>`<div><dt>${escape(k)}</dt><dd>${escape(v)}</dd></div>`;
 const vmrParams=()=>BANDS.map((b,i)=>item(b.label,`${N(Number(S.spectrum[i]),2)} MHz · ${i===0?SOURCE_LABEL.b:SOURCE_LABEL[S.source[i]]||'—'}`)).join('')
  +item('Vigencia',`${N(Number(S.years))} años`)+item('Tasa benchmark / derechos',`${N(Number(S.rateBenchmark),2)} % / ${N(Number(S.rateRights),2)} %`)
  +item('INPC base / actualización',`${N(Number(S.inpcBaseBenchmark),3)} / ${N(Number(S.inpcCurrent),3)}`)+item('Reducción general LFD',`${N(Number(S.discounts.reduction),2)} %`);
 let params='';
 if(tab==='calc'||tab==='method')params=vmrParams();
 else if(tab==='region')params=item('Banda',BANDS[regionBand].label)+item('Valores',regionMode==='excel'?'Valores base actualizados':'Mi escenario')+vmrParams();
 else if(tab==='discounts'){const d=S.discounts;params=item('Operador',d.operator)+item('Modalidad',d.mode)+item('Descuento',`${N(Number(d.percent))} %`)+item('Horizonte',`${N(Number(d.years))} años`)+item('Reducción general LFD',`${N(Number(d.reduction),2)} %`);}
 $('#printHead').innerHTML=`<div class="ph-top"><img src="assets/logo-crt.png" alt="Comisión Reguladora de Telecomunicaciones" width="857" height="193"><div class="ph-meta"><strong>Calculadora VMR 5G</strong><span>${now.toLocaleDateString('es-MX',{day:'2-digit',month:'long',year:'numeric'})} · ${now.toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'})}</span></div></div>
 <div class="ph-title"><h2>${escape(TAB_TITLES[tab])}</h2>${tab==='help'?'':`<span class="ph-state ${mod?'mod':''}">${mod?'Escenario modificado (simulación)':'Valores base del modelo 2026'}</span>`}</div>
 ${params?`<dl class="ph-params">${params}</dl>`:''}`;
}
let printOpened=[];
function setupPrint(){
 window.addEventListener('beforeprint',()=>{
  buildPrintHead();$('#printHead').hidden=false;
  printOpened=$$('#tab-help .faq:not([open])');printOpened.forEach(d=>d.open=true);
 });
 window.addEventListener('afterprint',()=>{$('#printHead').hidden=true;printOpened.forEach(d=>d.open=false);printOpened=[];});
}
function init(){
 syncStickyOffset();if('ResizeObserver' in window)new ResizeObserver(syncStickyOffset).observe($('.site-header'));
 window.addEventListener('resize',syncStickyOffset,{passive:true});
 const s=new URLSearchParams(location.search).get('s');
 if(s){try{S=decodeScenario(s);initMessage='Se cargó el escenario compartido.';}catch(e){initMessage=e.message+' Se muestran los valores base.';}}
 buildDiscountInputs();buildRegionEditor();buildRefEditor();buildBenchmarkEditor();fillInputs();updateModeFeedback();setupTabs();setupPrint();render();renderAudit();
 enhanceNumberInputs();
 new MutationObserver(()=>enhanceNumberInputs()).observe(document.querySelector('main'),{childList:true,subtree:true});
 document.addEventListener('input',e=>{if(e.target?.dataset?.modePart)changeModeRatio(e.target);else if(e.target?.dataset?.k&&e.target.tagName==='INPUT'&&e.target.type!=='checkbox')handleInput(e);});
 document.addEventListener('focusout',e=>{if(e.target?.dataset?.numberFormat==='grouped')formatOnBlur(e.target);});
 document.addEventListener('keydown',e=>{if(e.target?.dataset?.numberFormat==='grouped'&&!e.ctrlKey&&!e.altKey&&!e.metaKey&&(e.key==='ArrowUp'||e.key==='ArrowDown')){e.preventDefault();changeNumberStep(e.target,e.key==='ArrowUp'?1:-1);}});
 document.addEventListener('change',e=>{if(e.target?.dataset?.k&&(e.target.tagName==='SELECT'||e.target.type==='checkbox'))handleInput(e);});
 document.addEventListener('click',e=>{
  const step=e.target.closest('[data-step-dir]');if(step){changeNumberStep(step.closest('.input-wrap,.number-table-control')?.querySelector('input[data-number-format="grouped"]'),Number(step.dataset.stepDir));return;}
  const act=e.target.closest('[data-action]');
  if(act){switch(act.dataset.action){case 'reset':reset();break;case 'reset-vmr':reset('vmr');break;case 'reset-discounts':reset('discounts');break;case 'print':window.print();break;case 'share':share();break;case 'csv-discounts':download('discounts');break;case 'csv-vmr':download('vmr');break;}}
  const pct=e.target.closest('[data-select-discount]');
  if(pct&&!pct.disabled){S.discounts.percent=Number(pct.dataset.selectDiscount);invalid.delete('discounts.percent');const sel=$('[data-k="discounts.percent"]');if(sel)sel.value=String(S.discounts.percent);updateErrors();render();announce(`Descuento de ${S.discounts.percent} % aplicado a las tarjetas de resultados.`);}
  const go=e.target.closest('[data-goto]');if(go){const name=go.dataset.goto;history.replaceState(null,'',location.pathname+location.search+'#'+name);showTab(name,{scroll:true});}
 });
 $('#cards').addEventListener('toggle',e=>{if(e.target.matches('details[data-card]'))openCards[Number(e.target.dataset.card)]=e.target.open;},true);
 $('#bandSelector').addEventListener('click',e=>{const b=e.target.closest('[data-band]');if(b){regionBand=Number(b.dataset.band);renderRegion();}});
 $('#modeSelector').addEventListener('click',e=>{const b=e.target.closest('[data-mode]');if(b){regionMode=b.dataset.mode;renderRegion();}});
 $('#benchmarkFilter').addEventListener('change',buildBenchmarkEditor);
 setupHelpSearch();
 $('#print').addEventListener('click',()=>window.print());
 $('#csv').addEventListener('click',()=>download('region'));
 $('#copyLink').addEventListener('click',share);
 if(initMessage)announce(initMessage);
}
function setupHelpSearch(){
 const input=$('#helpSearch');if(!input)return;
 const norm=t=>t.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 const items=[...$$('#tab-help .gterm'),...$$('#tab-help .faq')];
 input.addEventListener('input',()=>{
  const q=norm(input.value.trim());let shown=0;
  items.forEach(el=>{const hit=!q||norm(el.textContent).includes(q);el.hidden=!hit;if(hit)shown++;if(q&&hit&&el.tagName==='DETAILS'&&q.length>2)el.open=true;});
  $('#gloss-h').hidden=!$$('#tab-help .gterm').some(e=>!e.hidden);
  $('#faq-h').hidden=!$$('#tab-help .faq').some(e=>!e.hidden);
  $('#helpEmpty').hidden=shown>0;
 });
}
init();
