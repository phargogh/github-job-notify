import json
import os
import urllib2

from bs4 import BeautifulSoup

if __name__ == '__main__':
    jobs_html_doc = urllib2.urlopen('https://github.com/about/jobs').read()
    jobs_soup = BeautifulSoup(jobs_html_doc)

    open_positions = jobs_soup.find('div', 'jobs-open-positions').find_all('a')
    jobs = dict((job.string, job['href']) for job in open_positions)
    print jobs

    # If the list does not exist in JSON, save it.  We need to have an existing
    # record to be able to check
    current_uri = 'current_jobs.json'
    if not os.path.exists(current_uri):
        json.dump(jobs, open(current_uri, 'w'), indent=4,
            sort_keys=True)

