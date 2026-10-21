import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {initialState,calculateVmr,calculateDiscount,pv,encodeScenario,decodeScenario,validateScenario,clone,inputError} from '../assets/model.js';
const controls=JSON.parse(fs.readFileSync(new URL('./excel-controls.json',import.meta.url),'utf8'));
const close=(actual,expected)=>assert.ok(Math.abs(actual-expected)<Math.max(0.001,Math.abs(expected)*1e-10),`${actual} ≠ ${expected}`);
test('VMR, annual rights, PV, medians and all 27 regional VMRs match the simplified workbook',()=>{
  const result=calculateVmr(initialState());
  for(let i=0;i<3;i++){close(result[i].vmr,controls.vmr[i]);close(result[i].rights,controls.rights[i]);close(result[i].rightsPv,controls.rightsPv[i]);close(result[i].median,controls.medians[i]);result[i].regions.forEach((r,k)=>close(r.vmr,controls.regions[i][k]));}
});
test('All 90 source discount scenarios match the received Excel',()=>{
 for(const c of controls.discounts){const d={...initialState().discounts,operator:c.operator,mode:c.mode,percent:c.percent};const r=calculateDiscount(d);assert.equal(r.available,true);for(const key of ['amount','localities','coveragePopulation','modernBases','modernPopulation'])close(r[key],c[key]);}
});
test('600 MHz excluded from general reduction; 800 and 2.5 rights decrease 12%',()=>{const r=calculateVmr(initialState());close(r[0].rightsNet,r[0].rights);for(const i of[1,2])close(r[i].rightsNet,r[i].rights*.88);});
test('Discounts do not alter VMR or benchmark-rights subtraction',()=>{const s=initialState(),before=calculateVmr(s);s.discounts.reduction=50;const after=calculateVmr(s);after.forEach((r,i)=>{close(r.vmr,before[i].vmr);close(r.b,before[i].b);});});
test('Zero rate, zero spectrum, zero coverage, later-region edits and alternative reference recalculate',()=>{
 close(pv(0,20,10,true),200);const s=initialState();s.rateBenchmark=0;s.rateRights=0;assert.ok(calculateVmr(s).every(r=>Number.isFinite(r.vmr)));s.spectrum[0]=0;close(calculateVmr(s)[0].vmr,0);close(calculateVmr(s)[0].rights,0);
 const z=initialState();z.coverage[1].fill(0);close(calculateVmr(z)[1].vmr,0);const p=initialState(),before=calculateVmr(p)[1].vmr;p.coverage[1][8]=100;assert.ok(calculateVmr(p)[1].vmr>before);p.source[1]='n';close(calculateVmr(p)[1].mp,calculateVmr(p)[1].national);
});
test('Missing/invalid source coverage is exposed rather than reported as zero',()=>{
 const s=initialState();s.population.fill(0);assert.throws(()=>calculateVmr(s),/población/);const q=initialState();q.q.q800.fill(0);assert.throws(()=>calculateVmr(q),/cuotas/);const b=initialState();b.benchmarkIncluded.fill(false);assert.throws(()=>calculateVmr(b),/observación/);
});
test('Benchmark inclusion changes the live median',()=>{const s=initialState(),before=calculateVmr(s)[0].median;const selected=s.benchmarkIncluded.map((x,i)=>i).filter(i=>i<30);for(const i of selected.slice(1))s.benchmarkIncluded[i]=false;assert.notEqual(calculateVmr(s)[0].median,before);});
test('Discount boundaries, unsupported modes, zero reduction and cost changes',()=>{
 const d=initialState().discounts;assert.throws(()=>calculateDiscount({...d,percent:0}));assert.throws(()=>calculateDiscount({...d,percent:15}));assert.equal(calculateDiscount({...d,percent:60}).available,false);assert.equal(calculateDiscount({...d,operator:'Operador C',mode:'Modernización'}).available,false);
 assert.ok(calculateDiscount({...d,costCoverage:d.costCoverage*2}).localities<calculateDiscount(d).localities);close(calculateDiscount({...d,reduction:100}).amount,0);assert.throws(()=>calculateDiscount({...d,costCoverage:0}));assert.throws(()=>calculateDiscount({...d,percent:null}));
});
test('Scenario links round-trip including benchmark choices, references and discounts',()=>{
 const s=initialState();s.source[1]='n';s.benchmarkIncluded[10]=false;s.references[3].amount=450000000;s.discounts.mode='Mixto 10/90';s.discounts.operator='Operador E';s.discounts.percent=100;assert.deepEqual(decodeScenario(encodeScenario(s)),s);
});
test('Malformed links, NaN, null numbers, unknown operators and unsafe payloads are rejected',()=>{
 assert.throws(()=>decodeScenario('invalid'));const s=initialState();s.rateBenchmark=null;assert.throws(()=>validateScenario(s));s.rateBenchmark=Infinity;assert.throws(()=>validateScenario(s));s.rateBenchmark=10;s.discounts.operator='<img src=x onerror=alert(1)>';assert.throws(()=>validateScenario(s));assert.throws(()=>decodeScenario('x'.repeat(30001)));
});
test('Rates accept 0 to 100 inclusive; years follow workbook 1 to 50',()=>{
 for(const v of [0,10.11,99,100])assert.equal(inputError('rateRights',v),'');assert.notEqual(inputError('rateRights',101),'');assert.notEqual(inputError('years',51),'');assert.notEqual(inputError('years',1.5),'');
});
test('INPC must be strictly positive and reference bands cannot be changed through a link',()=>{
 assert.notEqual(inputError('inpcBaseBenchmark',0),'');assert.notEqual(inputError('references.0.baseInpc',0),'');const s=initialState();s.references[0].band=1;assert.throws(()=>validateScenario(s));
});
test('Custom modality distribution updates budgets, remains complementary, and preserves original benchmark controls',()=>{
 const d=initialState().discounts;
 const original=calculateDiscount(d);
 d.allocations[0]=65.5;
 const edited=calculateDiscount(d);
 close(edited.amount,original.amount);
 close(edited.coverageBudget,edited.amount*.655);
 close(edited.modernBudget,edited.amount*.345);
 close(edited.coverageBudget+edited.modernBudget,edited.amount);
 assert.notEqual(edited.coverageBases,original.coverageBases);
 assert.ok(edited.modernBases>0);
 const s=initialState();s.discounts.allocations[0]=65.5;
 assert.deepEqual(decodeScenario(encodeScenario(s)),s);
 const bad=clone(s);bad.discounts.allocations[0]=110;
 assert.throws(()=>validateScenario(bad));
});
test('Legacy shared scenario links without custom proportions remain readable',()=>{
 const s=initialState();delete s.discounts.allocations;
 const bytes=Buffer.from(JSON.stringify({version:4,state:s}));
 const link=bytes.toString('base64url');
 const restored=decodeScenario(link);
 assert.deepEqual(restored.discounts.allocations,[100,0,50,10]);
});
test('Custom modality percentages require zero to two decimals',()=>{
 assert.equal(inputError('discounts.allocations.0',65.5),'');
 assert.equal(inputError('discounts.allocations.2',65.55),'');
 assert.ok(inputError('discounts.allocations.0',65.555));
 assert.ok(inputError('discounts.allocations.0',101));
});
