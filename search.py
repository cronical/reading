#!/usr/bin/env python3
import argparse
import csv
import os.path
import re
import urllib.parse
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
import pandas as pd
import requests
file_base='data/covers'

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
def xl_friendly_isbn(isbn):
  '''force excel to show isbn as a string'''
  if pd.isna(isbn): return isbn
  return '="%s"'% isbn

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

def soup_from_url(session,url):
  r=session.get(url)
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

def get_covers(isbns):
  '''Downloads cover for isbns and returns List of True if success, else false
  Looks each isbn up to find a cover and downloads the cover into data/covers
  File is name <isbn>.jpg
  returns True or false for each isbn
  '''
  if not isinstance(isbns,list):
    isbns=[isbns]
  results=[]
  headers={
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
  }
  isbn_url='https://www.biblio.com'
  session=prep_session(isbn_url,headers=headers)
  for isbn in isbns:
    if isbn:
      r=session.get(isbn_url+'/'+isbn,headers=headers)
      assert r.status_code==200,'Did not get a 200 back'
      soup=BeautifulSoup(r.content,'lxml')
      ts=soup.find(id='top-section')
      if ts is None:
        print(isbn_url+' giving alternate page not programmed')
        results+=[ False]
        continue
      img_url=ts.find('img').attrs['src']
      r=requests.get(img_url)
      if r.status_code!=200:
        print('Did not get a 200 back')
        results+=[ False]
        continue
      filepath=os.path.sep.join([file_base,isbn+'.jpg'])
      with open(filepath,'wb') as f:
        f.write(r.content)
      print('wrote cover image to: '+filepath)
      results+=[True]
    else:
      results+=[False]
  return results

def get_isbns (df):
  '''
  Searches for title (and author) on LCI
  df is a dataframe with columns for title and author
  author values may be NA
  Opens first book record and looks for isbn
  Raises Value errors under some conditions
  Returns list of isbns
  '''
  site='https://lci-mt.iii.com'
  fragment='lang=eng&suite=cobalt'
  session=prep_session(site)
  isbns=[]
  for _,row in df.iterrows():
    title=row['title']
    author=row['author']
    print (f'Searching for: {title}, by {author}:')
    scheme,hostname,path_template=ta_template(pd.isnull(author))
    path=insert_parms(path_template,title,author)
    url=scheme+'://'+hostname+path+'?'+fragment
    soup=soup_from_url(session,url)
    found=soup.find_all(id=re.compile('^resultRecord'))
    print ('%d records found on lci'%len(found))
    if len(found)==0:
      print('not programmed')
      isbns+=[None]
      continue
    record=None
    for item in found:
      # should have exactly one media description
      media=item.find(class_='itemMediaDescription').text
      if media.lower().strip().startswith('book'):
        print('Taking 1st book')
        record=item
        break
      print('skipping media: %s'%media)
    if record is None:
      print('No record found')
      isbns+=[None]
      continue
    next_path_frag=record.find(id=re.compile('^recordDisplayLinkComponent')).attrs['href']
    url=scheme+'://'+hostname+next_path_frag
    soup=soup_from_url(session,url)

    bib_info=soup.find(id="bibInfoDetails").find_all('td')
    flag=False
    found_isbns=[]
    for item in bib_info:
      if flag:
        for item in item.text.split(): # the split gets rid of the noise
          item=item.replace(':','') # it happens as in 	0394587545: $23.00
          if item.isdigit(): # loose the "hardcover", e.g.
            found_isbns+=[item]
        break
      if 'ISBN' in item.text:
        flag=True
    print ("%d ISBN numbers found: %s"%(len(found_isbns),' '.join(found_isbns)))
    if len(found_isbns)==0:
      print('No ISBN found')
      isbns+=[None]
      continue
    isbns+=[found_isbns[0]]
  return isbns

def main():
  parser=argparse.ArgumentParser('Input title and possibly author')
  single=parser.add_argument_group('single')
  from_file=parser.add_argument_group('from_file')
  single.add_argument('title',nargs='*')
  single.add_argument('--author', '-a', nargs='*')
  from_file.add_argument('--file','-f')
  args=parser.parse_args()
  if args.file:
    assert (len(args.title)==0) & (args.author is None), 'file option must be used alone'
    filepath=os.path.join(args.file)
    df=pd.read_csv(filepath)
    isbns=get_isbns(df)
    df['isbn']=[xl_friendly_isbn(i) for i in isbns]
    cover_found=get_covers(isbns)
    df['cover']=cover_found
    df.to_csv(filepath,index=False)
  if args.title:
    title=' '.join(args.title)
    author=args.author
    title_only=author is None
    if not title_only:
      author=' '.join(author)
    df=pd.DataFrame([{'title':title,'author':author}])
    isbns=get_isbns(df)
    cover_found=get_covers(isbns)


if __name__=='__main__':
  main()