"""API JSON de VMR y descuentos. Solo stdlib; mismas fórmulas del modelo JS.

Los datos fuente se leen de assets/data.js (JSON literal), evitando una segunda
copia susceptible de quedarse desactualizada. No se exponen datos de login.
"""
import copy
import json
import math
import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / 'assets' / 'data.js'
raw = SOURCE.read_text(encoding='utf-8').strip()
if not raw.startswith('export const DATA = ') or not raw.endswith(';'):
    raise RuntimeError('Formato de datos fuente inesperado')
DATA = json.loads(raw[len('export const DATA = '):-1])
BANDS = [('600 MHz', 'q600'), ('800 MHz', 'q800'), ('2.5 GHz', 'q25')]


class BadScenario(ValueError):
    pass


def defaults():
    base = copy.deepcopy(DATA['base'])
    base['discounts'] = copy.deepcopy(DATA['discounts'])
    base['discounts']['allocations'] = [m['coverage']*100 for m in DATA['modes']]
    return base


def input_error(path, value):
    if not isinstance(value, (float, int)) or isinstance(value, bool) or not math.isfinite(value):
        return 'Se requiere un número finito.'
    if abs(value) > (2**53 - 1):
        return 'El valor excede la precisión numérica admitida.'
    if path in ('rateBenchmark', 'rateRights', 'discounts.reduction', 'discounts.rangeFactor'):
        return 'Porcentaje fuera de 0 a 100.' if value < 0 or value > 100 else ''
    if path in ('years', 'discounts.years'):
        return 'Años fuera de 1 a 50 o no enteros.' if value < 1 or value > 50 or not float(value).is_integer() else ''
    if path.startswith('coverage.'):
        return 'Cobertura fuera de 0 a 100.' if value < 0 or value > 100 else ''
    if re.fullmatch(r'discounts\.allocations\.\d+', path):
        return 'Distribución fuera de 0 a 100 o con más de dos decimales.' if value < 0 or value > 100 or abs(value*100-round(value*100)) > 1e-7 else ''
    if path == 'discounts.percent':
        return 'El porcentaje debe aumentar de 10 en 10, de 10 a 100.' if value < 10 or value > 100 or value % 10 else ''
    if path.startswith('population.'):
        return 'Población no válida.' if value < 0 or not float(value).is_integer() else ''
    if 'Inpc' in path or path.startswith('inpc') or path in ('discounts.costCoverage', 'discounts.costModern', 'discounts.modernFactor'):
        return 'Se requiere un valor positivo válido.' if value <= 0 or path == 'discounts.modernFactor' and value > 100 else ''
    if path.startswith('spectrum.') or path.startswith('q.') or re.fullmatch(r'references\.\d+\.amount', path) or re.fullmatch(r'discounts\.(rights|minimum|maximum)\.\d+', path):
        return 'Se requiere un valor no negativo.' if value < 0 else ''
    if re.fullmatch(r'references\.\d+\.spectrum', path):
        return 'El espectro debe ser positivo.' if value <= 0 else ''
    if path in ('discounts.localitiesPerBase', 'discounts.populationPerLocality', 'discounts.populationPerModern'):
        return 'Se requiere un entero positivo.' if value < 1 or not float(value).is_integer() else ''
    return 'Se requiere un valor no negativo.' if value < 0 else ''


def validate_merge(overrides):
    if overrides is None:
        return defaults()
    if not isinstance(overrides, dict):
        raise BadScenario('El escenario debe ser un objeto JSON.')
    state = defaults()

    def merge(target, source, prefix=''):
        if not isinstance(source, dict) or not isinstance(target, dict):
            raise BadScenario(f'{prefix or "escenario"}: estructura inválida.')
        for key, value in source.items():
            if key not in target or key in ('__proto__', 'prototype', 'constructor'):
                raise BadScenario(f'{prefix}.{key}: parámetro desconocido.')
            path = f'{prefix}.{key}' if prefix else key
            orig = target[key]
            if isinstance(orig, dict):
                merge(orig, value, path)
            elif isinstance(orig, list):
                if not isinstance(value, list) or len(value) != len(orig):
                    raise BadScenario(f'{path}: el arreglo tiene longitud incorrecta.')
                for j, item in enumerate(value):
                    if isinstance(orig[j], dict):
                        merge(orig[j], item, f'{path}.{j}')
                    else:
                        orig[j] = validate_primitive(f'{path}.{j}', orig[j], item)
            else:
                target[key] = validate_primitive(path, orig, value)

    def validate_primitive(path, orig, value):
        if isinstance(orig, bool):
            if not isinstance(value, bool):
                raise BadScenario(f'{path}: se requiere un valor booleano.')
        elif isinstance(orig, (int, float)):
            err = input_error(path, value)
            if err:
                raise BadScenario(f'{path}: {err}')
        elif isinstance(orig, str):
            if not isinstance(value, str):
                raise BadScenario(f'{path}: se requiere texto.')
            if re.fullmatch(r'references\.\d+\.label', path) and value != orig:
                raise BadScenario(f'{path}: no se permite modificar la referencia.')
            if re.fullmatch(r'source\.[12]', path) and value not in ('b', 'n'):
                raise BadScenario(f'{path}: fuente no válida.')
            if path == 'discounts.operator' and value not in DATA['operators']:
                raise BadScenario('Operador no válido.')
            if path == 'discounts.mode' and value not in [m['name'] for m in DATA['modes']]:
                raise BadScenario('Modalidad no válida.')
            if path not in ('discounts.operator', 'discounts.mode') and not re.fullmatch(r'source\.[12]', path) and value != orig:
                raise BadScenario(f'{path}: texto no editable.')
        if re.fullmatch(r'references\.\d+\.band', path) and value != orig:
            raise BadScenario(f'{path}: la banda no es editable.')
        return value

    merge(state, overrides)
    if sum(state['population']) <= 0:
        raise BadScenario('La población nacional debe ser positiva.')
    for label, _ in BANDS:
        if not any(row['band'] == label and checked for row, checked in zip(DATA['benchmarks'], state['benchmarkIncluded'])):
            raise BadScenario(f'Seleccione alguna observación de benchmark para {label}.')
    return state


def excel_round(value, digits=0):
    p = 10**digits
    return math.copysign(math.floor(abs(value)*p + 0.5 + 1e-12)/p, value)


def pv(rate, years, payment, due=False):
    if rate < 0 or years < 0 or not all(math.isfinite(v) for v in (rate, years, payment)):
        raise BadScenario('Parámetros de valor presente no válidos.')
    factor = years if rate == 0 else -math.expm1(-years * math.log1p(rate))/rate
    return payment*factor*(1+rate if due else 1)


def median(values):
    values = sorted(values)
    if not values:
        raise BadScenario('El benchmark no tiene observaciones.')
    m = len(values)//2
    return values[m] if len(values)%2 else (values[m-1]+values[m])/2


def calculate_vmr(state):
    population = sum(state['population'])
    factor = excel_round(state['inpcCurrent']/state['inpcBaseBenchmark'], 4)
    output=[]
    for i, (label,key) in enumerate(BANDS):
        quota = state['q'][key]
        quota_total = sum(quota)
        if quota_total <= 0:
            raise BadScenario(f'Cuotas LFD de {label}: la suma debe ser positiva.')
        observations = [x['value'] for j,x in enumerate(DATA['benchmarks'])
                        if x['band'] == label and state['benchmarkIncluded'][j]]
        m = median(observations)
        a = pv(state['rateBenchmark']/100, state['years'], m)
        b = pv(state['rateRights']/100, state['years'], quota_total*1000, True)/population
        benchmark = (a-b)*factor
        national = None
        if i > 0:
            refs = [r for r in state['references'] if r['band'] == i]
            denominator = sum(r['spectrum'] for r in refs)
            if not denominator:
                raise BadScenario('El espectro ponderado nacional debe ser positivo.')
            national = sum(r['amount']*excel_round(state['inpcCurrent']/r['baseInpc'],4) for r in refs)/denominator/119530753
        mp = national if state['source'][i] == 'n' else benchmark
        reduction = 0 if i == 0 else state['discounts']['reduction']/100
        regions=[]
        for k,q in enumerate(quota):
            coverage = state['coverage'][i][k]/100
            prop = q/quota_total
            rights = state['spectrum'][i]*1000*q*coverage
            regions.append({
                'region':k+1, 'population':state['population'][k], 'coverage':coverage, 'prop':prop,
                'vmr':population*state['spectrum'][i]*mp*prop*coverage,
                'rights':rights, 'rightsPv':pv(state['rateRights']/100, state['years'],rights,True),
                'rightsNet':rights*(1-reduction),
                'rightsNetPv':pv(state['rateRights']/100,state['years'],rights*(1-reduction),True)
            })
        res = {'band':label,'i':i,'reduction':reduction,'population':population,
               'covered':sum(x['population']*x['coverage'] for x in regions),
               'coverageWeight':sum(x['prop']*x['coverage'] for x in regions),
               'mhz':state['spectrum'][i], 'mp':mp, 'median':m, 'observations':len(observations),
               'a':a,'b':b,'factor':factor,'benchmark':benchmark,'national':national,
               'source':state['source'][i], 'regions':regions}
        for k in ('vmr','rights','rightsPv','rightsNet','rightsNetPv'):
            res[k] = sum(r[k] for r in regions)
        res['saving'] = res['rights']-res['rightsNet']
        output.append(res)
    return output


def calculate_discount(d):
    index = DATA['operators'].index(d['operator'])
    mode_index = next(i for i,x in enumerate(DATA['modes']) if x['name'] == d['mode'])
    mode = DATA['modes'][mode_index]
    limit = DATA['discountMaximum'][index]
    if d['percent'] > limit:
        return {'available':False, 'reason':f"El descuento máximo del tipo {'ABCDE'[index]} es {limit}%."}
    if index > 1 and not mode['allOperators']:
        return {'available':False,'reason':'Esta modalidad solo está disponible para los tipos A y B. Para C/D/E, elija Cobertura o Mixto 10/90.'}
    if index > 1 and d['minimum'][index] > d['maximum'][index]:
        raise BadScenario('El mínimo del rango no puede superar al máximo.')
    coverage_share = d['allocations'][mode_index]/100
    base = d['rights'][index] if index<2 else (d['minimum'][index]+d['maximum'][index])/2 * d['rangeFactor']/100
    reduction = d['reduction']/100 if index<2 else 0
    annual_base = base*(1-reduction)
    annual_discount = annual_base*d['percent']/100
    amount = annual_discount*d['years']
    coverage_budget = amount*coverage_share
    modern_budget = amount*(1-coverage_share)
    coverage_bases = math.ceil(coverage_budget/d['costCoverage'])
    localities = coverage_bases*d['localitiesPerBase']
    modern_bases = math.ceil(modern_budget/(d['costModern']*d['modernFactor']/100))
    result = {'available':True,'index':index,'base':base,'reduction':reduction,
              'annualBase':annual_base,'annualDiscount':annual_discount,'amount':amount,
              'coverageBudget':coverage_budget,'modernBudget':modern_budget,
              'coverageBases':coverage_bases, 'localities':localities,
              'coveragePopulation':localities*d['populationPerLocality'],
              'modernBases':modern_bases, 'modernPopulation':modern_bases*d['populationPerModern'],
              'coverageProportion':coverage_share,'modernProportion':1-coverage_share}
    return result


def response(endpoint, payload=None):
    """Return serializable dict for fixed endpoint names; unknown routes rejected upstream."""
    if endpoint == 'metadata':
        return {'version':10, 'bands':[label for label,_ in BANDS],
                'operators':DATA['operators'], 'modes':DATA['modes'],
                'discountMaximum':DATA['discountMaximum'], 'units':'MXN'}
    if endpoint == 'defaults':
        return {'state':defaults()}
    if endpoint == 'health':
        return {'status':'ok', 'service':'crt-vmr-5g'}
    state = validate_merge(payload)
    if endpoint == 'vmr':
        return {'bands':calculate_vmr(state)}
    if endpoint == 'discounts':
        return {'discount':calculate_discount(state['discounts']),
                'table':[{'percent':p, **calculate_discount({**state['discounts'],'percent':p})}
                         for p in range(10,101,10)]}
    if endpoint == 'all':
        return {'bands':calculate_vmr(state),
                'discount':calculate_discount(state['discounts']),
                'table':[{'percent':p, **calculate_discount({**state['discounts'],'percent':p})}
                         for p in range(10,101,10)]}
    raise BadScenario('Endpoint no reconocido.')
