#!/usr/bin/env python3
'''merge the email and history data with the booklist
   merge with existing based on date and title, which are assumed to be clean
   Looks at the email and history files to see if there are any new items
   If there are then it appends those to the booklist data and resaves it.
'''
import argparse
import logging
import os
import sys
import pandas as pd

logging.basicConfig(level=logging.INFO)

def do_merge():
  logger=logging.getLogger(__name__)
  parser=argparse.ArgumentParser('Merge the email, my history and other_books data with the booklist')
  parser.add_argument("-r","--reset",action="store_true",default=False,help="Removes any existing records of booklist before merging")
  args=parser.parse_args()

  base='data'
  infiles=['email_data.csv','my_history.csv','other_books.csv']
  outfile='booklist.csv'

  booklist_file=os.path.join(base,outfile)
  for file in infiles+[outfile]:
    if not os.path.exists(booklist_file):
      logger.error(f"file {file} does not exist")
      sys.exit(-1)

  bl_df=pd.read_csv(booklist_file,parse_dates=['date'])
  if args.reset:
    n=len(bl_df)
    bl_df=bl_df.loc[[False]*n]
    logger.info(f"{n} existing records removed from {outfile}")
  logger.debug(f"existing columns are {bl_df.columns}")
  logger.debug(f"{bl_df.shape[0]} existing old records")

  for infile in infiles:
    logger.info(f"--{infile}--")
    df=pd.read_csv(os.path.join(base,infile),parse_dates=['date'])
    
    bl_ix=pd.MultiIndex.from_frame(bl_df[['date','title']])
    new_ix=pd.MultiIndex.from_frame(df[['date','title']])
    sel=[x not in bl_ix for x in new_ix]
    n=sum(sel)
    logger.info(f"  {n} new records to append")
    if n==0:
      continue
    df=df.loc[sel,bl_df.columns] # take only the existing columns
    bl_df=pd.concat([bl_df,df]).reset_index(drop=True)

  bl_df.to_csv(booklist_file,index=False)
  logger.info(f'{len(bl_df)} records written to {booklist_file}')

if __name__=='__main__':
  do_merge()