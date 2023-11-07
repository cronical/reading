#!/usr/bin/env python3
import argparse
import csv
import io
import os.path
import re
import urllib.parse
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
import imageio.v3 as iio
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

def get_biblio_covers(isbns):
  '''Downloads cover for isbns and returns List of True if success, else false
  Looks each isbn up to find a cover and downloads the cover into data/covers
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

def get_lci_info (df):
  '''
  Searches for title (and author) on LCI
  df is a dataframe with columns for title and author
  author values may be NA
  Opens first book record and looks for isbn, callno
  If an image is available from content cafe, writes it to a file
  Raises Value errors under some conditions
  Returns dataframe of isbns, callno and cover (the name of the image file)
  '''
  site='https://lci-mt.iii.com'
  fragment='lang=eng&suite=cobalt'
  session=prep_session(site)
  isbns=[]
  callnos=[]
  filenames=[]
  for _,row in df.iterrows():
    callno,isbn,filename=None,None,None
    title=row['title']
    author=row['author']
    print (f'Searching for: {title}, by {author}:')
    scheme,hostname,path_template=ta_template(pd.isnull(author))
    path=insert_parms(path_template,title,author)
    url=scheme+'://'+hostname+path+'?'+fragment
    query_result=soup_from_url(session,url)
    mca=query_result.find(id='mainContentArea')
    result_records=mca.find_all(id=re.compile('^resultRecord'))
    print ('%d records found on lci'%len(result_records))
    valid=True
    if len(result_records)==0:
      print('not programmed')
    if valid:    
      record=None
      for item in result_records: 
        # should have exactly one media description
        media=item.find(class_='itemMediaDescription').text
        if media.lower().strip().startswith('book'):
          print('Taking 1st book')
          record=item
          break
        print('skipping media: %s'%media)
      if record is None:
        print('No record found')
        valid=False
    
    # record was found and there is an entry that survives media filter
    if valid:
      # inspect thumbnail
      ibc=record.find(class_='itemBookCover') # div will be there even if there is no good image
      thumb_url=scheme+"://"+hostname+"/"+ibc.find('img')['src'] # we have to look at the image
      thumb_image=iio.imread(thumb_url,index=None)
      image_exists=thumb_image.shape[0:2]!=(1,1)# if its a 1x1 png then there is no image

      # the link on the title should always be there
      rdl=record.find(class_='title').find(id=re.compile('^recordDisplayLink'))
      url=scheme+'://'+hostname+rdl['href']
      book_details=soup_from_url(session,url) # header, location, details
      items_section=book_details.find(class_='allItemsSection')
      if items_section is None:
        items_section=book_details.find(class_= 'availableItemsSection')
      library_table=items_section.find('table',class_='itemTable')
      
      # get all the libraries and their call numbers
      library_map={}
      for tr in library_table.find_all('tr'):
        if tr.find('th') is None:
          for ix,td in enumerate(tr.find_all('td')):
            if ix==0:
              library=' '.join(td.text.strip().split(' '))
            if ix==1:
              callno=' '.join(td.find('a').text.strip().split(' '))
              library_map[library]=callno
              break
      df = pd.DataFrame([library_map.keys(),library_map.values()]).T
      df.columns=['library','callno']
      my_library='South Windsor Public Library'
      sel=df.library.str.startswith(my_library)
      # use my library's call no unless it doesn't have one, then use the mode
      if sel.sum(): 
        callno=df.loc[sel,'callno'].to_list()[0]
      else:
        callno=df.callno.mode().tolist()[0]
      callno=callno.replace(' ','_')

      if image_exists:
        # find cover art on content cafe
        gbc2=book_details.find(class_='gridBrowseCol2')
        cover_section=gbc2.find(class_='itemBookCover')
        cc_base_url=cover_section.find('a')['href']
        base_parts=urllib.parse.urlparse(cc_base_url)
        
        if urllib.parse.parse_qs(base_parts.query)['ItemKey']!=['%s']: # if the key is not a template value, there should be a cover
          cc=soup_from_url(session,cc_base_url)# follow link to content cafe page
          forms=cc.find_all('form')
          a=forms[0].find(title='Navigate to jacket information')
          if a is None:
            print('no cover image found on content cafe')
          else:
            href=a['href']
            aspx=href.split("'")[1]
            path='/'.join(base_parts.path.split('/')[:-1]+[aspx])
            form_data={}
            for item in forms[1].find_all('input'):
              form_data[item['name']]=item['value']
            url=base_parts.scheme+'://'+base_parts.hostname+path
            cover_image_page=soup_from_url(session,url=url,method='post',data=form_data)
            r=session.get(cover_image_page.find_all('img')[1]['src']) # the higher res image is second
            filename=f'{callno}.jpg'
            filepath=f'data/covers/'+filename
            with open(filepath,'wb') as f:
              f.write(r.content)
            print('wrote cover image to: '+filepath)
      else:
        print('no thumbnail cover image found')

      # get isbn if any  
      bib_info=book_details.find(id="bibInfoDetails").find_all('td')
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
      else:
        isbn=found_isbns[0]

    isbns+=[isbn]
    callnos+=[callno]
    filenames+=[filename]

  df=pd.DataFrame(zip(isbns,callnos,filenames),columns=['isbn','callno','cover'])
  return df

def enhance_covers(df):
  '''for missing covers that have isbn try biblio'''
  sel=df.isbn.notna() & df.cover.isna()
  other_covers=get_biblio_covers(df.loc[sel,'isbn'].to_list())
  df.loc[sel,'cover']=other_covers
  return df

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
    lci_info=get_lci_info(df)
    lci_info=enhance_covers(lci_info)
    sel=lci_info.isbn.notna()
    lci_info.loc[sel,'isbn']=[xl_friendly_isbn(i)for i in lci_info.loc[sel,'isbn'].to_list() ]
    df[lci_info.columns]=lci_info
    df.to_csv(filepath,index=False)
  if args.title:
    title=' '.join(args.title)
    author=args.author
    title_only=author is None
    if not title_only:
      author=' '.join(author)
    df=pd.DataFrame([{'title':title,'author':author}])
    lci_info=get_lci_info(df)
    lci_info=enhance_covers(lci_info)
    print(lci_info)

if __name__=='__main__':
  main()