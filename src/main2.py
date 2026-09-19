import tkinter as tk
import platform
from member import *
import excel_handler as XlsxHandler
import statistics_handler as StatLogger
import gui_module as GUI
from datetime import datetime, timedelta
import sys
import os

message_update_time_short = 2
message_update_time_long = 5
time_to_wait = 5
latest_message_time = datetime.now()

# Function to maximize the Tkinter window
def maximize_window(root):
    if platform.system() == 'Darwin':  # macOS
        root.attributes('-zoomed', True)
    else:  # Windows and Linux
        root.attributes('-fullscreen', True)

def setStateVariables(time_str):
    global latest_message_time
    latest_message_time = datetime.strf(time_str)

def exitProgram():
    sys.exit()

def secondCounter(datetime_wait_until):
    return str(int((datetime_wait_until - datetime.now()).seconds) + 1)

def mvIncheckadePNG():
    nbr_checked_in_members = len(Member.checked_in_members)
    nbr_checked_in_styret = len(Member.checked_in_styret)
    if nbr_checked_in_members < 11:
        copyfile(res_path + nbr_checked_in_members + '.png',
                   webpage_resources_path + 'incheckade.png')
    else:
        copyfile(res_path + 'fler.png', webpage_resources_path + 'incheckade.png')

    if nbr_checked_in_styret < 11:
        copyfile(res_path + nbr_checked_in_styret + '.png', webpage_resources_path + 'styret.png')
    else:
        copyfile(res_path + 'fler.png', webpage_resources_path + 'styret.png' )

def timedFunctions():
    time_now = datetime.now() 
    time_now_str = time_now.strftime("%H:%M:%S")
    if  time_now_str >= ('04:00:00') and \
        time_now_str <= ('05:00:10') and \
        (XlsxHandler.latest_save + timedelta(hours = 2) < time_now): 
        message_string = "Updating registers, please hold..."
        GUI.message(message_string)
        XlsxHandler.saveStatistics()
        StatLogger.resetCheckins()
        XlsxHandler.cleanEarliestLoggbook()
        XlsxHandler.importNewMembers()
        XlsxHandler.saveAllCheckedinToLog()
        Member.clearCheckedIn()
        XlsxHandler.initBoardMemberRegister()
        XlsxHandler.initMemberRegister()
        GUI.initPictures()
        GUI.updateNames(Member.checked_in_members, 'member')
        GUI.updateNames(Member.checked_in_styret, 'styret')
        GUI.hideMessage()
        
commands = {
    'exit' : exitProgram,
    'clear' : Member.clearCheckedIn,
    'save' : XlsxHandler.save,
    'update' : XlsxHandler.initMemberRegister,
    'save checkedin' : XlsxHandler.saveAllCheckedinToLog,
    'save members' : XlsxHandler.saveMemberlistToFile,
    'save statistics' : XlsxHandler.saveStatistics,
    'import' : XlsxHandler.importNewMembers,
    'clean' : XlsxHandler.cleanEarliestLoggbook
}

# Initierar excelfiler
XlsxHandler.initBoardMemberRegister()
XlsxHandler.initMemberRegister()

# Initialize Tkinter root and maximize the window
root = tk.Tk()
maximize_window(root)

while True:
    flag = True
    while not GUI.hasLines():
        timedFunctions()
        date_time_now = datetime.now()
        if (flag and (GUI.latest_message_time < date_time_now)):
            GUI.hideMessage()
            flag = False

    card_number = GUI.readInput()

    if card_number in commands:
        commands[card_number]()
    else:
        card_number = '0,' + card_number
        time_now_str = date_time_now.strftime("%H:%M:%S")
        date_now_str = date_time_now.strftime("%Y-%m-%d")
        member = Member.checkOut(card_number)
        if member != None:
            GUI.message('Goodbye %s' %member.getName(), 2)
            if member.getBoardmember():
                GUI.updateNames(Member.checked_in_styret, 'styret')
            else:
                GUI.updateNames(Member.checked_in_members, 'member')
            StatLogger.checkOutStat(member)
            XlsxHandler.saveToLog(member)
            XlsxHandler.save()
        elif card_number in Member.member_register:
            member_local = Member.member_register[card_number]
            Member.checkIn(member_local)
            GUI.message('Welcome %s' %member_local.getName(), 2)
            if (member_local.getBoardmember()):
                StatLogger.tickCheckInsStyret()
                GUI.updateNames(Member.checked_in_styret, 'styret')
            else:
                StatLogger.tickCheckInsMember()
                GUI.updateNames(Member.checked_in_members, 'member')
        else:
            old_card_number = card_number
            date_time_to_wait = datetime.now() + timedelta(0,time_to_wait)
            while (not GUI.hasLines()) and (date_time_to_wait > datetime.now()):
                message_string = ("Card not recognised!\nPlease scan again to start a transfer\n"
                                  "process, or wait %s seconds to cancel"
                                  %secondCounter(date_time_to_wait))
                GUI.message(message_string)
            if (GUI.hasLines()):
                new_card_number = '0,' + GUI.readInput()
                if new_card_number == old_card_number:
                    date_time_to_wait = datetime.now() + timedelta(0,time_to_wait)


