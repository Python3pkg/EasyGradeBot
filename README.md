# EasyGradeBot
A bot designed to interact with BlackBoard, aidding in downloading large numbers of assignments for students within a BlackBoard "Smart View".

### How to use:

1. Clone the repository.

    `$ git clone https://github.com/seanpianka/easygradebot.git`

2. Install the requirements.

    `$ cd EasyGradeBot && pip install -r requirements.txt`

3. Open `download.json` and enter in the names for your SmartViews, the name of the columns to download, and the FSU course name (exactly as it appears on the main BlackBoard page on the right-side column).

4. Run the bot and provide your login credentials.

    `$ python easygrade.py`

5. The assignments will be saved in individual directories: `~/Downloads`.

#### Requirements:
```
appdirs==1.4.0
cssselect==1.0.1
fsubot==0.2.11
lxml==3.7.2
packaging==16.8
pyparsing==2.1.10
selenium==3.0.2
six==1.10.0
```
