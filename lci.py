#!/usr/bin/env python3
"""Items to do with library connection inc
"""
import datetime

import re
import urllib.parse

from bs4 import BeautifulSoup
import imageio.v3 as iio
import pandas as pd

from navigate import prep_session, insert_parms,soup_from_url
from parse import title_subitle_author, drop_trailing_point, author_clean

readinghistory='data/readinghistory.html'

def ta_template(title_only=False):
  # copied from the browser to form a template
  if title_only:
    source_url='https://lci-mt.iii.com/iii/encore/search/C__St%3A%28Creating%20Connecticut%29%20c%3A29__Lf%3Afacetcollections%3A29%3A29%3ASouthWindsor%3A%3A__Orightresult__U?lang=eng&suite=cobalt'
    replace_title='Creating Connecticut'
    to_replace=replace_title,

  else:
    #source_url='https://lci-mt.iii.com/iii/encore/search/C__St%3A%28The%20periodic%20table%29%20a%3A%28Eric%20R.%20Scerri%29%20c%3A29__Lf%3Afacetcollections%3A29%3A29%3ASouthWindsor%3A%3A__Orightresult__U?lang=eng&suite=cobalt'
    # the following one does not limit to southwindsor
    source_url='https://lci-mt.iii.com/iii/encore/search/C__St%3A%28The%20periodic%20table%29%20a%3A%28Eric%20R.%20Scerri%29__Orightresult__U?lang=eng&suite=cobalt'
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
  
def get_lci_info (df):
  '''
  Searches for title (and author) on LCI
  df is a dataframe with columns for title and author
  author values may be NA
  For each book, opens record on LCI Encore and looks for isbn, callno
  If an image is available from content cafe, writes it to a file
  Raises Value errors under some conditions
  Returns dataframe of isbns, callno and cover (the name of the image file)
  '''
  site='https://lci-mt.iii.com'
  fragment='lang=eng&suite=cobalt'
  session=prep_session(site)
  ixs=[]
  isbns=[]
  callnos=[]
  filenames=[]
  for ix,row in df.iterrows():
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
          for x,td in enumerate(tr.find_all('td')):
            if x==0:
              library=' '.join(td.text.strip().split(' '))
            if x==1:
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

    ixs+=[ix]
    isbns+=[isbn]
    callnos+=[callno]
    filenames+=[filename]

  df=pd.DataFrame(zip(isbns,callnos,filenames),columns=['isbn','callno','cover'],index=ixs)
  return df

def extract_history_table():
  """Covert the html of the reading history into a dataframe
  The table is in a frame on the site. There is a pagination function.
  This is just dealing with a saved copy of one page, so far.
  It is needed to get the check out date.
  """
  with open(readinghistory) as f:
    html=f.read()
  class_map={'patFuncBibTitle':'th','patFuncAuthor':'td','patFuncDate':'td'}
  soup=BeautifulSoup(html,features="lxml")
  entries=soup.find_all('tr','patFuncEntry')
  df=pd.DataFrame([],columns=['date','title','subtitle','author'])
  for entry in entries:
    row={}
    for class_,tag in class_map.items():
      val=entry.find(tag,class_).text.strip()
      field=''.join(re.split('([A-Z])',class_)[-2:]).lower() # last word of camel case
      match field:
        case 'title':
          val,sub,_=title_subitle_author(val)
          row['subtitle']=sub
        case 'date':
          val=datetime.datetime.strptime(val,"%m-%d-%Y")
        case 'author':
          val=drop_trailing_point(author_clean(val))
      row[field]=val
    df.loc[df.shape[0]]=row
  return df


if __name__=='__main__':
  # testing
  print(extract_history_table())
