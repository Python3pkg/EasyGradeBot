import json
import time
import sys
from pprint import pprint
from urllib.parse import parse_qs, urlparse

from selenium.webdriver.common.action_chains import ActionChains
from lxml import html
from fsubot import FSUBot

try:
    from config import fsuid, fsupw
except ImportError:  # no config file set
    pass


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

    def main(self, course_id, smartview_names, columns):
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


        for smartview_id in smartview_ids:
            # get and wait for page load (hopefully 3 is enough)
            self.dr.get(EasyGradeBot.SMARTVIEW_URL.format(course_id, smartview_id))
            time.sleep(3)

            # create tree to parse
            smartview_tree = html.fromstring(self.page_source)

            # grab header to ascertain needed column (and store indexes)
            column_ids = {}
            student_table_header_css_selector = '#table1_header > thead > tr > th'
            student_table_header = smartview_tree.cssselect(
                student_table_header_css_selector
            )[1:]
            for i, column in enumerate(student_table_header):
                column_div = column.getchildren()[0].getchildren()[0].getchildren()[0]
                if column_div.text in columns:
                    # since we're skipping the first column
                    column_ids[i+1] = column_div.text

            # submissions will collect URLs to download the assignments
            students = []
            student_table_rows_css_selector = '#table1 > tbody > tr'
            student_rows = smartview_tree.cssselect(
                student_table_rows_css_selector
            )

            # now, let's get all of the items in the necessary columns
            for row_id in range(len(student_rows)):
                lastname, firstname = [
                    smartview_tree.cssselect(
                        '#cell_{}_{} > div > div.gbView > div > a'\
                        .format(row_id, i)
                    )[0].text for i in [1, 2]
                ]

                student = {
                    'Last Name': lastname,
                    'First Name': firstname,
                    'Submissions': [

                    ]
                }

                for column_id, column_name in column_ids.items():
                    dropdown_btn = self.dr.find_element_by_id(
                        'cmlink_{}{}'.format(row_id, column_id)
                    )
                    student['Submissions'].append({
                        'Title': column_name,
                        'Row': row_id,
                        'Column': column_id,
                        'Dropdown': dropdown_btn
                    })

                students.append(student)


            cell_id = "cell_{}_{}"

            for student in students:
                for submission in student['Submissions']:
                    cell = self.dr.find_element_by_css_selector(
                        'td#cell_{}_{}'.format(
                            submission['Row'], submission['Column']
                        )
                    ).click()
                    time.sleep(1.5)
                    dropdown_btn = self.dr.find_element_by_css_selector(
                        'tr#cmlink_{}{} > img'.format(
                            submission['Row'], submission['Column']
                        )
                    )
                    dropdown_btn.click()
                    #submission['Dropdown'].click()
                    #anchor.click()
                    #attempt = self.dr.find_element_by_css_selector(
                    #    '#context_menu_tag_item1_{}{}'.format(
                    #        anchor['Row'], anchor['Column']
                    #    )
                    #)
                    #print(attempt)
                    time.sleep(5)


            time.sleep(5)

        sys.exit()


if __name__ == '__main__':
    mbpath = '../../../../../../../../../../../../usr/local/bin/chromedriver'
    calderapath = '../drivers/chromedriver'
    bot = EasyGradeBot(
        fsuid=fsuid, fsupw=fsupw,
        browser={
            'title': 'chrome',
            'path' :calderapath
        }
    )

    with open('download.json') as f:
        smartview_json = json.load(f)

    bot.main(
        smartview_json['course_id'], # eventually switch this to course name
        ["04_Pianka", "07_Pianka", "16_Pianka", "17_Pianka"],
        ["Homework 1"]
    )
