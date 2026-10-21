"""Security regressions for protected React production front end."""
import json
import urllib.error
import urllib.request
from test_server import ServerTest

class ReactSecurityTest(ServerTest):
    def test_session_endpoint_needs_login_and_reveals_csrf_to_owner(self):
        self.assertEqual(self.request('/api/v1/auth/session').status,401)
        self.login().read()
        data=json.load(self.request('/api/v1/auth/session'))
        self.assertTrue(data['authenticated'])
        self.assertEqual(len(data['csrf']),64)
    def test_api_requires_csrf(self):
        self.login().read()
        req=urllib.request.Request(self.base+'/api/v1/calculate',
             data=json.dumps({'scenario':{}}).encode(),headers={'Content-Type':'application/json'},method='POST')
        try: resp=self.opener.open(req)
        except urllib.error.HTTPError as e: resp=e
        self.assertEqual(resp.status,403)
        token=json.load(self.request('/api/v1/auth/session'))['csrf']
        req.add_header('X-VMR-CSRF',token)
        self.assertEqual(self.opener.open(req).status,200)
    def test_origin_rejects_cross_site(self):
        self.login().read()
        token=json.load(self.request('/api/v1/auth/session'))['csrf']
        req=urllib.request.Request(self.base+'/api/v1/calculate',data=b'{"scenario":{}}',method='POST',
            headers={'Content-Type':'application/json','X-VMR-CSRF':token,'Origin':'https://evil.example'})
        try: resp=self.opener.open(req)
        except urllib.error.HTTPError as e: resp=e
        self.assertEqual(resp.status,403)
    def test_app_data_not_exposed(self):
        for path in ('/api.py','/server.py','/frontend/src/main.jsx','/.git/config','/frontend/dist/index.html'):
            self.assertEqual(self.request(path).status,404)
        self.assertEqual(self.request('/api/v1/readiness').status,200)
