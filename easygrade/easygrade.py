import json
import time
import sys
from pprint import pprint
from urllib.parse import parse_qs, urlparse

from lxml import html
from fsubot import FSUBot


def get_query_field(url, field):
    try:
        return parse_qs(urlparse(url).query)[field]
    except KeyError:
        return []


class EasyGradeBot(FSUBot):
    SMARTVIEWS_URL = "https://campus.fsu.edu/webapps/gradebook/do/instructor/manageCustomViews?course_id={}"
    SMARTVIEW_URL = "https://campus.fsu.edu/webapps/gradebook/do/instructor/viewSpreadsheet2?course_id={}&cvid={}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def main(self, course_id, smartview_names, assignment):
        portal_tab = self.dr.current_window_handle
        self.SLEEP_TIME = 0.5

        with open('pages.json') as f:
            pages = json.load(f)

        # must be a list
        portal_tab_json = [pages['pages'][0]] # not a list
        blackboard_tab_json = pages['pages'][1:] # already a list
        bot.navigate(json_list=portal_tab_json)

        blackboard_tab = [h for h in self.dr.window_handles if h != portal_tab][0]
        ignored_tabs = [portal_tab]

        self.dr.switch_to_window(blackboard_tab)
        bot.navigate(json_list=blackboard_tab_json)

	# should now be at list of all grades

        # useful for after switch to course_name
        #course_id = get_query_field(self.dr.current_url, "course_id")[0]

        smartview_listing_url = EasyGradeBot.SMARTVIEWS_URL.format(course_id)
        self.dr.get(smartview_listing_url)

        # getting smartview URLs
        tree = html.fromstring(self.page_source)

        smartview_table_rows_xpath = '//*[@id="listContainer_databody"]/tr'
        smartview_rows = tree.xpath(smartview_table_rows_xpath)
        smartview_ids = []

        for row in smartview_rows:
            smartview_element = row.getchildren()[1].getchildren()[0]
            if smartview_element.text.strip() not in smartview_names: continue
            smartview_id = smartview_element.attrib['href'].\
                           split('\'')[1].\
                           split('\'')[0]
            smartview_ids.append(smartview_id)

        # now, let's get the rows of students
        students = []
        student_table_rows_xpath = '//*[@id="listContainer_databody"]/tr'
        student_rows = tree.xpath(student_table_rows_xpath)

        for smartview_id in smartview_ids:
            self.dr.get(EasyGradeBot.SMARTVIEW_URL.format(course_id, smartview_id))
            smartview_tree = html.fromstring(self.page_source)

            # now, let's get the table header so we know which columns to select
            columns = []
            student_table_header_xpath = '//*[@id="table1_header"]/thead/tr/*'
            student_table_header = smartview_tree.xpath(student_table_header_xpath)
            for column in student_table_header[1:]:
                pprint(column.getchildren()[0].getchildren()[0].text)

            time.sleep(5)

        sys.exit()


if __name__ == '__main__':
    bot = EasyGradeBot(fsuid='', fsupw='!', browser={'title':'chrome','path':'../../../../../../../../../../../../usr/local/bin/chromedriver'})

    with open('download.json') as f:
        smartview_json = json.load(f)

    bot.main(
        smartview_json['course_id'], # eventually switch this to course name
        ["04_Pianka", "07_Pianka", "16_Pianka", "17_Pianka"],
        "Homework 1"
    )
