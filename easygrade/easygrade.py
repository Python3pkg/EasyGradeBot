import json

from fsubot import FSUBot


class EasyGradeBot(FSUBot):
    SMARTVIEWS_URL = "https://campus.fsu.edu/webapps/gradebook/do/instructor/manageCustomViews?course_id={}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def main(self):


if __name__ == '__main__':
    bot = EasyGradeBot(browser={'title':'chrome','path':'../../../../../../../../../../../usr/local/bin/chromedriver'})
    bot.main(course_ids, course_url)
