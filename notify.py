import json
import os
import urllib2
import smtplib
import sys
import codecs

from bs4 import BeautifulSoup
import requests

def _get_page(url):
    return urllib2.urlopen(url).read()


def gitlab():
    url = 'https://about.gitlab.com/jobs/'
    jobs_soup = BeautifulSoup(_get_page(url), 'lxml')
    open_positions = jobs_soup.find(
        'div', class_='container md-page').find_all('h3')
    jobs = dict(
        (job.string, job.find_next_sibling('ul').find('li').a['href'])
        for job in open_positions)
    return jobs


def github():
    url = 'https://github.com/about/jobs'
    jobs_soup = BeautifulSoup(_get_page(url), "lxml")

    open_positions = jobs_soup.find('div', 'jobs-open-positions').find_all('a')
    jobs = dict((job.string, job['href']) for job in open_positions)
    return jobs


def atlassian():
    #import dryscrape
    url = ("https://www.atlassian.com/company/careers/all-jobs?"
           "team=Engineering&location=San%20Francisco")
    url = "https://careers.smartrecruiters.com/Atlassian"
    url = "https://careers.smartrecruiters.com/Atlassian?search=san%20francisco"
    url = "https://www.atlassian.com/company/careers/locations/san-francisco"
    url = "https://www.atlassian.com/company/careers/all-jobs"

    data = {
        'team': 'Engineering',
        'location': 'San Francisco'
    }
    response = requests.post(url, data=data)
    html = response.content

    #session = dryscrape.Session(base_url=url)
    #session.interact()
    #query = session.at_xpath('//*[@name="searchForm"]')
    #query.form().submit()
    #html = session.body()
    print html
    jobs_soup = BeautifulSoup(html, "lxml")
    codecs.open('atlassian.html', 'wb', 'utf-8').write(html)

    #open_positions = jobs_soup.find('table', class_='careers-job-list').find_all('a')
    open_positions = jobs_soup.find('div', class_='all-job-groups').find_all('a')
    jobs = dict((job.string, job['href']) for job in open_positions)
    return jobs


if __name__ == '__main__':
    #print atlassian()
    #sys.exit(0)

    jobs = github()

    # If the list does not exist in JSON, save it.  We need to have an existing
    # record to be able to check
    current_uri = 'current_jobs.json'
    if not os.path.exists(current_uri):
        json.dump(jobs, open(current_uri, 'w'), indent=4,
            sort_keys=True)
        past_jobs = jobs
    else:
        # we have a known job state that we're comparing against, so load that.
        past_jobs = json.load(open(current_uri))

    # write the current job state to JSON
    json.dump(jobs, open(current_uri, 'w'), indent=4, sort_keys=True)

    all_jobs = dict(jobs.items() + past_jobs.items())
    known_jobs = set(past_jobs.keys())
    current_jobs = set(jobs.keys())

    intersection = current_jobs.intersection(known_jobs)

    new_jobs = current_jobs - intersection
    removed_jobs = known_jobs - intersection

    if len(new_jobs) > 0 or len(removed_jobs) > 0:
        message = """
        Ahoy!  Some changes have been detected in github's job page.  Here's the scoop:

        %s

        That's it for now!
        """

        def build_ul(jobs_set, link=True):
            if link:
                links = ['\t%s: %s' % (job, all_jobs[job]) for job in jobs_set]
            else:
                links = ['\t%s' % job for job in jobs_set]
            return '\n'.join(links) + '\n\n'

        changes_string = ''
        if len(new_jobs) > 0:
            changes_string += 'Added positions:\n'
            changes_string += build_ul(new_jobs)

        if len(removed_jobs) > 0:
            changes_string += 'Closed positions:\n'
            changes_string += build_ul(removed_jobs, link=False)

        message = message % changes_string

        # build up an email to send
        # ASSUMES TWO THINGS:
        #  - localhost is an smtp server
        #  - there's a file in CWD that contains the target email address
        server = smtplib.SMTP('localhost')
        email_file = os.path.join(os.path.dirname(__file__),
            'email_address.txt')
        email_address = open(email_file).read()
        server.sendmail(email_address, email_address, message)

