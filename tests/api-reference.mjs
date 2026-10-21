import {initialState,calculateVmr,calculateDiscount} from '../assets/model.js';
const result=[];
for(const [op,mode,pct,coverage] of [
 ['Telcel','Cobertura',10,100],['AT&T','Modernización',30,0],['Operador C','Mixto 10/90',60,10],
 ['Operador D','Cobertura',80,100],['Operador E','Mixto 10/90',100,12.5],['Telcel','Híbrido 50/50',50,75]]){
 const s=initialState(),i=s.discounts.allocations.findIndex((_,j)=>['Cobertura','Modernización','Híbrido 50/50','Mixto 10/90'][j]===mode);
 s.discounts.operator=op;s.discounts.mode=mode;s.discounts.percent=pct;s.discounts.allocations[i]=coverage;
 s.spectrum=[36,22,15];s.years=25;s.rateRights=10.42;
 result.push({overrides:{spectrum:s.spectrum,years:s.years,rateRights:s.rateRights,discounts:{operator:op,mode,percent:pct,allocations:s.discounts.allocations}},vmr:calculateVmr(s),discount:calculateDiscount(s.discounts)});
}
console.log(JSON.stringify(result));
