#!/usr/bin/env python3
import argparse
import re
import urllib.parse

from bs4 import BeautifulSoup
import requests

def ta_template(title_only=False):
  # copied from the browser to form a template
  if title_only:
    source_url='https://lci-mt.iii.com/iii/encore/search/C__St%3A%28Creating%20Connecticut%29%20c%3A29__Lf%3Afacetcollections%3A29%3A29%3ASouthWindsor%3A%3A__Orightresult__U?lang=eng&suite=cobalt'
    replace_title='Creating Connecticut'
    to_replace=replace_title,

  else:
    source_url='https://lci-mt.iii.com/iii/encore/search/C__St%3A%28The%20periodic%20table%29%20a%3A%28Eric%20R.%20Scerri%29%20c%3A29__Lf%3Afacetcollections%3A29%3A29%3ASouthWindsor%3A%3A__Orightresult__U?lang=eng&suite=cobalt'
    replace_title='The periodic table'
    replace_author='Eric R. Scerri'
    to_replace=replace_title,replace_author
 
  # create the template
  o=urllib.parse.urlparse(source_url)
  scheme=o.scheme
  hostname=o.hostname
  path_template=urllib.parse.unquote(o.path)
  for text in to_replace:
    path_template=path_template.replace(text,'%s')
  return scheme,hostname,path_template

def insert_parms(path_template,title,author=None):
  # insert the new parms
  match author is None:
    case True:
      path=path_template%title
    case False:
      path=path_template%(title,author)
  path=urllib.parse.quote(path)
  return path

def main():
  parser=argparse.ArgumentParser('Input title and possibly author')
  parser.add_argument('title',nargs='*')
  parser.add_argument('--author', '-a', nargs='*')
  args=parser.parse_args()
  title=' '.join(args.title)
  author=args.author
  title_only=author is None
  if not title_only:
    author=' '.join(author)
  scheme,hostname,path_template=ta_template(title_only)
  fragment='lang=eng&suite=cobalt'
  path=insert_parms(path_template,title,author)
  url=scheme+'://'+hostname+path+'?'+fragment
  r=requests.get(url)
  assert r.status_code==200,'Did not get a 200 back'
  soup=BeautifulSoup(r.content,'lxml')
  found=soup.find_all(id=re.compile('^resultRecord'))
  print ('%d records found on lci'%len(found))
  assert len(found)!=0,'nonce'
  record=None
  for item in found:
    # should have exactly one media description
    media=item.find(class_='itemMediaDescription').text
    if media.lower().strip().startswith('book'):
      print('Taking 1st book')
      record=item
      break
    print('skipping media: %s'%media)


  next_path_frag=record.find(id=re.compile('^recordDisplayLinkComponent')).attrs['href']
  next_url=scheme+'://'+hostname+next_path_frag
  r=requests.get(next_url)
  assert r.status_code==200,'Did not get a 200 back'
  soup=BeautifulSoup(r.content,'lxml')

  bib_info=soup.find(id="bibInfoDetails").find_all('td')
  flag=False
  for item in bib_info:
    if flag:
      isbns=[]
      for item in item.text.split(): # the split gets rid of the noise
        if item.isdigit(): # loose the "hardcover", e.g.
          isbns+=[item]
      break
    if 'ISBN' in item.text:
      flag=True
  print ("ISBN numbers found: %s"%' '.join(isbns))
  if len(isbns)==0:
    print('No cover downloaded')
  else:
    headers={
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    }
    isbn_url='https://www.biblio.com'
    s=requests.Session()
    r=s.get(isbn_url)# get any cookies
    r=s.get(isbn_url+'/'+isbns[0],headers=headers)
    if r.history:
      print("Request was redirected")
      print(r.history)
      for resp in r.history:
          print(resp.status_code, resp.url)
      print("Final destination:")
      print(r.status_code, r.url)
    assert r.status_code==200,'Did not get a 200 back'
    soup=BeautifulSoup(r.content,'lxml')
    img_url=soup.find(id='top-section').find('img').attrs['src']
    r=requests.get(img_url)
    assert r.status_code==200,'Did not get a 200 back'
    filepath='data/'+isbns[0]+'.jpg'
    with open(filepath,'wb') as f:
      f.write(r.content)
    print('wrote cover image to: '+filepath)
    pass
  
  pass

if __name__=='__main__':
  main()