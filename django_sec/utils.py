import re
import urllib2
import time

def lookup_cik(ticker):
    """
    Given a ticker symbol, retrieves the CIK.
    """
    ticker = ticker.strip().upper()
    
    # First try the SEC. In theory, should for all known symbols, even
    # deactivated ones. In practice, fails to work for many, even active ones.
    url = 'http://www.sec.gov/cgi-bin/browse-edgar?CIK={cik}&owner=exclude&Find=Find+Companies&action=getcompany'.format(cik=ticker)
    #print 'url1:',url
    response = urllib2.urlopen(url)
    data = response.read()
    try:
        match = re.finditer('CIK=([0-9]+)', data).next()
        return match.group().split('=')[-1]
    except StopIteration:
        pass
    
    # If the SEC search doesn't find anything, then try Yahoo.
    # Should work for all active symbols, but won't work for any deactive
    # symbols. 
    url = 'http://finance.yahoo.com/q/sec?s={symbol}+SEC+Filings'.format(symbol=ticker)
    #print 'url2:',url
    response = urllib2.urlopen(url)
    data = response.read()
    try:
        match = re.finditer('search/\?cik=([0-9]+)', data).next()
        return match.group().split('=')[-1]
    except StopIteration:
        pass
    