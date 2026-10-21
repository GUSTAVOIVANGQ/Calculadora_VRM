"""API REST sobre el servicio con login; no cambia el sistema de acceso."""
import json
import urllib.request
import urllib.error
from test_server import ServerTest


class ApiTest(ServerTest):
    # Heredamos las pruebas de autenticación, además de los endpoints JSON.
    def json_request(self,path,body=None,headers=None,unauth=False):
        data=json.dumps(body).encode() if body is not None else None
        hdr = dict(headers or ({'Content-Type':'application/json'} if data else {}))
        if data and path.startswith('/api/v1/calculate') and not unauth and self.cookies:
            csrf = json.load(self.opener.open(self.base+'/api/v1/auth/session')).get('csrf')
            hdr['X-VMR-CSRF'] = csrf
        req=urllib.request.Request(self.base+path,data=data,headers=hdr,method='POST' if data is not None else 'GET')
        opener=urllib.request.build_opener(urllib.request.HTTPHandler) if unauth else self.opener
        try:return opener.open(req)
        except urllib.error.HTTPError as err:return err

    def test_12_api_protected_without_login(self):
        self.assertEqual(self.json_request('/api/v1/health').status,200)
        for path in ('/api/v1/metadata','/api/v1/defaults'):
            self.assertEqual(self.json_request(path).status,401)
        for path in ('/api/v1/calculate','/api/v1/calculate/vmr','/api/v1/calculate/discounts'):
            self.assertEqual(self.json_request(path,{'scenario':{}}).status,401)

    def test_13_get_metadata_defaults(self):
        self.login().read()
        r=self.json_request('/api/v1/metadata')
        self.assertEqual(r.status,200)
        self.assertEqual(r.headers.get_content_type(),'application/json')
        meta=json.load(r)
        self.assertEqual(meta['discountMaximum'],[50,50,70,80,100])
        self.assertEqual(len(json.load(self.json_request('/api/v1/defaults'))['state']['population']),9)

    def test_14_calculate_vmr_and_all(self):
        self.login().read()
        a=json.load(self.json_request('/api/v1/calculate/vmr',{'scenario':{'spectrum':[36,22,15]}}))
        self.assertEqual(len(a['bands']),3)
        self.assertEqual(a['bands'][0]['mhz'],36)
        self.assertGreater(a['bands'][0]['vmr'],0)
        b=json.load(self.json_request('/api/v1/calculate',{'scenario':{'discounts':{'operator':'Operador C','mode':'Mixto 10/90','percent':70}}}))
        self.assertEqual(len(b['table']),10)
        self.assertEqual(b['table'][-1]['available'],False)
        self.assertEqual(b['discount']['available'],True)
        self.assertEqual(len(b['bands']),3)

    def test_15_discount_custom_ratio(self):
        self.login().read()
        payload={'scenario':{'discounts':{'operator':'AT&T','mode':'Híbrido 50/50','percent':30,'allocations':[100,0,80,10]}}}
        r=json.load(self.json_request('/api/v1/calculate/discounts',payload))
        self.assertEqual(r['discount']['coverageProportion'],0.8)
        self.assertEqual(r['discount']['modernProportion'],0.19999999999999996)
        self.assertEqual(r['table'][2]['percent'],30)

    def test_16_api_rejects_invalid(self):
        self.login().read()
        for body in ({'scenario':{'unknown':123}}, {'scenario':{'discounts':{'percent':11}}},
                     {'scenario':{'years':100}}, {'scenario':{'spectrum':['bad',0,0]}},
                     {'scenario':{'source':['n','b','n']}}, {'scenario':{'discounts':{'allocations':[5,4]}}}):
            self.assertEqual(self.json_request('/api/v1/calculate',body).status,422,body)
        self.assertEqual(self.json_request('/api/v1/calculate',{'scenario':{}},headers={'Content-Type':'text/plain'}).status,415)
        self.assertEqual(self.json_request('/api/v1/nonexistent').status,404)

    def test_17_same_login_and_no_public_data(self):
        self.login().read()
        self.assertEqual(self.json_request('/api/v1/metadata').status,200)
        r=self.request('/logout','POST',{'csrf': json.load(self.request('/api/v1/auth/session'))['csrf']})
        self.assertEqual(self.json_request('/api/v1/metadata').status,401)
        self.assertEqual(self.request('/api.py').status,404)
