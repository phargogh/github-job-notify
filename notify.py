import json
import urllib2

from bs4 import BeautifulSoup

if __name__ == '__main__':
    jobs_html_doc = urllib2.urlopen('https://github.com/about/jobs').read()
    jobs_soup = BeautifulSoup(jobs_html_doc)

    open_positions = jobs_soup.find('div', 'jobs-open-positions').find_all('a')
    jobs = dict((job.string, job['href']) for job in open_positions)
    print jobs


