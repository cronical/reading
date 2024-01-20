"""Items to do with navigating the web and getting data
"""
import urllib.parse
from urllib3.util import Retry
import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

def insert_parms(path_template,title,author=None):
  # insert the new parms
  match author is None:
    case True:
      path=path_template%title
    case False:
      path=path_template%(title,author)
  path=urllib.parse.quote(path)
  return path
def prep_session(url,headers=None):
  s = requests.Session()
  retries = Retry(
      total=4,
      backoff_factor=1,
      status_forcelist=[429],
      allowed_methods={'GET'},
  )
  s.mount('https://', HTTPAdapter(max_retries=retries))  
  _=s.get(url,headers=headers)# get any cookies  
  return s

def soup_from_url(session,url,method='get',data=None):
  match method:
    case 'get':
      r=session.get(url)
    case 'post':
      r=session.post(url,data=data)
  if r.status_code!=200:
    raise ValueError('Did not get a 200 back')
  if r.history:
    print("Request was redirected")
    #print(r.history)
    #for resp in r.history:
        #print(resp.status_code, resp.url)
    #print("Final destination:")
    #print(r.status_code, r.url)
  return BeautifulSoup(r.content,'lxml')  
