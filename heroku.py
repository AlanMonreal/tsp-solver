from urllib.request import urlopen, Request, HTTPError
from urllib.parse import urlencode
from json import load
from os import getenv

def runOneOff(command):
    token = getenv('HEROKU_API_KEY')
    url = 'https://api.heroku.com'
    appId = getenv('HEROKU_APP')
    if not appId:
        print('HEROKU_APP env var need to be set')
        return False
    qs = '/apps/'+appId+'/dynos'
    reqData = urlencode({'command':command, 'attach':'false'}).encode()
    authHeader = {'Authorization':'Bearer {}'.format(token), 'Accept':'application/vnd.heroku+json; version=3'}
    try:
        with urlopen(Request(url+qs, data=reqData, headers=authHeader)) as respData:
            return True
    except HTTPError as err:
        print('Connection failed with HTTP code '+str(err.code)+': '+str(err.reason)+'\n on url: '+err.url)
        print(err.read().decode('utf-8'))
        return False
