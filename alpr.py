# Python 2.7
from openalpr import Alpr
from slackclient import SlackClient 
import sys
import argparse
import sqlite3 # for both portable and I/O sensitive record keeping
import json
import os.path
import urllib
import time

DEBUGGING = True
SC = None
c = None

def sendSlackMessage(slackChannel, message):
    SC.api_call("chat.postMessage", channel=slackChannel, text=message)

def createTable():
    # Create table
    c.execute('''CREATE TABLE alpr (time int, records text, camera int)''')
    conn.commit()

def insertRow(time, records, camera):
    c.execute("INSERT INTO alpr VALUES ('{}','{}',{})".format(time, records.replace('"', '""'), camera))
    conn.commit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', nargs=1, help="SQLite DB File to use")
    parser.add_argument('--slack', nargs=2, help="Slack API token and channel")
    args = parser.parse_args()

    if(len(args.slack) == 2):
        SC = SlackClient(args.slack[0])

    # Create table if the DB file doesn't exist
    DB_FILE = args.db[0] if args.db else 'alprRecords.db'
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if(not os.path.isfile(DB_FILE)): createTable()

    # Set up image recognition
    alpr = Alpr("us", "/etc/openalpr/openalpr.conf", "/usr/share/openalpr/runtime_data/")
    if not alpr.is_loaded():
        print("Error loading OpenALPR")
        sys.exit(1)
    
    alpr.set_top_n(20)
    alpr.set_default_region("ca")

    # Begin ALPR
    currentCamera = 0 # 0 = L, 1 = R
    while True:
        # Timestamp for consistient record keeping
        currentTime = int(time.time())

        # File to be saved (possibly temporarily) for alpr
        alprImage = "./images/camera{}-{}.jpg".format(currentCamera, currentTime)
	
        # Save image from camera
        urllib.urlretrieve("http://localhost:808{}/?action=snapshot".format(currentCamera), alprImage)

        # Parse image into results
        results = alpr.recognize_file(alprImage)
        results_json = json.dumps(results)

        # Save if a match otherwise delete image
        if(results["results"]):
	    for plate in results["results"]:
                insertRow(currentTime, json.dumps(plate), currentCamera)

                if(DEBUGGING):
		    message = "Found plate: {}".format(json.dumps(plate["plate"]))
                    print(message)
		    if(SC): sendSlackMessage(args.slack[1], message)

        else:
            os.remove(alprImage)
        
        # Flip bit to other camera
        currentCamera = 1-currentCamera

        # Wait a bit
        time.sleep(1)

    # Call when completely done to release memory
    alpr.unload()
