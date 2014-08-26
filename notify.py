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
        past_jobs = jobs
    else:
        # we have a known job state that we're comparing against, so load that.
        past_jobs = json.load(open(current_uri))

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
            li_template = '<li><a href="%s">%s</a></li>'
            links = [li_template % (job, current_jobs[job]) for job in new_jobs]
            return  '<ul>%s</ul>' % ''.join(links)

        changes_string = ''
        if len(new_jobs) > 0:
            changes_string += 'Added positions: '
            changes_string += build_ul(new_jobs)

        if len(removed_jobs) > 0:
            changes_string += 'Closed positions: '
            changes_string += build_ul(removed_jobs)

        message = message % changes_string
