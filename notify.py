import json
import os
import urllib2
import smtplib
import sys
import argparse
import warnings
import logging

from bs4 import BeautifulSoup

logging.basicConfig()
LOGGER = logging.getLogger()


def _get_page(url):
    request = urllib2.Request(
        url, headers={'User-Agent': 'Wget/1.13.4 (linux-gnu)'})
    return urllib2.urlopen(request).read()


def basecamp():
    url = 'https://basecamp.com/about/jobs'
    jobs_soup = BeautifulSoup(_get_page(url), 'lxml')
    open_positions = jobs_soup.find('main').find('ul').find_all('a')
    jobs = dict((job.string, job['href']) for job in open_positions)
    return jobs


def gitlab():
    url = 'https://about.gitlab.com/jobs'
    jobs_soup = BeautifulSoup(_get_page(url), 'lxml')
    open_positions = jobs_soup.find(
        'div', class_='container md-page').find_all('h3')
    jobs = dict(
        (job.string,
         url + job.find_next_sibling('ul').find('li').a['href'].replace(
             'jobs/', ''))
        for job in open_positions)
    return jobs


def github():
    url = 'https://github.com/about/careers'
    jobs_soup = BeautifulSoup(_get_page(url), "lxml")

    open_positions = jobs_soup.find_all('ul', 'list-unstyled', 'li')
    jobs = dict((job.find('a').string, job.find('a')['href'])
                for job in open_positions)
    return jobs


def atlassian():
    base_url = ('https://careers.smartrecruiters.com/Atlassian/'
                '?search=&page=0&location=')
    jobs = {}
    for city in ['San Francisco', 'Palo Alto', 'Santa Clara', 'Mountain View']:
        url = base_url + city.replace(' ', '%20')
        try:
            jobs_soup = BeautifulSoup(_get_page(url), "lxml")
        except urllib2.HTTPError as error:
            warnings.warn('%s: %s' % (url, error))
            continue
        except Exception as error:
            # allow to continue, but log the error.
            warnings.warn(str(error))
            continue

        try:
            open_positions = jobs_soup.find(
                'ul', class_='opening-jobs').find_all('a')
        except AttributeError:
            # When there are no job postings available for this city.
            continue

        job_location = ' (%s)' % city
        for job in open_positions:
            title = job.h3.string
            jobs[title + job_location] = job['href']

    return jobs


def etsy():
    etsy = 'https://www.etsy.com'
    url = etsy + '/careers/'
    jobs_soup = BeautifulSoup(_get_page(url), "lxml")

    open_positions = jobs_soup.find(
        'div', class_='positions').find_all('a')
    jobs = dict((job.string, etsy + job['href']) for job in open_positions
                if job.string)
    return jobs


def _find_changes_to_jobs(json_filename, jobs_dict):
    # If the list does not exist in JSON, save it.  We need to have an
    # existing record to be able to check
    if not os.path.exists(current_uri):
        past_jobs = {}
    else:
        # we have a known job state that we're comparing against, so load that.
        past_jobs = json.load(open(current_uri))

    # write the current job state to JSON
    json.dump(jobs_dict, open(current_uri, 'w'), indent=4, sort_keys=True)

    all_jobs = dict(jobs_dict.items() + past_jobs.items())
    known_jobs = set(past_jobs.keys())
    current_jobs = set(jobs_dict.keys())

    intersection = current_jobs.intersection(known_jobs)

    new_jobs = current_jobs - intersection
    removed_jobs = known_jobs - intersection
    return new_jobs, removed_jobs, all_jobs


def _format_email(jobs_dict):
    message_template = u"""
    Ahoy!  Some changes have been detected.  Here's the scoop:

    {company_sections}

    That's it for now!
    """

    company_section_template = u"""
    ****{company}****
        Added positions: \n{added_positions}

        Removed positions: \n{removed_positions}
    """
    company_sections = []
    for company, company_data in jobs_dict.iteritems():
        # Skip this company if there were no changes.
        if len(company_data['added']) + len(company_data['removed']) == 0:
            continue

        if len(company_data['added']) > 0:
            added_positions = [
                u'\t{name}: {link}'.format(name=jobname,
                                           link=company_data['all'][jobname])
                for jobname in company_data['added']]
            added_positions = u'\n'.join(added_positions) + '\n\n'
        else:
            added_positions = u'\tNone\n'

        if len(company_data['removed']) > 0:
            removed_positions = [
                '\t{name}'.format(name=jobname)
                for jobname in company_data['removed']]
            removed_positions = u'\n'.join(removed_positions) + '\n\n'
        else:
            removed_positions = u'\tNone\n'

        company_section = company_section_template.format(
            company=company,
            added_positions=added_positions,
            removed_positions=removed_positions)
        company_sections.append(company_section)

    return message_template.format(
        company_sections='\n\n'.join(company_sections))


if __name__ == '__main__':
    parsers = [
        ('Atlassian', atlassian),
        ('Basecamp', basecamp),
        ('Etsy', etsy),
        ('GitLab', gitlab),
        ('GitHub', github),
    ]
    parser = argparse.ArgumentParser(description=(
        'Parse known job sites and assemble a message to be printed or '
        'emailed.  Parses job pages for : {companies}').format(
        companies=', '.join([a[0] for a in parsers])))
    parser.add_argument('--email', metavar='EMAIL', default=False, help=(
        'Send the report via email to the given address.  Assumes localhost '
        'is an SMTP server.  If not provided, the formatted message will be '
        'printed to stdout.')
    )
    parser.add_argument('company', metavar='company', default='all', nargs='*',
                        help=('Only report these companies.  If no companies '
                              'are provided, all companies will be scraped.'))
    parser.add_argument('--always', action='store_true', default=False,
                        help=('Always produce a message.  Default is to only '
                              'produce a message if a change has been '
                              'detected.'))
    args = parser.parse_args()

    current_uri_template = 'current_jobs_{name}.json'
    jobs_data = {}
    for company, parser in parsers:
        # if the user defined companies to use, skip anything that doesn't
        # match the user's requested companies.
        if (company.lower() not in args.company) and args.company != 'all':
            continue

        current_uri = current_uri_template.format(name=company.lower())
        try:
            jobs = parser()
        except Exception as error:
            LOGGER.exception('Traceback while parsing company %s', company)
            continue

        new_jobs, removed_jobs, all_jobs = _find_changes_to_jobs(current_uri,
                                                                 jobs)

        jobs_data[company] = {
            'added': new_jobs,
            'removed': removed_jobs,
            'all': all_jobs
        }

    # Only send an email if jobs changed.
    if sum([(len(data['added']) + len(data['removed'])) > 0
            for data in jobs_data.values()]) > 0 or args.always:
        message = _format_email(jobs_data)

        if not args.email:
            print message
            sys.exit(0)
        else:
            # build up an email to send
            # ASSUMES TWO THINGS:
            #  - localhost is an smtp server
            #  - there's a file in CWD that contains the target email address
            server = smtplib.SMTP('localhost')
            email_filepath = os.path.join(os.path.dirname(__file__),
                                          'email_address.txt')
            with open(email_filepath) as email_file:
                for line in email_file:
                    address = line.strip()
                    server.sendmail(address, address, message)
