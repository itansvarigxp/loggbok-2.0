from helpers.utils import normalize_card



from member import *
import excel_handler as XlsxHandler
import db
import statistics_handler as StatLogger
import gui_module as GUI
from datetime import datetime, timedelta
import sys
import os
#import pyautogui	*********** Flyttas 

db.init_db()

message_update_time_short = 2
message_update_time_long = 5
time_to_wait = 5
latest_message_time = datetime.now()

# Frågar efter CID för mount av Z-disk
#cid = pyautogui.prompt(text='Enter CID for mounting Z-drive', title='' , default='') **************

# Frågar efter lösen för mount av Z-disk
#pw = pyautogui.password(text='Enter password for mounting Z-drive', title='', default='', mask='*') ***************

# Fras för att montera Z-disken
#mnt = '+sudo mount.cifs //sol.ita.chalmers.se/expe /mnt -o user={GUI.cid}, password={GUI.pw},vers=3.0+'


def setStateVariables(time_str):
    global latest_message_time
    latest_message_time = datetime.strf(time_str)

def exitProgram():
    sys.exit()

def secondCounter(datetime_wait_until):
    return str(int((datetime_wait_until - datetime.now()).seconds) + 1)

# Funktion för att flytta bilder som används till hemsidan
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
    #Funktioner som körs inom bestämda tidsintervall varje dygn.
    #print('in timed function')
    time_now = datetime.now() 
    time_now_str = time_now.strftime("%H:%M:%S")
    #print(time_now)
    #print((XlsxHandler.latest_save + timedelta(hours = 0, minutes = 1))
    # Debugga denna
    if  time_now_str >= ('04:00:00') and \
        time_now_str <= ('05:00:10') and \
        (XlsxHandler.latest_save + timedelta(hours = 2) < time_now): 
        #Mellan 4 och 5 på morgonen rensas loggboken, de som fortfarande är
        #incheckade blir sparade. Nya medlemmar importeras till medlemsregistret
        message_string = "Updating registers, please hold..."
        GUI.message(message_string)
        # Dagens statistik loggas. Måste göras innan de som glömt att checka ut
        # rensas ur loggboken
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

def processInput():
        card_number = GUI.readInput()
        if card_number in commands:
            commands[card_number]()
        else:
            row = db.get_member(card_number)
            if row is None:
                row = db.get_member(normalize_card(card_number))

            if row is None:
                GUI.message(f"Unknown card: {card_number}", 2)
            else:
                # Returns the stored Member if they were checked in, else None
                member = Member.checkOut(row["card_number"])
    
                if member is not None:
                    # Was checked in -> check out
                    GUI.message('Goodbye %s' % member.getName(), 2)
    
                    if member.getBoardmember():
                        GUI.updateNames(Member.checked_in_styret, 'styret')
                    else:
                        GUI.updateNames(Member.checked_in_members, 'member')
    
                    StatLogger.checkOutStat(member)
                    XlsxHandler.saveToLog(member)
                    XlsxHandler.save()
                else:
                    # Wasn't checked in -> check in
                    member = Member.from_row(row)
                    Member.checkIn(member)
    
                    GUI.message('Welcome %s' % member.getName(), 2)
    
                    if member.getBoardmember():
                        StatLogger.tickCheckInsStyret()
                        GUI.updateNames(Member.checked_in_styret, 'styret')
                    else:
                        StatLogger.tickCheckInsMember()
                        GUI.updateNames(Member.checked_in_members, 'member')
        
# Kommandon som kan skrivas i programmet för att kalla på motsvarande funktion
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

while True:
    # Gör om klassvariablerna i Members till en lista av strings med namm
    # samt uppdaterar GUI-modulen som hanterar de olika listorna.
    

    
    # Flagga för att förhindra för många functioncalls i whileloopen nedan.
    flag = True
    # Flytta bilder för hemsidan
#    mvIncheckadePNG()
    # Denna körs så länge inget nytt input har tillkommit
    while not GUI.hasLines():
        timedFunctions()
        date_time_now = datetime.now()
        if (flag and (GUI.latest_message_time < date_time_now)):
            GUI.hideMessage()
            #GUI.message("Please swipe your card")
            flag = False

    # Nytt input har tillkommit
    processInput()



