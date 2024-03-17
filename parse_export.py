#!/usr/bin/env python3
'''Parse the files downloaded from the LCI my reading history export function "Full Display"
While there is a field for Author it is not as full featured as the part after the slash in the title field,
so we use that instead.
'''
import datetime
import logging
import re
import pandas as pd
from simple_term_menu import TerminalMenu

from parse import title_subitle_author, drop_trailing_point, xl_friendly_isbn
from lci import extract_history_table
from biblio import enhance_covers

logging.basicConfig(level=logging.DEBUG)
logger=logging.getLogger(__name__) 

edition_fields=['isbn','format']
lib_fields=['library','call_no']
pub_fields=['publ_city','publisher','publ_year','copyright_year']
tit_fields=['title','subtitle']
fields=['author']+tit_fields+edition_fields+lib_fields+pub_fields
home_library='South Windsor Public Library'
datafile='data/export.txt'
outfile='data/my_history.csv'
library_file='data/libraries.csv'
libraries=pd.read_csv(library_file)
pat_record=r'^(Record|TITLE|PUB INFO|STANDARD #|\d{1,2} >)(.*$)'

def select_pub_info(pub_infos,title):
  """Get just one"""
  pat_cr=r'^\u00A9(\d{4,4})\.'
  pat_publ=r'(.+?):(.+?),.*?(\d{4,4})'
  copyright_year=-1 # missing value indicator
  options=[]
  for val in pub_infos:
    m=re.match(pat_cr,val)
    if m: #  the line that offers the copyright year
      copyright_year=int(m.group(1)) 
      continue
    options+=[val]
  option=0
  if len(options)>1:
    terminal_menu = TerminalMenu(options,title=f'Please select publisher for {title}')
    option = terminal_menu.show()
    if option is None:
      raise ValueError("Cannot determine publisher")
  publ=options[option]
  m=re.match(pat_publ,publ)
  if m:
    publ_city=m.group(1).strip()
    publisher=m.group(2).strip()
    publ_year=int(m.group(3))
    return publ_city,publisher,publ_year,copyright_year
  raise ValueError("Cannot parse the publisher info")

def select_library_call_no(libs,home_library,title):
  """returns library and callno"""
  lc=[]
  home=[]
  for ix,tab_row in enumerate(libs):
    lib=tab_row[0:30].split('-')[0].strip() # ignore the collection part after the dash
    pat_branch=re.compile(r',|:|\sat\s') # sometimes its a colon, and bloomfield at the atrium
    lib=pat_branch.split(lib)
    call_no=tab_row[31:62].strip()
    if not (libraries.library.str.startswith(lib[0])).any():
      if not (libraries.alias.str.startswith(lib[0])).any():
        logger.warning(f'Not in master library list: {lib[0]}')
    lc+=[(lib[0],call_no)]
    if lib[0].startswith(home_library):
      home+=[ix]
  if len(home)==1:
    return lc[home[0]]
  if len(lc)==1:
    return lc[0]
  # prompt from the unique list of library towns (there can be >1 due to branches and collections)
  options=[a[0] for a in lc]
  options_u=sorted(list(set(options)))
  terminal_menu = TerminalMenu(options_u,title=f'Please select library for {title}')
  menu_entry_index = terminal_menu.show()
  if menu_entry_index is None:
    raise ValueError("Cannot determine library")
  lc_ix=options.index(options_u[menu_entry_index])
  return lc[lc_ix]

def select_edition(editions,title):
  """ pick most likely one if possible, then ask if needed.
  """
  num_fmt=[]
  pref_fmt='hard'#['hardcover','hardback']
  excl='UK '
  for ix,tab_row in enumerate(editions):
    w=tab_row.split(' ')
    sbn=w[0]
    fmt=' '.join(w[1:])
    num_fmt+=[(sbn,fmt)]
  df_all=pd.DataFrame(num_fmt,columns=['num','fmt'])
  sel=(df_all.fmt.str.contains(pref_fmt)) | (df_all.fmt.str.len() == 0)
  sel=sel & ~ (df_all.fmt.str.startswith(excl))
  df=df_all.loc[sel]
  sel=df.num.str.len()==13
  if sel.any():
    df=df.loc[sel]
  tuples=list(df.itertuples(index=False,name=None))
  if df.shape[0]==1:
    return tuples[0]
  options=df_all.agg(' '.join,axis=1).to_list()
  terminal_menu = TerminalMenu(options,title=f'Please select standard number for {title}')
  menu_entry_index = terminal_menu.show()
  if menu_entry_index is None:
    raise ValueError("Cannot determine standard book number")
  return tuple(df_all.iloc[menu_entry_index].to_list())

def complete_record(record,pub_info,libs,home_library,sbn):
  title=record['title']
  try:
    record.update(zip(pub_fields,select_pub_info(pub_info,title)))
  except (ValueError, IndexError):
    logger.warning(f'Could not determine publishing info for {title}')
  try:
    record.update(zip(lib_fields,select_library_call_no(libs,home_library=home_library,title=title)))
  except ValueError:
    logger.warning(f'Could not determine library for {title}')
  try:
    if len(sbn): # there are records with no standard # entries.
      isbn,fmt=select_edition(sbn,title)
      isbn=xl_friendly_isbn(isbn)
      record.update(zip(edition_fields,(isbn,fmt)))
  except ValueError:
    logger.warning(f'Could not determine isbn for {title}')
  logger.debug(f"Completed {title}")
  return record

def unwrap_file(path):
  """Read entire text file and combine lines that wrap into a single line
  Return list of lines"""
  with open(path) as f:
    lines=f.readlines()
  output=[]
  current=""
  for line in lines:
    mtch=re.match(r'^\s',line)
    if mtch: # its a continuation
      current=current+' '+line.strip()
    else:
      output+=[current]
      current=line.strip()

  output+=[current]  
  return output[1:] # drop the pseudo record

def read_file(path):
  df=pd.DataFrame([],columns=fields,dtype=int) # use integer type.  Treat -1 as missing value, strings will be changed
  record={}
  lines=unwrap_file(path)
  for line in lines:
    mtch=re.match(pat_record,line)
    if mtch:
      kw=mtch.group(1)
      val=mtch.group(2).strip()
      match kw:
        case 'Record':
          # jump to new record
          if len(record)>0:
            record=complete_record(record,pub_info,libs,home_library,sbn)
            df.loc[df.shape[0]]=record
          record={}
          pub_info=[]
          sbn=[]
          libs=[]
        case 'TITLE':
          val=title_subitle_author(val)
          record.update(zip(tit_fields,val[0:2]))#title, subtitle
          record['author']=val[2]# parsing (from_title) has moved to the load routine
        case 'PUB INFO':
          pub_info+=[val]
        case 'STANDARD #':
          sbn+=[drop_trailing_point(val)]
        case _:
          libs+=[val]

  if len(record)>0: #last one?
    df.loc[df.shape[0]]=complete_record(record,pub_info,libs,home_library,sbn)

  # get the date
  hist_df=extract_history_table()
  df.insert(0,'date',datetime.datetime.now())
  for frame in [df,hist_df]:
    frame.set_index('title',inplace=True)
  for ix,row in hist_df.iterrows():
    df.loc[ix,'date']=row['date']
  df.reset_index(inplace=True)  

  # preferred order of columns
  order=[1,0]+list(range(2,df.shape[1]))
  df=df.iloc[:,order]

  df=enhance_covers(df)

  pd.options.display.width=None
  pd.options.display.max_columns=11
  pd.options.display.max_colwidth=20
  
  sel=df.author.str.len()==0
  if any(sel):
    logger.warning("Ignoring line(s) with no author:")
    for ix,row in df.loc[sel].iterrows():
      logger.warning(f"   {row['title']}")
    df=df.loc[~sel]
  df.to_csv(outfile,index=False)
  logger.info(f'Wrote to {outfile}')

if __name__=='__main__':
  read_file(datafile)  
