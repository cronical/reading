#!/usr/bin/env python3
import argparse
import logging
import os.path
import warnings

import pandas as pd

from biblio import enhance_covers
from lci import get_lci_info
from parse import xl_friendly_isbn


file_base='data/covers'
my_library= "South Windsor Public Library"
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

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
    logger.info(f"Getting LCI info & cover art")
    df=pd.read_csv(filepath)
    new=df.title==df.title
    if 'call_no' in df.columns:
      new=df.call_no.isna()
    logger.info(f"Processing {sum(new)} records without call numbers")
    lci_info=get_lci_info(df.loc[new])
    lci_info=enhance_covers(lci_info)
    sel=lci_info.isbn.notna()
    lci_info.loc[sel,'isbn']=[xl_friendly_isbn(i)for i in lci_info.loc[sel,'isbn'].to_list() ]
    warnings.simplefilter(action='ignore', category=FutureWarning)
    df.loc[lci_info.index,lci_info.columns]=lci_info # generates a futurewarning but that is probably a bug (as of pandas version 2.1.2)
    df["library"]=my_library
    df.to_csv(filepath,index=False)

  if args.title:
    title=' '.join(args.title)
    subtitle=''
    if ':' in title:
      title,subtitle=title.split(':',maxsplit=2)
    author=args.author
    title_only=author is None
    if not title_only:
      author=' '.join(author)
    df=pd.DataFrame([{'title':title,'subtitle':subtitle,'author':author}])
    lci_info=get_lci_info(df)
    lci_info=enhance_covers(lci_info)
    print(lci_info)

if __name__=='__main__':
  main()