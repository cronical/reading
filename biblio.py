"""Items to do with biblio
"""
import os
import re

from bs4 import BeautifulSoup
import requests

from navigate import prep_session
from parse import strip_xl_friendly

def get_biblio_covers(isbns,file_base='data/covers'):
  '''Downloads cover for isbns and returns List of True if success, else false
  Looks each isbn up to find a cover and downloads the cover into file_base folder
  File is name <isbn>.jpg
  returns filename or None for each isbn
  '''
  if not isinstance(isbns,list):
    isbns=[isbns]
  filenames=[]
  headers={
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
  }
  isbn_url='https://www.biblio.com'
  session=prep_session(isbn_url,headers=headers)
  for isbn in isbns:
    if isbn:
      isbn=strip_xl_friendly(isbn)
      r=session.get(isbn_url+'/'+isbn,headers=headers)
      assert r.status_code==200,'Did not get a 200 back'
      soup=BeautifulSoup(r.content,'lxml')
      ts=soup.find(id='top-section')
      if ts is None:
        print(isbn_url+' giving alternate page not programmed')
        filenames+=[ None]
        continue
      img_url=ts.find('img').attrs['src']
      r=requests.get(img_url)
      if r.status_code!=200:
        print('Did not get a 200 back')
        filenames+=[ None]
        continue
      filename=isbn+'.jpg'
      filepath=os.path.sep.join([file_base,filename])
      with open(filepath,'wb') as f:
        f.write(r.content)
      print('wrote cover image to: '+filepath)
      filenames+=[filename]
    else:
      filenames+=[None]
  return filenames

def enhance_covers(df):
  '''for missing covers that have isbn try biblio'''
  sel=df.isbn.notna() 
  if 'cover' in df.columns:
    sel=sel & (df.cover.isna())
  other_covers=get_biblio_covers(df.loc[sel,'isbn'].to_list())
  df.loc[sel,'cover']=other_covers
  return df
