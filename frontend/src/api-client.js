/** Same-origin only API wrapper with session-bound CSRF. */
export async function getSession() {
  const response = await fetch('/api/v1/auth/session', {credentials:'same-origin',cache:'no-store'});
  if (!response.ok) throw new Error('Sesión no autorizada');
  return response.json();
}
export async function calculateScenario(scenario, kind='all') {
  const routes = {all:'/api/v1/calculate',vmr:'/api/v1/calculate/vmr',discounts:'/api/v1/calculate/discounts'};
  const route = routes[kind];
  if (!route) throw new Error('Tipo de cálculo no válido');
  const session = await getSession();
  const response = await fetch(route,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-VMR-CSRF':session.csrf},body:JSON.stringify({scenario})});
  if (response.status===401) {location.assign('/login');throw new Error('Sesión vencida');}
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Error de cálculo');
  return body;
}
