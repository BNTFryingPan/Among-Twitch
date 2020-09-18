import random
import socket
import time
import re
import threading
import datetime
import env

changeColor = True
newColor = 000000
    
user = env.USER
channel = env.CHANNEL

class AmongTwitchGame:
    def __init__(self):
        self.playerList = PlayerList()
        self.gameRules = None
        self._lastMeeting = 0

    def startGame(self):
        pass

    def randomizeImposters(self):
        pass

    def canCallMeeting(self, player=None):
        if (player.meetingsLeft > 0) and ():
            pass

    def callMeeting(self):
        if datetime.time():
            pass

    def _callMeeting(self, player):
        pass

    def checkWinCondition(self):
        if self.playerList.aliveImposterCount() >= self.playerList.aliveCrewmateCount():
            return {"crewmates": False, "imposters": True, "winners": [x for x in self.playerList.players if x.imposter]}
        elif self.playerList.aliveImposterCount() <= 0:
            return {"crewmates": True, "imposters": False, "winners": [x for x in self.playerList.players if not x.imposter]}
        else:
            return {"crewmates": False, "imposters": False, "winners": []}

class Player:
    def __init__(self, username):
        self.username = username
        self.meetingsLeft = 0
        self.alive = True
        self.imposter = False

    def resetWithRules(self, rules):
        self.meetingsLeft = rules.meetingsPerPlayer
        self.alive = True
        self.imposter = False

    def resetWithoutRules(self):
        self.meetingsLeft = 1
        self.alive = True
        self.imposter = False

class GameRules:
    def __init__(self):
        self.maxPlayers = 10
        self.imposterCount = 2
        self.debugMode = True
        self.meetingsPerPlayer = 1
        self.meetingCooldown = datetime.timedelta(seconds=15)

    def reset(self):
        self = GameRules()

    def setMeetingCooldown(self, seconds):
        self.meetingCooldown = datetime.timedelta(seconds=seconds)

class PlayerList:
    def __init__(self):
        self.players = []

    def addPlayer(self, player):
        self.players.append(player)
    
    def alivePlayerCount(self):
        return len([x for x in self.players if x.alive])

    def deadPlayerCount(self):
        return len([x for x in self.players if not x.alive])
    
    def totalPlayerCount(self):
        return len(self.players)

    def aliveImposterCount(self):
        return len([x for x in self.players if (x.alive and x.imposter)])

    def deadImposterCount(self):
        return len([x for x in self.players if ((not x.alive) and x.imposter)])

    def totalImposterCount(self):
        return len([x for x in self.players if (x.imposter)])

    def aliveCrewmateCount(self):
        return len([x for x in self.players if (x.alive and (not x.imposter))])

    def deadCrewmateCount(self):
        return len([x for x in self.players if ((not x.alive) and (not x.imposter))])

    def totalCrewmateCount(self):
        return len([x for x in self.players if (not x.imposter)])
        
        
def handleCommand(username, message):
    pass

oauth = env.OAUTH
# get your oauth token here: https://twitchapps.com/tmi/

s = socket.socket()

CHAT_MSG = re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :")

s.connect(("irc.chat.twitch.tv", 6667))
s.send(bytes("PASS " + oauth + "\r\n", "UTF-8")) # joins twitch chat
s.send(bytes("NICK " + user.lower() + "\r\n", "UTF-8"))
s.send(bytes("JOIN #" + channel.lower() + "\r\n", "UTF-8"))

def chat(msg):
    blab = "PRIVMSG #" + channel.lower() + " :"  + msg + "\r\n"
    s.send(bytes(str(blab), 'utf-8'))

while True:
    response = s.recv(1027).decode("utf-8")
    if response == "PING :tmi.twitch.tv\r\n":
        s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
    else:
        username = re.search(r"\w+", response).group(0)
        message = CHAT_MSG.sub("", response)
        msg = message.lower()
        handleCommand(username, message)
        print(channel + "> " + username + ": " + message)