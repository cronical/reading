#!/usr/bin/env python3
"""Items to do with library connection inc
"""
import datetime
import logging
import re
import urllib.parse

from bs4 import BeautifulSoup
import imageio.v3 as iio
import pandas as pd

from navigate import prep_session, insert_parms,soup_from_url
from parse import title_subitle_author, drop_trailing_point, author_clean, extract_isbn
from via.model.contributor import from_title, Contributor

readinghistory='data/readinghistory.html'
my_library='South Windsor Public Library'


def ta_template(title_only=False):
  # copied from the browser to form a template
  if title_only:
    source_url="https://lci-mt.iii.com/iii/encore/search/C__St%3A%28Creating%20Connecticut%29__Orightresult__U?lang=eng&suite=cobalt"
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
  df is a dataframe with columns for title, subtitle and author
  author values may be NA.
  both author and subtitle may be truncated, so result brings in full values
  author is considered truncated if it does NOT end in a period.
  
  Searches for the title and (author if known) to get a list of results, which
  are then filtered based on media type and what we have of the subtitle.
  For the first resulting book, opens record on LCI Encore and looks for isbn, call_no
  
  Raises Value errors under some conditions
  Returns dataframe of author, subtitle, isbn, call_no
  '''
  site='https://lci-mt.iii.com'
  fragment='lang=eng&suite=cobalt'
  session=prep_session(site)

  logging.basicConfig(level=logging.INFO)
  logger=logging.getLogger(__name__)
  logger.info(f"Calling LCI for info on {len(df)} books")

  details=[]
  for ix,row in df.iterrows():
    title=row['title']
    subtitle=row['subtitle']
    author=row['author']
    title_only=pd.isnull(author)
    if pd.isna(author):
      author=None
    else:
      if not author.endswith('.'): # check if termination character is intact
        author=None
        title_only=True
      else: # search on last name to avoid problem with nickname, eg. Dan for Daniel
        authors=from_title(row['author']).authors()
        author=([a.last for a in authors]+[None])[0]
    logger.info (f'{title}')
    logger.info(f'   Author: {author}')
    scheme,hostname,path_template=ta_template(title_only=title_only)
    path=insert_parms(path_template,title,author)
    url=scheme+'://'+hostname+path+'?'+fragment
    query_result=soup_from_url(session,url)
    mca=query_result.find(id='mainContentArea')
    result_records=mca.find_all(id=re.compile('^resultRecord')) # such as resultRecord-b2147185
    logger.info ('   %d records found on lci'%len(result_records))
    if len(result_records)==0:
      logger.info('   No results found. not programmed')
      continue
    results=[]
    for record in result_records: 
      result={'id':record.attrs['id']} # use the div-id just to make it unique
      result['media']=record.find(class_='itemMediaDescription').text # should have exactly one media description
      result['author_raw']=None
      author_info=record.find(class_="dpBibAuthor") # sometimes author info is missing on title line, so pick it up here.
      if author_info is not None:
        if author_info.find('a'):
          result['author_raw']=author_info.find('a').text.strip() # last, first, dob-
      title_info=record.find(class_='title')
      result['title']=title_info.text.strip()
      rdl=title_info.find(id=re.compile('^recordDisplayLink'))
      result['url']=scheme+'://'+hostname+rdl['href']
      results+=[result]

    result_df=pd.DataFrame(results)
    pd.options.display.max_colwidth=0
    
    # apply fitering
    sel=result_df.media=='Book'
    sel=sel & result_df.title.str.startswith(title)
    if title_only:
      titles=result_df.title.to_list()
      sel=sel & pd.Series([drop_trailing_point(subtitle) in a for a in titles])
    logger.info(f"   {sum(sel)} matching records found")
    if sum(sel)>0:
      for _,row in result_df.iloc[[sel.to_list().index(True)]].iterrows(): # take the 1st one
        tsa=title_subitle_author(row['title'])
        if len(tsa[2])==0: # if the title doesn't contain the author data
          if row['author_raw']is not None:
            ar_parts=row['author_raw'].split(', ')
            assert 3==len(ar_parts),f"unexpected author format {row['author_raw']}"
            last,first=ar_parts[:2]
            a=Contributor(last=last,first=first,role='author')
            tsa[2]=a.full_name()+"."
        detail={"author":tsa[2],"subtitle":tsa[1],"index":ix}
      
        book_details=soup_from_url(session,url=row['url']) # header, location, details
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
                call_no=' '.join(td.find('a').text.strip().split(' '))
                library_map[library]=call_no
                break
        lib_df = pd.DataFrame([library_map.keys(),library_map.values()]).T
        lib_df.columns=['library','call_no']
        sel=lib_df.library.str.startswith(my_library)
        # use my library's call no unless it doesn't have one, then use the mode
        if sel.sum(): 
          call_no=lib_df.loc[sel,'call_no'].to_list()[0]
        else:
          call_no=lib_df.call_no.mode().tolist()[0]
        detail['call_no']=call_no.replace(' ','_')

        # get isbn if any  
        detail['isbn']=None
        bib_info=book_details.find(id="bibInfoDetails").find_all('td')
        flag=False
        found_isbns=[]
        for items in bib_info:
          if flag:
            for item in items.text.split(): # the split gets rid of the noise
              isbn=extract_isbn(item)
              if isbn:
                found_isbns+=[item]
            break
          if 'ISBN' in items.text:
            flag=True
        logger.info ("   %d ISBN numbers found: %s"%(len(found_isbns),' '.join(found_isbns)))
        if len(found_isbns):
          detail['isbn']=sorted(found_isbns,reverse=True)[0]# largest one
        details+=[detail]

  lci_df=pd.DataFrame(details)
  lci_df.set_index('index',inplace=True)
  return lci_df

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
