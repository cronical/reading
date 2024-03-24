"""Items to do with biblio
"""
import os
import logging
import re

from bs4 import BeautifulSoup
import requests

from navigate import prep_session
from parse import strip_xl_friendly
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

def get_biblio_covers(isbns,file_base='data/covers'):
  '''Downloads cover for isbns and returns List of True if success, else false
  Looks each isbn up to find a cover and downloads the cover into file_base folder
  File is name <isbn>.jpg
  returns filename or None for each isbn
  '''
  if not isinstance(isbns,list):
    isbns=[isbns]
  
  logger.info(f"Calling {__name__} for info on {len(isbns)} books")
  
  filenames=[]
  headers={
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
  }
  isbn_url='https://www.biblio.com'
  session=prep_session(isbn_url,headers=headers)
  for isbn in isbns:
    isbn=strip_xl_friendly(isbn)
    filename=isbn+'.jpg'
    filepath=os.path.sep.join([file_base,filename])
    filenames+=[filename] # provisionally this will be the name (unless an error happens)
    if os.path.exists(filepath):
      logger.info('using existing cover image: '+filepath)
    else:
      if isbn:
        r=session.get(isbn_url+'/'+isbn,headers=headers)
        if r.status_code!=200:
          logger.warning(f'Got status {r.status_code} while loading page for {isbn}')
          filenames[-1]=None
          continue                         
        soup=BeautifulSoup(r.content,'lxml')
        ts=soup.find(id='top-section')
        if ts is None:
          logger.warning(f'biblio gave alternate page for {isbn}. not programmed') # e.g. https://www.biblio.com/9780593490594  (silverview)
          filenames[-1]=None
          continue
        img_url=ts.find('img').attrs['src']
        if len(img_url)==0:
          logger.warning(f'No image found for {isbn}')
          filenames[-1]=None
          continue
        r=requests.get(img_url)
        if r.status_code!=200:
          logger.warning(f'Got status {r.status_code} while trying to get cover image for {isbn}')
          filenames[-1]=None
          continue                         
        with open(filepath,'wb') as f:
          f.write(r.content)
        logger.info('wrote cover image to: '+filepath)
      else:
        filenames[-1]=None
  return filenames

def enhance_covers(df):
  '''for missing covers that have isbn try biblio'''
  sel=df.isbn.notna() 
  if 'cover' in df.columns:
    sel=sel & (df.cover.isna())
  other_covers=get_biblio_covers(df.loc[sel,'isbn'].to_list())
  df.loc[sel,'cover']=other_covers
  return df
