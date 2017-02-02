import json
import time
import os
import sys
from pprint import pprint
from urllib.parse import parse_qs, urlparse

import selenium.webdriver.support.ui as ui
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
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

    def main(self, course_name, smartview_names, columns):
        portal_tab = self.dr.current_window_handle
        self.SLEEP_TIME = 0.5

        bot._navigate(title="BlackBoard", xpath="//*[@id=\"link_icon_197\"]")
        blackboard_tab = [h for h in self.dr.window_handles if h != portal_tab][0]
        ta_courses_xpath = '//*[@id="_4_1termCourses_noterm"]/ul[2]/li[*]/a'
        self.dr.switch_to_window(blackboard_tab)
        self.wait.until(lambda driver: driver.find_element_by_xpath(ta_courses_xpath))
        # get course_id from course_name
        for course_li in self.dr.find_elements_by_xpath(ta_courses_xpath):
            if str(course_name) == str(course_li.text):
                course_id = int(course_li.get_attribute("href").split('id=')[1].split('&')[0])
                break
        else:
            print("Unable to locate course. Ensure it exactly matches the text under \"Courses where you are: Teaching Assistant\".")
            sys.exit()

        smartview_listing_url = EasyGradeBot.SMARTVIEWS_URL.format(course_id)
        self.dr.get(smartview_listing_url)
        self.wait.until(lambda driver: driver.find_element_by_xpath(
            '//*[@id="nav"]/li/a'
        ))

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
            self.wait.until(lambda driver: driver.find_element_by_xpath(
                '//*[@id="cell_0_3"]/div/div[1]/div/a'
            ))

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
            student_rows = smartview_tree.cssselect(
                '#table1 > tbody > tr'
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
                    student['Submissions'].append({
                        'Title': column_name,
                        'Row': row_id,
                        'Column': column_id,
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
                    time.sleep(0.5)
                    # click dropdown to make "View Grade Details" element visible
                    self.dr.find_element_by_css_selector(
                        'a#cmlink_{}{}'.format(
                            submission['Row'], submission['Column']
                        )
                    ).click()
                    time.sleep(0.5)

                    # navigate to view grade details
                    [a for a in self.dr.find_elements_by_xpath(
                        '//*[@id="context_menu_tag_item1_{}{}"]'.format(
                            submission['Row'], submission['Column']
                        )
                    ) if "View Grade Details" in a.get_attribute("title")][0].click()

                    # entering grade details page
                    latest_attempt_row = len(self.dr.find_elements_by_xpath(
                        '//*[@id="attemptsTable"]/tbody/tr[contains(@id,"attemptRow")]'
                    )) - 1

                    attempt_url = "https://campus.fsu.edu/webapps/assignment/gradeAssignmentRedirector?anonymousMode=false&course_id={}&attempt_id={}"
                    attempt_row_xpath = '//*[@id="attemptsTable"]/tbody/tr[contains(@id,"attemptRow{}")]'

                    attempt_row = self.dr.find_element_by_xpath(
                        attempt_row_xpath.format(latest_attempt_row)
                    )
                    attempt_row_id = attempt_row.get_attribute("id")

                    submit_date = attempt_row.find_element_by_xpath(
                        '//*[@id="{}"]/td[1]/div'.format(attempt_row_id)
                    ).text

                    attempt_id = attempt_row.find_element_by_xpath(
                        '//*[@id="{}"]/td[6]/div/a[1]'.format(
                            attempt_row_id
                        )
                    ).get_attribute("onclick").split("'")[1].split("'")[0]

                    self.dr.get(attempt_url.format(course_id, attempt_id))
                    self.wait.until(lambda driver: driver.find_element_by_xpath(
                        '//*[@id="downloadPanelButton"]'
                    ))
                    download_btn = self.dr.find_element_by_xpath(
                        '//*[@id="downloadPanelButton"]'
                    )
                    download_btn.click()
                    self.dr.execute_script('window.history.go(-1)')

                    self.dr.execute_script('window.history.go(-1)')
                    self.wait.until(lambda driver: driver.find_element_by_css_selector(
                        'td#cell_{}_{}'.format(
                            submission['Row'], submission['Column']
                        )
                    ))
            time.sleep(1)

        sys.exit()


if __name__ == '__main__':
    chrome_options = webdriver.ChromeOptions()
    download_dir = os.path.join(os.path.expanduser("~"), "Downloads/assignments")
    prefs = {"download.default_directory" : download_dir}
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(
        executable_path='/usr/local/bin/chromedriver',
        chrome_options=chrome_options
    )

    try:
        from config import fsuid, fsupw
    except ImportError:  # no config file set
        fsuid, fsupw = '', ''

    bot = EasyGradeBot(
        fsuid=fsuid, fsupw=fsupw,
        driver=driver,
    )

    with open('download.json') as f:
        d_json = json.load(f)

    bot.main(
        d_json['course_name'], # eventually switch this to course name
        d_json['smartview_names'],
        d_json['column_names']
    )
