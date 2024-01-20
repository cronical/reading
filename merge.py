#!/usr/bin/env python3
'''merge the email and history data with the booklist
   merge with existing based on date and title, which are assumed to be clean
   Looks at the email and history files to see if there are any new items
   If there are then it appends those to the booklist data and resaves it.
'''
import os
import pandas as pd

base='data'
infiles=['email_data.csv','my_history.csv']
outfile='booklist.csv'

booklist_file=os.path.join(base,outfile)
if not os.path.exists(booklist_file):
  raise ValueError(f"target file {booklist_file} does not exist")
bl_df=pd.read_csv(booklist_file,parse_dates=['date'])
print(f"existing columns are {bl_df.columns}")
print(f"{bl_df.shape[0]} existing old records")

pd.set_option('display.max_colwidth',35)
pd.set_option('display.max_columns',10)
pd.set_option('display.width',0)

for infile in infiles:
  print(f"--{infile}--")
  df=pd.read_csv(os.path.join(base,infile),parse_dates=['date'])
  
  bl_ix=pd.MultiIndex.from_frame(bl_df[['date','title']])
  new_ix=pd.MultiIndex.from_frame(df[['date','title']])
  sel=[x not in bl_ix for x in new_ix]
  n=sum(sel)
  print(f"{n} new records to append")
  if n==0:
    continue
  df=df.loc[sel,bl_df.columns] # take only the existing columns
  bl_df=pd.concat([bl_df,df]).reset_index(drop=True)

bl_df.to_csv(booklist_file,index=False)
print('%d records written to %s'%(bl_df.shape[0],booklist_file))
