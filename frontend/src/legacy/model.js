import { DATA } from './data.js';
export const BANDS = [
  {label:'600 MHz',key:'q600',color:'#7d3f56'},
  {label:'800 MHz',key:'q800',color:'#8b681d'},
  {label:'2.5 GHz',key:'q25',color:'#3f7779'}
];
export const clone = value => structuredClone(value);
export const initialState = () => ({...clone(DATA.base),discounts:{...clone(DATA.discounts),allocations:DATA.modes.map(m=>m.coverage*100)}});
export const sum = values => values.reduce((a,b)=>a+b,0);
export function excelRound(value,digits=0) {const p=10**digits;return Math.sign(value)*Math.floor(Math.abs(value)*p+0.5+1e-12)/p;}
export function pv(rate,years,payment,due=false) {
  if(![rate,years,payment].every(Number.isFinite)||rate<0||years<0)throw new Error('Parámetros de valor presente no válidos.');
  const factor=rate===0?years:-Math.expm1(-years*Math.log1p(rate))/rate;
  return payment*factor*(due?1+rate:1);
}
export function median(values) {
  if(!values.length)throw new Error('Seleccione al menos una observación del benchmark por banda.');
  const a=[...values].sort((x,y)=>x-y),m=Math.floor(a.length/2);
  return a.length%2?a[m]:(a[m-1]+a[m])/2;
}
export function inputError(path,value) {
  if(value===null||value===undefined||value==='')return 'Este campo es obligatorio.';
  if(typeof value!=='number'||!Number.isFinite(value))return 'Ingrese un número válido.';
  if(Math.abs(value)>Number.MAX_SAFE_INTEGER)return 'El valor excede la precisión numérica admitida.';
  if(['rateBenchmark','rateRights','discounts.reduction','discounts.rangeFactor'].includes(path))return value<0||value>100?'Ingrese un porcentaje entre 0% y 100%.':'';
  if(path==='years'||path==='discounts.years')return !Number.isInteger(value)||value<1||value>50?'Ingrese años enteros entre 1 y 50.':'';
  if(path.startsWith('coverage.'))return value<0||value>100?'Ingrese una cobertura entre 0% y 100%.':'';
  if(/^discounts\.allocations\.\d+$/.test(path))return value<0||value>100?'Ingrese una distribución entre 0% y 100%.':Math.abs(value*100-Math.round(value*100))>1e-7?'Utilice como máximo dos decimales.':'';
  if(path==='discounts.percent')return value<10||value>100||value%10!==0?'Elija un descuento de 10% en 10%.':'';
  if(path.startsWith('population.'))return value<0||!Number.isInteger(value)?'Ingrese un número entero de habitantes mayor o igual a cero.':'';
  if(path.includes('Inpc')||path.startsWith('inpc')||path==='discounts.costCoverage'||path==='discounts.costModern'||path==='discounts.modernFactor')return value<=0||path==='discounts.modernFactor'&&value>100?'Ingrese un valor mayor que cero'+(path==='discounts.modernFactor'?' y hasta 100%.':'.'):'';
  if(path.startsWith('spectrum.')||path.startsWith('q.')||/^references\.\d+\.amount$/.test(path)||/^discounts\.(rights|minimum|maximum)\./.test(path))return value<0?'El valor debe ser mayor o igual a cero.':'';
  if(/^references\.\d+\.spectrum$/.test(path))return value<=0?'El espectro ponderado debe ser mayor que cero.':'';
  if(['discounts.localitiesPerBase','discounts.populationPerLocality','discounts.populationPerModern'].includes(path))return !Number.isInteger(value)||value<1?'Ingrese un número entero mayor que cero.':'';
  return value<0?'El valor debe ser mayor o igual a cero.':'';
}
export function getPath(state,path){return path.split('.').reduce((x,k)=>x?.[k],state);}
export function setPath(state,path,value){
  const parts=path.split('.');
  if(parts.some(x=>['__proto__','prototype','constructor'].includes(x)))throw new Error('Campo no permitido.');
  const key=parts.pop(),parent=parts.reduce((x,k)=>x[k],state);parent[key]=value;
}
export function validateScenario(candidate) {
  if(!candidate||typeof candidate!=='object'||Array.isArray(candidate))throw new Error('Enlace de escenario no válido.');
  const result=initialState();
  function copy(target,input,prefix='') {
    for(const key of Object.keys(target)){
      const path=prefix?`${prefix}.${key}`:key;
      // Los enlaces compartidos de la versión anterior no incluían proporciones personalizables.
      if(!(key in input)&&path==='discounts.allocations')continue;
      if(!(key in input))throw new Error('El enlace pertenece a otra versión o le faltan parámetros.');
      const value=input[key];
      if(target[key]!==null&&typeof target[key]==='object'){
        if(!value||typeof value!=='object'||Array.isArray(target[key])!==Array.isArray(value)||Array.isArray(value)&&value.length!==target[key].length)throw new Error('Estructura del escenario no válida.');
        copy(target[key],value,path);
      } else if(typeof target[key]==='number') {
        if(/^references\.\d+\.band$/.test(path)&&value!==target[key])throw new Error('La banda de una licitación no se puede cambiar.');
        const err=inputError(path,value);if(err)throw new Error(`${path}: ${err}`);target[key]=value;
      } else if(typeof target[key]==='boolean') {
        if(typeof value!=='boolean')throw new Error('Selección de benchmark no válida.');target[key]=value;
      } else {
        let allowed=[target[key]];
        if(/^source\.[12]$/.test(path))allowed=['b','n'];
        if(path==='discounts.operator')allowed=DATA.operators;
        if(path==='discounts.mode')allowed=DATA.modes.map(x=>x.name);
        if(!allowed.includes(value))throw new Error('Selección del escenario no válida.');target[key]=value;
      }
    }
  }
  copy(result,candidate);return result;
}
export function calculateVmr(state) {
  const population=sum(state.population);
  if(!(population>0))throw new Error('La población nacional debe ser mayor que cero.');
  const factor=excelRound(state.inpcCurrent/state.inpcBaseBenchmark,4);
  return BANDS.map((band,i)=>{
    const quota=state.q[band.key],quotaTotal=sum(quota);
    if(!(quotaTotal>0))throw new Error(`La suma de cuotas LFD de ${band.label} debe ser mayor que cero.`);
    const observations=DATA.benchmarks.filter((x,j)=>x.band===band.label&&state.benchmarkIncluded[j]).map(x=>x.value);
    const m=median(observations);
    const a=pv(state.rateBenchmark/100,state.years,m);
    const b=pv(state.rateRights/100,state.years,quotaTotal*1000,true)/population;
    const benchmark=(a-b)*factor;
    let national=null;
    if(i>0){const refs=state.references.filter(x=>x.band===i);national=sum(refs.map(x=>x.amount*excelRound(state.inpcCurrent/x.baseInpc,4)))/sum(refs.map(x=>x.spectrum))/119530753;}
    const mp=state.source[i]==='n'?national:benchmark;
    const reduction=i===0?0:state.discounts.reduction/100;
    const regions=quota.map((q,k)=>{
      const coverage=state.coverage[i][k]/100,prop=q/quotaTotal;
      const rights=state.spectrum[i]*1000*q*coverage;
      return {region:k+1,population:state.population[k],coverage,prop,vmr:population*state.spectrum[i]*mp*prop*coverage,rights,rightsPv:pv(state.rateRights/100,state.years,rights,true),rightsNet:rights*(1-reduction),rightsNetPv:pv(state.rateRights/100,state.years,rights*(1-reduction),true)};
    });
    const vmr=sum(regions.map(x=>x.vmr)),rights=sum(regions.map(x=>x.rights)),rightsPv=sum(regions.map(x=>x.rightsPv)),rightsNet=sum(regions.map(x=>x.rightsNet)),rightsNetPv=sum(regions.map(x=>x.rightsNetPv));
    const result={band:band.label,i,vmr,rights,rightsPv,rightsNet,rightsNetPv,reduction,saving:rights-rightsNet,population,covered:sum(regions.map(x=>x.population*x.coverage)),coverageWeight:sum(regions.map(x=>x.prop*x.coverage)),mhz:state.spectrum[i],mp,median:m,observations:observations.length,a,b,factor,benchmark,national,source:state.source[i],regions};
    if(Object.values(result).some(x=>typeof x==='number'&&!Number.isFinite(x)))throw new Error('Los parámetros generan un resultado fuera del rango numérico.');
    return result;
  });
}
export function calculateDiscount(d) {
  const index=DATA.operators.indexOf(d.operator),mode=DATA.modes.find(x=>x.name===d.mode);
  if(index<0||!mode)throw new Error('Seleccione operador y modalidad.');
  for(const key of ['percent','reduction','years','costCoverage','costModern','modernFactor','localitiesPerBase','populationPerLocality','populationPerModern','rangeFactor']){
    const err=inputError(`discounts.${key}`,d[key]);if(err)throw new Error(err);
  }
  if(d.percent>DATA.discountMaximum[index])return {available:false,reason:`El descuento máximo del tipo ${'ABCDE'[index]} es ${DATA.discountMaximum[index]}%.`};
  if(index>1&&!mode.allOperators)return {available:false,reason:'Esta modalidad solo está disponible para los tipos A y B. Para C/D/E, elija Cobertura o Mixto 10/90.'};
  if(d.minimum[index]>d.maximum[index]&&index>1)throw new Error('El mínimo del rango no puede superar al máximo.');
  const selectedMode=DATA.modes.findIndex(m=>m.name===d.mode);
  const customCoverage=d.allocations?.[selectedMode]??mode.coverage*100;
  const allocationError=inputError(`discounts.allocations.${selectedMode}`,customCoverage);
  if(allocationError)throw new Error(allocationError);
  const coverageShare=customCoverage/100;
  const base=index<2?d.rights[index]:(d.minimum[index]+d.maximum[index])/2*d.rangeFactor/100;
  const reduction=index<2?d.reduction/100:0;
  const annualBase=base*(1-reduction),annualDiscount=annualBase*d.percent/100,amount=annualDiscount*d.years;
  const coverageBudget=amount*coverageShare,modernBudget=amount*(1-coverageShare);
  const coverageBases=Math.ceil(coverageBudget/d.costCoverage),localities=coverageBases*d.localitiesPerBase,coveragePopulation=localities*d.populationPerLocality;
  const modernBases=Math.ceil(modernBudget/(d.costModern*d.modernFactor/100)),modernPopulation=modernBases*d.populationPerModern;
  const result={available:true,index,base,reduction,annualBase,annualDiscount,amount,coverageBudget,modernBudget,coverageBases,localities,coveragePopulation,modernBases,modernPopulation,coverageProportion:coverageShare,modernProportion:1-coverageShare};
  if(Object.values(result).some(x=>typeof x==='number'&&!Number.isFinite(x)))throw new Error('El escenario excede el rango numérico.');
  return result;
}
export function encodeScenario(state){const bytes=new TextEncoder().encode(JSON.stringify({version:5,state}));return btoa(Array.from(bytes,x=>String.fromCharCode(x)).join('')).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');}
export function decodeScenario(text){
  if(text.length>30000)throw new Error('El enlace de escenario es demasiado largo.');
  const s=text.replaceAll('-','+').replaceAll('_','/');const bytes=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const envelope=JSON.parse(new TextDecoder().decode(bytes));
  if(![4,5].includes(envelope.version))throw new Error('El enlace pertenece a otra versión. Se cargaron los valores base.');return validateScenario(envelope.state);
}
export function csvCell(value){let text=String(value);if(/^[=+@\-\t\r]/.test(text)&&typeof value!=='number')text="'"+text;return '"'+text.replaceAll('"','""')+'"';}
