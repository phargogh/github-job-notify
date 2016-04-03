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


def _find_changes_to_jobs(json_filename, jobs_dict):
    # If the list does not exist in JSON, save it.  We need to have an
    # existing record to be able to check
    if not os.path.exists(current_uri):
        json.dump(jobs, open(current_uri, 'w'), indent=4,
                    sort_keys=True)
        past_jobs = jobs
    else:
        # we have a known job state that we're comparing against, so load that.
        past_jobs = json.load(open(current_uri))

    # write the current job state to JSON
    json.dump(jobs, open(current_uri, 'w'), indent=4, sort_keys=True)

    all_jobs = dict(jobs_dict.items() + past_jobs.items())
    known_jobs = set(past_jobs.keys())
    current_jobs = set(jobs_dict.keys())

    intersection = current_jobs.intersection(known_jobs)

    new_jobs = current_jobs - intersection
    removed_jobs = known_jobs - intersection
    return new_jobs, removed_jobs, all_jobs


def _format_email(jobs_dict):
    message_template = """
    Ahoy!  Some changes have been detected.  Here's the scoop:

    {company_sections}

    That's it for now!
    """

    company_section_template = """
    ****{company}****
        Added positions: {added_positions}

        Removed positions: {removed_positions}
    """

    company_sections = []
    for company, company_data in jobs_dict.iteritems():
        if len(company_data['added']) > 0:
            added_positions = [
                '\t{name}: {link}'.format(name=jobname, link=link)
                for jobname, link in company_data['added'].iteritems()]
            added_positions = '\n'.join(added_positions) + '\n\n'
        else:
            added_positions = 'None\n'

        if len(company_data['removed']) > 0:
            removed_positions = [
                '\t{name}'.format(name=jobname)
                for jobname, link in company_data['removed'].iteritems()]
            removed_positions = '\n'.join(removed_positions) + '\n\n'
        else:
            removed_positions = 'None\n'

        company_section = company_section_template.format(
            company=company,
            added_positions=added_positions,
            removed_positions=removed_positions)
        company_sections.append(company_section)

    return message_template.format(
        company_sections='\n\n'.join(company_sections))


if __name__ == '__main__':
    print gitlab()
    #sys.exit(0)

    parsers = [
        ('GitLab', gitlab),
        ('GitHub', github),
    ]
    current_uri_template = 'current_jobs_{name}.json'
    jobs_data = {}
    for company, parser in parsers:
        current_uri = current_uri_template.format(name=company.lower())
        jobs = parser()

        new_jobs, removed_jobs, all_jobs = _find_changes_to_jobs(current_uri,
                                                                 jobs)

        jobs_data[company] = {
            'added': new_jobs,
            'removed': removed_jobs,
            'all': all_jobs
        }

    message = _format_email(jobs_data)

    # build up an email to send
    # ASSUMES TWO THINGS:
    #  - localhost is an smtp server
    #  - there's a file in CWD that contains the target email address
    server = smtplib.SMTP('localhost')
    email_file = os.path.join(os.path.dirname(__file__),
                              'email_address.txt')
    email_address = open(email_file).read()
    server.sendmail(email_address, email_address, message)
