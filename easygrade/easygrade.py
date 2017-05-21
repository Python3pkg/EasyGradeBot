import errno
import json
import glob
import time
import os
import sys
from pprint import pprint
from urllib.parse import parse_qs, urlparse

import selenium.webdriver.support.ui as ui
from selenium.common.exceptions import WebDriverException, ElementNotVisibleException, ElementNotVisibleException
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

    def __init__(self, *args, download_dir=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.download_dir = download_dir

    def main(self, course_name, smartview_names, columns):
        portal_tab = self.dr.current_window_handle
        self.SLEEP_TIME = 0.5

        bot._click(title="BlackBoard", xpath="//*[@id=\"link_icon_197\"]")
        time.sleep(0.5)
        blackboard_tab = [h for h in self.dr.window_handles if h != portal_tab][0]
        ta_courses_xpath = '//*[@id="_4_1termCourses_noterm"]/ul[2]/li[*]/a'
        self.dr.switch_to_window(blackboard_tab)
        self.wait.until(lambda driver: driver.find_element_by_xpath(ta_courses_xpath))
        # get course_id from course_name
        for course_li in self.dr.find_elements_by_xpath(ta_courses_xpath):
            if str(course_name) == str(course_li.text):
                self.course_id = course_li.get_attribute("href").split('id=')[1].split('&')[0]
                break
        else:
            print("Unable to locate course. Ensure it exactly matches the text under \"Courses where you are: Teaching Assistant\".")
            sys.exit()

        smartview_listing_url = EasyGradeBot.SMARTVIEWS_URL.format(self.course_id)
        self.dr.get(smartview_listing_url)
        self.wait.until(lambda driver: driver.find_element_by_xpath(
            '//*[@id="nav"]/li/a'
        ))

        # getting smartview URLs
        tree = html.fromstring(self.page_source)
        smartview_table_rows_xpath = '//*[@id="listContainer_databody"]/tr'
        smartview_rows = tree.xpath(smartview_table_rows_xpath)
        smartviews = []

        for row in smartview_rows:
            _smartview_element = row.getchildren()[1].getchildren()[0]
            _smartview_name = _smartview_element.text.strip()
            if _smartview_name not in smartview_names: continue
            _smartview_id = _smartview_element.attrib['href'].\
                           split('\'')[1].\
                           split('\'')[0]
            smartviews.append((_smartview_id, _smartview_name))
        while(1):
            print("Which Smart View Assignments would you like to download?")
            for i, smartview in enumerate(smartviews):
                print(("{}. \"{}\"".format(i+1, smartview[1])))

            try:
                choice_num = int(eval(input("--> ")))
                if choice_num == 0:
                    print("Exiting.")
                    self.dr.close()
                    sys.exit()
                elif choice_num not in list(range(1, len(smartviews) + 1)): continue
            except (ValueError, TypeError):
                continue

            smartview_id = smartviews[choice_num - 1][0]
            try:
                print("==========================================")
                self.download_smartview(smartview_id, smartviews[choice_num - 1][1], columns)
            except (KeyboardInterrupt, WebDriverException) as e:
                print(("{}: exiting that Smart View.".format(str(e))))
            finally:
                print("\n==========================================")

            self.dr.get(smartview_listing_url)
            self.wait.until(lambda driver: driver.find_element_by_xpath(
                '//*[@id="nav"]/li/a'
            ))

        # fin
        sys.exit(0)

    def download_smartview(self, smartview_id, smartview_name, columns):
        # get and wait for page load (hopefully 3 is enough)
        self.dr.get(EasyGradeBot.SMARTVIEW_URL.format(self.course_id, smartview_id))
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
                'First Name': firstname,
                'Last Name': lastname,
                'Submissions': []
            }

            for column_id, column_name in list(column_ids.items()):
                student['Submissions'].append({
                    'Title': column_name,
                    'Filename': None,
                    'Row': row_id,
                    'Column': column_id,
                    'Downloaded': False,
                    'Score': -1
                })

            students.append(student)

        smartview_dir = EasyGradeBot._create_dir(os.path.join(self.download_dir, smartview_name))

        cell_id = "cell_{}_{}"
        for i, student in enumerate(students):
            print(("{} {}".format(student['First Name'], student['Last Name'])))
            for j, submission in enumerate(student['Submissions']):
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
                #latest_attempt_row = len(self.dr.find_elements_by_xpath(
                #    '//*[@id="attemptsTable"]/tbody/tr[contains(@id,"attemptRow")]'
                #)) - 1
                latest_attempt_row = 0


                attempt_url = "https://campus.fsu.edu/webapps/assignment/gradeAssignmentRedirector?anonymousMode=false&course_id={}&attempt_id={}"
                attempt_row_xpath = '//*[@id="attemptsTable"]/tbody/tr[contains(@id,"attemptRow{}")]'

                try:
                    try:
                        attempt_row = self.dr.find_element_by_xpath(
                            attempt_row_xpath.format(latest_attempt_row)
                        )
                    except (WebDriverException, ElementNotVisibleException, ElementNotVisibleException):
                        # View Grade Details contains no attempts, go back
                        self.dr.get(EasyGradeBot.SMARTVIEW_URL.format(self.course_id, smartview_id))
                        self.wait.until(lambda driver: driver.find_element_by_xpath(
                            '//*[@id="cell_0_3"]/div/div[1]/div/a'
                        ))
                        continue

                    attempt_row_id = attempt_row.get_attribute("id")

                    submit_date = attempt_row.find_element_by_xpath(
                        '//*[@id="{}"]/td[1]/div'.format(attempt_row_id)
                    ).text

                    attempt_id = attempt_row.find_element_by_xpath(
                        '//*[@id="{}"]/td[6]/div/a[1]'.format(
                            attempt_row_id
                        )
                    ).get_attribute("onclick").split("'")[1].split("'")[0]

                    self.dr.get(attempt_url.format(self.course_id, attempt_id))
                    self.wait.until(lambda driver: driver.find_element_by_xpath(
                        '//*[@id="currentAttempt_submission"]/h4'
                    ))

                    try:
                        self.dr.find_element_by_xpath(
                            '//*[@id="downloadPanelButton"]'
                        ).click()
                    except (WebDriverException, ElementNotVisibleException, ElementNotVisibleException):
                        self.dr.find_element_by_xpath(
                            '//*[@id="currentAttempt_submissionList"]/li/div/a'
                        ).click()
                    except (WebDriverException, ElementNotVisibleException, ElementNotVisibleException):
                        self.dr.find_element_by_xpath(
                            '//*[@id="currentAttempt_submissionList"]/li[2]/div/a'
                        ).click()
                    except (WebDriverException, ElementNotVisibleException, ElementNotVisibleException):
                        self.dr.execute_script('window.history.go(-1)')
                        self.dr.execute_script('window.history.go(-1)')
                        continue


                    _escape_chars = EasyGradeBot._make_escape_chars(r""")+}=\\>@[~:$#,"?{^*<%\'!|/(]&;`""")

                    filename = EasyGradeBot._move_to_subfolder(
                        self.download_dir,
                        _escape_chars(smartview_name),
                        add_on=str(i)
                    )
                    student['Submissions'][j]['Filename'] = filename
                    student['Submissions'][j]['Downloaded'] = True
                    time.sleep(1.2)
                except (WebDriverException, ElementNotVisibleException, ElementNotVisibleException) as e:
                    print(("{}: Bailing on submission at ({}, {}) by {}.".format(
                        str(e), submission['Row'], submission['Column'],
                        ' '.join([student['First Name'], student['Last Name']])
                        )
                    ))

                    self.dr.execute_script('window.history.go(-1)')
                    self.dr.execute_script('window.history.go(-1)')
                    continue

                self.dr.execute_script('window.history.go(-1)')
                self.dr.execute_script('window.history.go(-1)')
                self.wait.until(lambda driver: driver.find_element_by_css_selector(
                    'td#cell_{}_{}'.format(
                        submission['Row'], submission['Column']
                    )
                ))

        with open(os.path.join(os.path.join(self.download_dir, smartview_name), 'students.json'), 'w') as f:
            json.dump(students, f, indent=2)
        time.sleep(1)

    @staticmethod
    def _move_to_subfolder(download_dir, subfolder, auto_download=False, auto_skip=False, add_on=None):
        """ Move a downloaded submission to it's own submit folder.

        :param download_dir: where the old file is located
        :type download_dir: str

        :param new_filename: new filename, includes new folders
        :type new_filename: str

        :param file_extension: file extension of the new file
        :type file_extension: str

        """
        attempts = 0
        done_checking = False
        while 1:
            try:
                fname = [f for f in EasyGradeBot._os_list_dir_files(download_dir) if os.path.splitext(f)[1] == '.cpp'][0]
                break
                #raise WebDriverException("Found file without matching extension.")
            except IndexError:
                if attempts == 2:
                    try:
                        fname = [f for f in EasyGradeBot._os_list_dir_files(download_dir)][0]
                    except IndexError:
                        return "DOWNLOAD FAILED"

                    if auto_download:
                        break
                    elif auto_skip:
                        return "DOWNLOAD FAILED"
                    while 1:
                        print("This submission contains a file with the wrong "
                              "extension, what would you like to do?\n"
                              "1. Skip\n2. Download")
                        try:
                            choice = int(eval(input('--> ')))
                            if choice not in [1, 2]:
                                raise ValueError
                        except ValueError:
                            continue

                        if choice == 1:
                            return "DOWNLOAD FAILED"
                        elif choice == 2:
                            done_checking = True
                            break

                if done_checking: break
                attempts += 1
                time.sleep(1.5)
                continue

        filename = os.path.split(fname)[1]
        if add_on:
            filename = ''.join(['_'.join([os.path.splitext(filename)[0], add_on]), os.path.splitext(filename)[1]])
        print(("Moving \"{}\"...".format(filename)))
        new_file = os.path.join(download_dir, subfolder, filename)
        print((download_dir, subfolder, filename))
        print(new_file)
        # make sure it exists
        EasyGradeBot._create_dir(os.path.join(download_dir, subfolder))
        os.rename(fname, new_file)
        print("Moved.")
        return filename

    @staticmethod
    def _make_escape_chars(esc_chars):
        return lambda s: ''.join(['\\' + c if c in esc_chars else c for c in s])

    @staticmethod
    def _os_list_dir_files(root):
        """
        returns list containing absolute paths to files (only) in directory
        """
        return [
            os.path.join(root, fname) for fname in os.listdir(root)
            if not os.path.isdir(os.path.join(root, fname))
        ]

    @staticmethod
    def _create_dir(dir_name):
        """ Safely create a new directory.

        :param dir_name: directory name
        :type dir_name: str

        :return: str, name of the new directory
        """
        try:
            os.makedirs(dir_name)
            return dir_name
        except OSError as e:
            if e.errno != errno.EEXIST:
                print((str(e)))
                raise OSError('Unable to create directory.')


if __name__ == '__main__':
    chrome_options = webdriver.ChromeOptions()

    # ensure this directory is empty
    download_dir = os.path.join(os.path.expanduser("~"), "Downloads/assignments")
    prefs = {"download.default_directory" : download_dir}
    chrome_options.add_experimental_option("prefs", prefs)


    driver = webdriver.Chrome(
        executable_path='../drivers/chromedriver',
        chrome_options=chrome_options
    )


    try:
        from config import fsuid, fsupw
    except ImportError:  # no config.py file exists
        fsuid, fsupw = '', ''

    bot = EasyGradeBot(
        fsuid=fsuid, fsupw=fsupw,
        driver=driver, download_dir=download_dir
    )

    with open('download.json') as f:
        d_json = json.load(f)

    bot.main(
        d_json['course_name'], # eventually switch this to course name
        d_json['smartview_names'],
        d_json['column_names']
    )
