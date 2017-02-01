import json

from fsubot import FSUBot


class EasyGradeBot(FSUBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def main(self):
        portal_tab = self.dr.current_window_handle

        with open('pages.json') as f:
            pages = json.load(f)

        # must be a list
        portal_tab_json = [pages['pages'][0]] # not a list
        blackboard_tab_json = pages['pages'][1:] # already a list
        bot.navigate(json_list=portal_tab_json)

        blackboard_tab = [h for h in self.dr.window_handles if h != portal_tab][0]
        self.dr.switch_to_window(blackboard_tab)
        bot.navigate(json_list=blackboard_tab_json)

        ignored_tabs = [portal_tab]


if __name__ == '__main__':
    bot = EasyGradeBot(browser={'title':'chrome','path':'../drivers/chromedriver'})
    bot.setup()
