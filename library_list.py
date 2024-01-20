#!/usr/bin/env python3
"""Convert html page https://www.libraryconnection.info/members_list.php
to csv file data/libaries.csv
"""
from bs4 import BeautifulSoup
import pandas as pd
outfile='data/libraries.csv'
def main():
    with open ('data/libraries.html') as f:
        soup=BeautifulSoup(f,features="lxml")
    lib_divs=soup.find_all('div','libraryname')
    libs=[a.text.strip().split(':') for a in lib_divs]
    df=pd.DataFrame(libs,columns=['library','branch'])
    # a few need aliases
    df['alias']=''
    aliases={'Portland Library':'Portland Public Library',
             'Wethersfield Library': 'Wethersfield Public Library'
             }
    sel=df.library.isin(aliases)
    for ix,row in df.loc[sel].iterrows():
        df.loc[ix,'alias']=aliases[row['library']]

    df.to_csv(outfile,index=False)
    print(f'Wrote to {outfile}')

if __name__ == "__main__":
    main()