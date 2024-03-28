#!/usr/bin/env python3
"""Generate the library list by
- parsing html page https://www.libraryconnection.info/members_list.php (stored locally as data/libraries.html)
- adding rows from library_other.csv
Save result to to csv file data/libraries.csv
"""
from bs4 import BeautifulSoup
import pandas as pd
outfile='data/libraries.csv'
def lci_html_to_df():
    with open ('data/libraries.html') as f:
        soup=BeautifulSoup(f,features="lxml")
    lib_divs=soup.find_all('div','libraryname')
    libs=[a.text.strip().split(':') for a in lib_divs]
    df=pd.DataFrame(libs,columns=['library','branch'])
    # a few need aliases
    df['alias']=''
    aliases={
        'Portland Library':'Portland Public Library',
        'Wethersfield Library': 'Wethersfield Public Library',
        'West Hartford Public Library':'West Hartford',
        'Windsor Public Library':'Windsor'
        }
    sel=df.library.isin(aliases)
    for ix,row in df.loc[sel].iterrows():
        df.loc[ix,'alias']=aliases[row['library']]
    return df

def main():
    df=lci_html_to_df()
    other=pd.read_csv('data/library_other.csv')
    for _,row in other.iterrows():
        df.loc[len(df)]=row
    df.to_csv(outfile,index=False)
    print(f'Wrote {len(df)} records to {outfile}')

if __name__ == "__main__":
    main()