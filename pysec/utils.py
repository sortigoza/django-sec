import re
import urllib2
import time

def lookup_cik(ticker):
    """
    Given a ticker symbol, retrieves the CIK.
    """
    ticker = ticker.strip().upper()
    url = 'http://www.sec.gov/cgi-bin/browse-edgar?CIK={cik}&owner=exclude&Find=Find+Companies&action=getcompany'.format(cik=ticker)
    response = urllib2.urlopen(url)
    data = response.read()
    try:
        match = re.finditer('CIK=([0-9]+)', data).next()
        return match.group().split('=')[-1]
    except StopIteration:
        return
    