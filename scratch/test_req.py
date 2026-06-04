import urllib.request
from urllib.error import HTTPError

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = urllib.request.build_opener(NoRedirectHandler())
try:
    res = opener.open('https://app.janiopontes.com.br/acesso/PRT-20260604-5EE1D3')
except HTTPError as e:
    res = e

print("Status:", res.status)
for k, v in res.headers.items():
    print(k, ":", v)
