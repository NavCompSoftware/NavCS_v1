from flask import *
from datetime import datetime,timedelta
import database_manager as db_man
import modes
import os

#Set up Flask app
app = Flask(__name__, static_url_path='/static')

#Start page
@app.route("/")

def index():
  db = db_man.init_SQL()
  db_man.confirm_tables(db)
  print("loading home page")
  if db_man.scan_needed():
    print("scan due")
    try:
      db_man.maintain_db(db)
    except:
      print("scan failed")
  db_man.save(db)
  #else:
  #  print("no need to scan")
  return(render_template("home.html"))

#Page for players to join a game
@app.route("/join")

def join():
  print("loading join page")
  return(render_template("join.html", message="Please enter your details to join a game:"))

@app.route("/connect2",methods=["POST"])

def connect2():
  print("RUNNING CONNECT2")
  name,code = str(request.data).strip("b").strip("'").split(",")
  id = db_man.generate_code();
  
  success = False
  error = "[unknown error]"
  
  print("name:",name)
  print("code:",code)
  print("id:",id)
  
  db = db_man.init_SQL()
  game_state = db_man.game_running(db,code)
  if game_state:
    started,ended = game_state
    if started:
      print("game already started")
      error = "[game started]"
    else:
      print("game is good to go")
      success = True
  else:
    error = "[invalid code]"
  db_man.end_query(db)
  
  if not success:
    print("error, sending details")
    return(error)
  else:
    print("success, registering player")
    player = db_man.player(id,name,code)
    db = db_man.init_SQL()
    player.register(db)
    db_man.save(db)
    print("registered player")
    return(id)

#Submission of join form
@app.route("/connect", methods=["POST","GET"])

def connect():
  success = False
  error = ""
  print(request.json)
  try:
    #Collect all the form info
    keys = []
    info = {}
    for inpt in request.form:
      keys.append(inpt)
    for key in keys:
      info[key] = request.form[key]
  
    #Collect additional info
    ip = request.environ['REMOTE_ADDR']
    info["ip"] = ip
    code = info["game_code"]
    
    db = db_man.init_SQL()
    game_state = db_man.game_running(db,code)
    if db_man.ip_already_in(db,ip):
      print("user already in")
      error = f"user already registered at ip [{ip}]"
    else:
      print("true new user")
      if game_state:
        started,ended = game_state
        if started:
          print("game already started")
          error = "game has already started."
        else:
          print("game is good to go")
          success = True
      else:
        error = "Invalid code."
    db_man.end_query(db)
  except:
    error="An unknown error occured."
  if not success:
    print("error - reloading")
    return(render_template("join.html",message=error))
  else:
    print("ip:",ip)
    name = info["f_name"] + " " + info["l_name"]
    print("name:",name)
    print("code:",code)
    player = db_man.player(ip,name,code)
    db = db_man.init_SQL()
    player.register(db)
    db_man.save(db)
    print("registered player")
    return(render_template("run.html"))

@app.route("/create")

def create():
  return(render_template("create.html"))

@app.route("/submit_application", methods=["POST","GET"])

def submit_application():
  #try:
  data = request.data
  time,date,timeadj,hours,minutes,mode = str(data).strip("b").strip("'").split(",")
  H,M = [int(x) for x in time.split(":")]
  y,m,d = [int(x) for x in date.split("-")]
  start = db_man.time_object(0,M,H,d,m,y) + timedelta(minutes = int(timeadj))
  start_str = datetime.strftime(start,"%d/%m/%Y %H:%M:%S")
  duration = int(hours) + int(minutes)/60
  code = db_man.generate_code()
  if db_man.is_before(datetime.now(),start):
    db = db_man.init_SQL()
    db_man.confirm_tables(db)
    game = db_man.game(start_str,duration,code,mode)
    game.register(db)
    db_man.save(db)
    return(code)
  else:
    print("date/time error")
    return("!")
  #except:
  #  print("unknown error")
  #  return("error")

@app.route("/admin_test",methods=["POST","GET"])

def admin_test():
  db = db_man.init_SQL()
  print(db_man.get_codes(db))
  db_man.all_players(db)
  db_man.end_query(db)
  return(render_template("home.html"))

@app.route("/run")

def run():
  return(render_template("run.html"))

@app.route("/update_state", methods=["POST","GET"])

def update_state():
  print("RUNNING update_state")
  lat,long,id = str(request.data).strip("b").strip("'").split(",")
  lat,long = float(lat),float(long)
  db = db_man.init_SQL()
  game = db_man.get_code(db,id)
  print("user id:", id)
  print("in game:", game)
  print("at lat:", lat)
  print("at long:", long)
  loc_string = str(lat)+","+str(long)
  game_state = db_man.game_running(db,game)
  if game_state:
    if game_state[0] and not game_state[1]:
      print("game running")
      db_man.update_location(db,id,loc_string)
      db_man.save(db)
      db = db_man.init_SQL()
      if db_man.get_mode(db,game) == "HS_2":
        print("running hide and seek game")
        program = modes.HideAndSeek(id)
        print(program.players)
        if program.assigned():
          print("targets already assigned")
        else:
          print("targets not yet assigned, fixing")
          program.assign_targets()
        db_man.get_target_locations(db,id)
        db_man.save(db)
        
      else:
        print("unknown game mode")
        print(db_man.get_mode(db,game))
      return(loc_string)
    else:
      print("game not running rn")
      db_man.end_query(db)
      return("!")
  else:
    db_man.end_query(db)
    return("!")

if __name__ == '__main__':
  port = int(os.environ.get("PORT", 5000))
  app.run(debug = True, port=port)
