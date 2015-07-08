import json
import os
import urllib2
import smtplib

from bs4 import BeautifulSoup


def get_jobs(html_doc):
    """Take an HTML doc (in a string) and parse out the jobs that are found.
    Returns a dictionary mapping {job title: job URI}."""

    # Assuming lxml to stop a warning on Linux.
    jobs_soup = BeautifulSoup(jobs_html_doc, "lxml")

    open_positions = jobs_soup.find('div', 'jobs-open-positions').find_all('a')
    jobs = dict((job.string, job['href']) for job in open_positions)
    return jobs

if __name__ == '__main__':
    jobs_html_doc = urllib2.urlopen('https://github.com/about/jobs').read()
    jobs = get_jobs(jobs_html_doc)

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


        def build_ul(jobs_set):
            li_template = '\t%s: %s'
            links = [li_template % (job, all_jobs[job]) for job in jobs_set]
            return  '\n'.join(links) + '\n\n'

        changes_string = ''
        if len(new_jobs) > 0:
            changes_string += 'Added positions:\n'
            changes_string += build_ul(new_jobs)

        if len(removed_jobs) > 0:
            changes_string += 'Closed positions:\n'
            changes_string += build_ul(removed_jobs)

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

