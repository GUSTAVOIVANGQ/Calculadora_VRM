import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const ui=readFileSync(new URL('../assets/ui.js',import.meta.url),'utf8');
const from=ui.indexOf('function numberDisplay('), to=ui.indexOf('const TABS =');
assert.ok(from>=0&&to>from);
const {numberDisplay,groupNumberString,parseNumberInput,formatWhileTyping,changeNumberStep}=new Function(ui.slice(from,to)+'\nreturn {numberDisplay,groupNumberString,parseNumberInput,formatWhileTyping,changeNumberStep};')();
test('Números: comas de miles, punto decimal y precisión original',()=>{
 assert.equal(numberDisplay(16889342.82),'16,889,342.82');
 assert.equal(numberDisplay(5135745),'5,135,745');
 assert.equal(groupNumberString('12345.600'),'12,345.600');
 assert.equal(groupNumberString('1200.'),'1,200.');
 assert.equal(groupNumberString('.25'),'.25');
 assert.equal(groupNumberString('-123456.75'),'-123,456.75');
});
test('Los campos con separadores vuelven a su valor numérico sin alterar el cálculo',()=>{
 assert.equal(parseNumberInput('1,234,567.89'),1234567.89);
 assert.equal(parseNumberInput('12,345,678'),12345678);
 assert.equal(parseNumberInput('12.50'),12.5);
 assert.equal(parseNumberInput(''),null);
 assert.ok(Number.isNaN(parseNumberInput('no es número')));
 assert.ok(Number.isNaN(parseNumberInput('1.2.3')));
});
test('El cursor se conserva después de insertar comas durante la edición',()=>{
 const input={value:'1234.5',selectionStart:4,selectionEnd:4,setSelectionRange(start,end){this.selectionStart=start;this.selectionEnd=end;}};
 formatWhileTyping(input);
 assert.equal(input.value,'1,234.5');
 assert.equal(input.selectionStart,5);
});

test('Flechas: incrementan 0.01 en MXN con decimales y respetan límites',()=>{
 const attrs={min:'0',max:'10000',step:'any'};
 let events=0;
 const field={value:'1,234.56',getAttribute:k=>attrs[k]??null,dispatchEvent(){events++;},focus(){}};
 changeNumberStep(field,1);
 assert.equal(field.value,'1,234.57');
 changeNumberStep(field,-1);
 assert.equal(field.value,'1,234.56');
 assert.equal(events,2);
 field.value='10,000';changeNumberStep(field,1);
 assert.equal(field.value,'10,000');
 assert.equal(events,2);
});
test('Flechas: incrementos enteros, números vacíos y límite mínimo',()=>{
 const attrs={min:'0',max:'100',step:'1'};
 let events=0;
 const field={value:'50',getAttribute:k=>attrs[k]??null,dispatchEvent(){events++;},focus(){}};
 changeNumberStep(field,1);assert.equal(field.value,'51');
 field.value='0';changeNumberStep(field,-1);assert.equal(field.value,'0');
 field.value='';changeNumberStep(field,1);assert.equal(field.value,'1');
 assert.equal(events,2);
});
