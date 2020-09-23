import random
import socket
import time
import re
import threading
import datetime
import env
import traceback as tb
    
user = env.USER
channel = env.CHANNEL

version = "a0.2.0"

def runIn(seconds, function, *args):
    def _f(seconds, function, *args):
        time.sleep(seconds);function.__call__(*args)
    threading.Thread(target=_f, daemon=True, args=(seconds, function, *args)).start()

class AmongTwitchGame:
    def __init__(self):
        self.playerList = PlayerList()
        self.gameRules = GameRules(self)
        self._lastMeeting = datetime.datetime.min
        self.gameStarted = False
        self.isMeeting = False
        self.skipVotes = 0

    def startGame(self):
        """Attemts to start the game, and returns if it was able to or not"""
        if self.gameRules.getImposterCount(self.playerList.totalPlayerCount()) > 0:
            for p in self.playerList.players:
                p.resetWithRules(self.gameRules)
            self.randomizeImposters()
            if self.gameRules.debugMode:
                chat("game started with imposters: " + str([x.username for x in self.playerList.players if x.imposter]))
            self.gameStarted = True
            return True
        else:
            return False

    def randomizeImposters(self):
        """Chooses new imposters. Can theoretically be called mid-game, but could cause issues, notably with clues"""
        for i in range(self.gameRules.getImposterCount(self.playerList.totalPlayerCount())):
            index = random.choice([x for x in range(self.playerList.totalPlayerCount())])
            if self.playerList.players[index].imposter:
                i -= 1
                print("duplicate imposter")
            else:
                self.playerList.players[index].imposter = True
            

    def meetingCooldownPast(self):
        """Returns true if enough time has passed for a meeting to be called"""
        return (self._lastMeeting + self.gameRules.meetingCooldown) < datetime.datetime.now()

    def canCallMeeting(self, player=None):
        """returns true if the provided player can call a meeting"""
        return (player == None or (player.meetingsLeft > 0 and player.alive)) and self.meetingCooldownPast()

    def callMeeting(self, player):
        """Attempts to have player call a meeting"""
        if self.canCallMeeting(player):
            self._callMeeting(player)
            return True
        return False

    def _callMeeting(self, player):
        self.skipVotes = 0
        player.meetingsLeft -= 1
        self._lastMeeting = datetime.datetime.now()
        self.isMeeting = True
        runIn(self.gameRules._meetingDuration, self._endMeeting)

    def vote(self, player, name):
        """Makes a player vote for another player"""
        if name.lower() in [x.username for x in self.playerList.players]:
            [x for x in self.playerList.players if x.username == name.lower()][0].addVote()
            player.voted = True
            return True
        else:
            return False

    def _endMeeting(self):
        result = self.checkIfMeetingShouldEnd()
        if result[0]:
            self._lastMeeting = datetime.datetime.now()

            voted = game.playerList.getPlayerWithMostVotes()
            if voted[1] == "TIE":
                if self.skipVotes > voted[0]:
                    chat("No one was ejected. (Skipped)")
                else:
                    chat("No one was ejected. (Tie)")
            elif voted[1] == "NOVOTES":
                if self.skipVotes > voted[0]:
                    chat("No one was ejected. (Skipped)")
                else:
                    chat("No one was ejected. (No Votes)")
            else:
                if self.skipVotes > voted[0].votesFor:
                    chat("No one was ejected. (Skipped)")
                else:
                    if self.gameRules.confirmEjects:
                        if voted[0].imposter:
                            if self.gameRules.getImposterCount(self.playerList.totalPlayerCount) == 1:
                                chat(voted[0].username + " was The Imposter.")
                            else:
                                chat(voted[0].username + " was An Imposter.")
                        else:
                            if self.gameRules.getImposterCount(self.playerList.totalPlayerCount) == 1:
                                chat(voted[0].username + " was not The Imposter.")
                            else:
                                chat(voted[0].username + " was not An Imposter.")
                    else:
                        chat(voted[0].username + " was ejected.")

            if (self.gameRules.confirmEjects):
                chat("(" + self.playerList.aliveImposterCount() + " Imposters remain.)")
            

            for p in [x for x in self.playerList.players if x.alive]:
                p.resetVotes()

            win = self.checkWinCondition()
            if (win["crewmates"]):
                game.gameStarted = False
                chat("")

        return result

    def checkIfMeetingShouldEnd(self):
        """Checks if the meeting should end. Returns a tuple of (bool: should the meeting end, str: why)"""
        if (self.isMeeting):
            if (self._lastMeeting + self.gameRules.meetingDuration) < datetime.datetime.now():
                return (True, "TIME")
            elif len([x for x in self.playerList.players if x.voted]) == len(self.playerList.players):
                return (True, "VOTED")
            else:
                return (False, "NORMAL")
        else:
            return (False, "NOTMEETING")
        

    def checkWinCondition(self):
        """Checks if any win conditions are met. Returns an object of {"crewmates": bool, "imposters": bool, "winners": Player[]}. Crewmates win when all imposters are dead. Imposters win when the number of alive crewmates is equal to the number of alive imposters"""
        if self.playerList.aliveImposterCount() >= self.playerList.aliveCrewmateCount():
            self.gameStarted = False
            return {"crewmates": False, "imposters": True, "winners": [x for x in self.playerList.players if x.imposter]}
        elif self.playerList.aliveImposterCount() <= 0:
            self.gameStarted = False
            return {"crewmates": True, "imposters": False, "winners": [x for x in self.playerList.players if not x.imposter]}
        else:
            return {"crewmates": False, "imposters": False, "winners": []}

class Player:
    def __init__(self, username):
        self.username = username
        self.meetingsLeft = 0
        self.alive = True
        self.imposter = False
        self.votesFor = 0
        self.cluesGiven = []
        self.voted = False

    def resetWithRules(self, rules):
        """Resets player data from a rule set"""
        self.resetWithoutRules()
        self.meetingsLeft = rules.meetingsPerPlayer

    def resetWithoutRules(self):
        """Resets player data without a rule set"""
        self.resetVotes()
        self.meetingsLeft = 1
        self.alive = True
        self.imposter = False
        self.cluesGiven = []

    def getClueString(self):
        """Returns the clue string for this player's clues"""
        ret = ""
        for clue in self.cluesGiven:
            ret += clue.name + ": "
            if clue.imposter:
                ret += "Imposter"
            else:
                ret += "Crewmate"
            ret += ", "
        return ret[0:-2]

    def kill(self):
        """Kills the player"""
        self.alive = False
        self.meetingsLeft = 0
        self.resetVotes()

    def addVote(self):
        """Adds a vote to this player"""
        self.votesFor += 1

    def resetVotes(self):
        """Resets voting info for this player"""
        self.votesFor = 0
        self.voted = False

class GameRules:
    def __init__(self, game):
        self.maxPlayers = 10
        self.imposterCount = 2
        self.debugMode = True
        self.meetingsPerPlayer = 1
        self.meetingCooldown = datetime.timedelta(seconds=20)
        self._meetingCooldown = 20
        self.meetingDuration = datetime.timedelta(seconds=120)
        self._meetingDuration = 120
        self.confirmEjects = True
        self.game = game

    def getImposterCount(self, playerCount):
        """Returns the number of imposters that should be in a game based on the player count"""
        if playerCount < 4:
            return min(0, self.imposterCount)
        elif playerCount < 7:
            return min(1, self.imposterCount)
        elif playerCount < 9:
            return min(2, self.imposterCount)
        elif playerCount < 12:
            return min(3, self.imposterCount)
        elif playerCount < 16:
            return min(4, self.imposterCount)
        elif playerCount < 20:
            return min(5, self.imposterCount)
        else:
            return min(6, self.imposterCount)

    def reset(self):
        """Resets game rules"""
        self = GameRules(self.game)

    def __str__(self):
        return "maxPlayers: " + str(self.maxPlayers) + ", confirmEjects: " + str(self.confirmEjects) + ", imposterCount: " + str(self.imposterCount) + " (limit: " + str(self.getImposterCount(game.playerList.totalPlayerCount())) + "), debugMode: " + str(self.debugMode) + ", meetingsPerPlayer: " + str(self.meetingsPerPlayer) + ", meetingCooldown: " + str(self._meetingCooldown) + ", meetingDuration: " + str(self._meetingDuration)

    def setMeetingCooldown(self, seconds):
        """Sets a new meeting cooldown"""
        self.meetingCooldown = datetime.timedelta(seconds=seconds)
        self._meetingCooldown = seconds

    def setMeetingDuration(self, seconds):
        """Sets a new meeting duration"""
        self.meetingDuration = datetime.timedelta(seconds=seconds)
        self._meetingDuration = seconds

class PlayerList:
    def __init__(self):
        self.players = []

    def getPlayerWithMostVotes(self):
        self.players.sort(key=lambda x: x.votesFor)
        if (self.players[0].votesFor == 0):
            return (0, "NOVOTES")
        elif (self.players[0].votesFor == self.players[1].votesFor):
            return (self.players[0].votesFor, "TIE")
        else:
            return (self.players[0], "MOST")

    def playerIsInGame(self, name):
        """Returns true if a user with the given name is in the player list"""
        return len([x for x in self.players if x.username == name]) > 0

    def getPlayerByUsername(self, name):
        """Returns the Player object of the player from the player list, None if they are not in the game"""
        if self.playerIsInGame(name):
            return [x for x in self.players if x.username == name][0]
        else:
            return None

    def addPlayer(self, player):
        """Adds a player to the player list"""
        self.players.append(player)

    def addUser(self, user):
        """Creates a player object from a username, and adds it to the list. Returns true if the player was succesfully added, false otherwise"""
        if (user in [x.username for x in self.players]):
            return False
        self.addPlayer(Player(user))
        return True
    
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
        
        
game = AmongTwitchGame()

def handleCommand(username, msg):
    """Attempts to handle a chat command"""
    #arguments = msg.split(" ")
    message = msg.lower()
    args = message.split(" ")

    if (message.startswith("!join")):
        if game.playerList.addUser(username):
            chat("You have joined the game")
        
        else:
            chat("Unable to join game. Are you already in it?")
    
    elif (message.startswith("!info")):
        chat("Among Twitch - " + version + " - How to play: https://github.com/LeotomasMC/Among-Twitch")
    
    elif (message.startswith("!list")):
        if (game.gameStarted):
            l = "Players In Game: "
            for p in game.playerList.players:
                l += p.username
                if not p.alive:
                    l += "!"
                elif game.isMeeting and p.voted:
                    l += "*"
                l += ", "
            l = l[0:-2]
            l += "[! = dead"
            if game.isMeeting:
                l += ", * = voted"
            l += "]"
            chat(l)
        else:
            if (game.playerList.totalPlayerCount() > 0):
                chat(", ".join([x.username for x in game.playerList.players]))
            else:
                chat("There is nobody in the game currently!")
            
    elif (message.startswith("!start")):
        #chat("starting game...")
        if (game.startGame()):
            pass
        else:
            chat("Unable to start game.")

    elif (message.startswith("!rules")):
        chat("Current Game Rules: " + str(game.gameRules))

    elif (message.startswith("!leave")):
        if username in [x.username for x in game.playerList.players]:
            if game.gameStarted:
                [x for x in game.playerList.players if x.username == username][0].kill()
        else:
            chat("You are not currently in the game")

    elif (message.startswith("!changerules")):
        if len(args) >= 3:
            if args[1] == "impostercount":
                try:
                    game.gameRules.imposterCount = int(args[2])
                except TypeError:
                    chat("That is not a number")
            
            elif args[1] == "maxplayers":
                try:
                    game.gameRules.maxPlayers = int(args[2])
                except TypeError:
                    chat("That is not a number")
            
            elif args[1] == "meetingsperplayer":
                try:
                    game.gameRules.meetingsPerPlayer = int(args[2])
                except TypeError:
                    chat("That is not a number")
            
            elif args[1] == "meetingcooldown":
                try:
                    game.gameRules.setMeetingCooldown(int(args[2]))
                except TypeError:
                    chat("That is not a number")
            
            elif args[1] == "meetingduration":
                try:
                    game.gameRules.setMeetingDuration(int(args[2]))
                except TypeError:
                    chat("That is not a number")
            
            elif args[1] == "debug":
                if args[2] in ["yes", "y", "true", "t", "1"]:
                    game.gameRules.debugMode = True
                elif args[2] in ["no", "n", "false", "f", "0"]:
                    game.gameRules.debugMode = False
                else:
                    chat("that is not a valid argument " + str(["yes", "y", "true", "t", "1"] + ["no", "n", "false", "f", "0"]))
        
        else:
            chat("you did not provide enough arguments! [" + str(len(args)) + "]")

    elif (message.startswith("!vote")):
        if (game.playerList.playerIsInGame(username)):
            print(len(args))
            if len(args) >= 2:
                if (args[1] == "skip" or args[1] == "s"):
                    game.skipVotes += 1
                    game.playerList.getPlayerByUsername(username).voted = True
                else:
                    print(args[1])
                    if game.playerList.playerIsInGame(args[1]):
                        game.vote(game.playerList.getPlayerByUsername(username), args[1])
                    else:
                        chat("There is no user in the game by that name.")
            else:
                chat("Who do you want to vote for?")
        else:
            pass

    elif (message.startswith("!meeting")):
        if (game.isMeeting):
            left = (game._lastMeeting + game.gameRules.meetingDuration) - datetime.datetime.now()
            chat("Time left in meeting: " + str(left))
            print(game.checkIfMeetingShouldEnd())
        else:
            if (game.playerList.playerIsInGame(username)):
                if game.callMeeting(game.playerList.getPlayerByUsername(username)):
                    chat("calling meeting")
                else:
                    chat("You cannot call a meeting right now")
            else:
                chat("You cannot call a meeting as you are not in the game!")
            


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
    print(channel + "> " + user.lower() + ": " + msg)

while True:
    response = s.recv(1027).decode("utf-8")
    if response == "PING :tmi.twitch.tv\r\n":
        s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
    else:
        username = re.search(r"\w+", response).group(0)
        message = CHAT_MSG.sub("", response)
        msg = message.lower()
        print(channel + "> " + username + ": " + message.strip())
        
        if (username == channel.lower() and msg.startswith("!sudo ")):
            parts = message.split(" ", 2)
            handleCommand(parts[1], parts[2]) 
        elif (username == "leotomas" and msg.startswith("!exec ")):
            try:
                exec(message[6::])
            except Exception as e:
                tb.print_exc()
        elif (username == "leotomas" and msg.startswith("!kb")):
            chat("Killing bot...")
            exit()
        elif (username == "leotomas" and msg.startswith("!debugstart")):
            handleCommand("a", "!join")
            handleCommand("b", "!join")
            handleCommand("c", "!join")
            handleCommand("d", "!join")
            handleCommand("leotomas", "!start")
        else:
            handleCommand(username, message)