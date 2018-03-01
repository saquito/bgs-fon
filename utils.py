import requests
import json
import sqlite3
import os.path
import time
import datetime
import sys
import os
import shutil
import pprint
from collections import defaultdict
import itertools

EXPANSION_RADIUS = 27.5
EXPANSION_THRESHOLD = 0.65
RETREAT_THRESHOLD = 0.05
WAR_THRESHOLD = 0.05
TICK_TIME = "15:30:00"
TIME_FORMAT = '%d-%m-%Y %H:%M:%S'
DEBUG_LEVEL = 0
LOCAL_JSON_PATH = "LOCAL_JSON"
DATABASE = "bgs-data.sqlite3"

db_connection = None

def set_database_connection(db_name):
  DATABASE = db_name

def get_database_connection():
  global db_connection
  if db_connection == None:
    db_connection = sqlite3.connect(DATABASE)
  return db_connection

def close_database_connection():
  global db_connection
  db_connection.close()
  db_connection = None

def debug(message,level = 0):
  if level <= DEBUG_LEVEL:
    print(message)

def clean_local_json_path():
  if os.path.exists(LOCAL_JSON_PATH):
    shutil.rmtree(LOCAL_JSON_PATH)

def get_local_json_path(filename):
  if not os.path.exists(LOCAL_JSON_PATH):
    os.mkdir(LOCAL_JSON_PATH)
  return "/".join((LOCAL_JSON_PATH,filename))

def get_json_data(filename,request, request_data, local = False):
  data = None
  json_file_path = get_local_json_path(filename)
  if local and os.path.isfile(json_file_path):
      json_file = open(json_file_path,"r")
      data = json.load(json_file)
  else:
    r = requests.post(request, request_data)
    data = json.loads(r.text)
    if r.text == "[]":
      print(r.headers)
      exit(-1)
    json_file = open(json_file_path,"w")
    json_file.write(json.dumps(data))
    json_file.close()
  return data

def fetch_system(conn,systemName):
  c = conn.cursor()
  c.execute("SELECT * FROM Systems WHERE system_name=:name",{'name':systemName})
  data = c.fetchone()
  return data

def fetch_faction(conn,factionName):
  c = conn.cursor()
  c.execute("SELECT * FROM Factions WHERE faction_name=:name",{'name':factionName})
  data = c.fetchone()
  return data

def fill_factions_from_system(conn,systemName, local = False):
  c = conn.cursor()
  data_factions = get_json_data("factions_{0}.json".format(systemName),
                       "https://www.edsm.net/api-system-v1/factions",
                       {'systemName': systemName, 'showHistory':1}, 
                       local)
  if not data_factions['factions']:
    return None
  for faction in data_factions['factions']:
    if not fetch_faction(faction['name']):
      values = [faction['name'],faction['allegiance'],faction['government'],faction['isPlayer'], None]
      c.execute("INSERT INTO Factions VALUES (?,?,?,?,?)",values)
  conn.commit()    

def fill_systems_in_bubble(systemName, radius = EXPANSION_RADIUS, local = False):
  conn = get_database_connection()
  c = conn.cursor()
  debug("RADIUS:",radius)
  data_bubble = get_json_data("sphere_{0}.json".format(systemName),
                       "https://www.edsm.net/api-v1/sphere-systems",
                       {'systemName': systemName,'radius':radius}, 
                       local)
  for system in data_bubble:
    distance = system['distance']
    data_system = get_json_data("system_{0}.json".format(system['name']),
                   "https://www.edsm.net/api-v1/system",
                   {'systemName': system['name'],'showPrimaryStar':1,'showInformation':1}, 
                   local)
    population = 0
    economy = 'None'
    if data_system['information']:
      population = data_system['information']['population']
      economy = data_system['information']['economy']
      allegiance = data_system['information']['allegiance']
      faction = data_system['information']['faction']
      factionState = data_system['information']['factionState']
    values = [data_system['name'],
              population,
              economy,distance,allegiance,faction,factionState]

    c.execute("INSERT INTO Systems VALUES (?,?,?,?,?,?,?)",values)
    data_stations = get_json_data("stations_{0}.json".format(system['name']),
                   "https://www.edsm.net/api-system-v1/stations",
                   {'systemName': system['name']}, 
                   local)
    for station in data_stations['stations']:
      controlling_faction = None
      if 'controllingFaction' in station:
        controlling_faction = station['controllingFaction']['name']
      values = [systemName,station['name'],station['type'],station['distanceToArrival'],station['economy'],controlling_faction]
      c.execute("INSERT INTO Stations VALUES (?,?,?,?,?,?)",values)
    debug("Updating system: {0}".format(system['name']))
    fill_factions_from_system(data_system['name'], local)
  conn.commit()

def fetch_systems(criteria = None):
  conn = get_database_connection()
  c = conn.cursor(conn)
  if criteria:
    c.execute("SELECT * FROM Systems WHERE {0}".format(criteria))
  else:
    c.execute("SELECT * FROM Systems")  
  return c.fetchall()

def clean_updates():
  conn = get_database_connection()
  c = conn.cursor()
  c.execute("DELETE FROM ticks")
  c.execute("DELETE FROM faction_system")
  c.execute("DELETE FROM system_status")
  c.execute("DELETE FROM faction_system_state")
  conn.commit()

def clean_fixed_tables():
  conn = get_database_connection()
  c = conn.cursor(conn)
  c.execute("DELETE FROM Factions")
  c.execute("DELETE FROM Systems")
  c.execute("DELETE FROM Stations")
  conn.commit()

def get_time(cur_time = None):
  current_time = time.time()
  if cur_time != None:
    if isinstance(cur_time,str):
      current_time = get_epoch_from_utc_time(cur_time)
    elif isinstance(cur_time,float) or isinstance(cur_time,int):
      current_time = cur_time
    else:
      print("DATE FORMAT ERROR")
      exit(-1)
  return current_time

def get_last_tick_time(cur_time = None):
  current_time = get_time(cur_time)
  
  todays_tick_time = get_todays_tick_time(current_time)
  if current_time >= todays_tick_time:
    return todays_tick_time
  else:
    todays_tick_datetime = datetime.datetime.fromtimestamp(todays_tick_time)
    tomorrows_tick_datetime = todays_tick_datetime - datetime.timedelta(days=1)
    return tomorrows_tick_datetime.timestamp()
    
def get_next_tick_time(cur_time = None):
  current_time = get_time(cur_time)
  
  todays_tick_time = get_todays_tick_time(current_time)
  if current_time < todays_tick_time:
    return todays_tick_time
  else:
    todays_tick_datetime = datetime.datetime.fromtimestamp(todays_tick_time)
    tomorrows_tick_datetime = todays_tick_datetime + datetime.timedelta(days=1)
    return tomorrows_tick_datetime.timestamp()

def get_current_tick_time(cur_time = None):
  current_time = get_time(cur_time)
  
  todays_tick_time = get_todays_tick_time(current_time)
  last_tick_time = get_last_tick_time(current_time)
  if current_time <= todays_tick_time:
    return last_tick_time
  else:
    return todays_tick_time    
  
def get_todays_tick_time(cur_time = None):
  current_time = get_time(cur_time)
  
  day_time = time.strftime("%d-%m-%Y",time.gmtime(current_time))
  if cur_time:
    day_time = time.strftime("%d-%m-%Y",time.gmtime(cur_time))
  todays_tick_time = " ".join((day_time,TICK_TIME))
  return get_epoch_from_utc_time(todays_tick_time)

def is_update_needed(conn, cur_time = None):
  current_time = time.time()
  if cur_time:
    if isinstance(cur_time,str):
      current_time = get_epoch_from_utc_time(cur_time)
    elif isinstance(cur_time,float) or isinstance(cur_time,int):
      current_time = cur_time
    else:
      print("DATE FORMAT ERROR")
      return False
  last_update_time = get_last_update()
  todays_tick_time = get_todays_tick_time(current_time)
  current_tick_time = get_current_tick_time(current_time)
  next_tick_time = get_next_tick_time(current_time)
  debug("CURRENT_TIME:\t\t{0} [{1}]".format(int(current_time),get_utc_time_from_epoch(current_time)))
  debug("LAST_UPDATE_TIME:\t{0} [{1}]".format(int(last_update_time),get_utc_time_from_epoch(last_update_time)))
  debug("TODAYS_TICK_TIME:\t{0} [{1}]".format(int(todays_tick_time),get_utc_time_from_epoch(todays_tick_time)))
  debug("CURRENT_TICK_TIME:\t{0} [{1}]".format(int(current_tick_time),get_utc_time_from_epoch(current_tick_time)))
  debug("NEXT_TICK_TIME:\t\t{0} [{1}]".format(int(next_tick_time),get_utc_time_from_epoch(next_tick_time)))

  if last_update_time == 0:
    return True
  if current_time > last_update_time and last_update_time < todays_tick_time: 
    if current_time < todays_tick_time:
      return False
    else:
      return True
  else:
    return False

def get_utc_time_from_epoch(epoch):
  if isinstance(epoch,str):
    epoch = int(epoch)
  return time.strftime(TIME_FORMAT,time.gmtime(epoch))

def get_epoch_from_utc_time(utc_time):
  return time.mktime(time.strptime(utc_time, TIME_FORMAT))

def get_timestamp(cur_time = None):
  current_time = time.time()
  if cur_time:
    if isinstance(cur_time,str):
      current_time = get_epoch_from_utc_time(cur_time)
    elif isinstance(cur_time,float) or isinstance(cur_time,int):
      current_time = cur_time
    else:
      print("DATE FORMAT ERROR")
      exit(-1)
  return int(current_time)

def get_last_update():
  conn = get_database_connection()
  c = conn.cursor()
  last_update = c.execute("SELECT MAX(timestamp) FROM ticks").fetchone()[0]
  if not last_update:
    last_update = 0
  return last_update

def update_system(systemName, local = False):
  data_system = get_json_data("system_{0}.json".format(systemName),
                   "https://www.edsm.net/api-v1/system",
                   {'systemName': systemName,'showPrimaryStar':1,'showInformation':1}, 
                   local)
  return data_system

def update_state_entry(timestamp,state_name,state_type,faction_name, system_name, trend):
  conn = get_database_connection()
  c = conn.cursor()
  values = [timestamp,state_name,state_type,faction_name, system_name, trend]
  c.execute("INSERT INTO faction_system_state VALUES",values)
  c.commit()

def update_tick(cur_time = None, local = False, history = False):
  conn = get_database_connection()
  c = conn.cursor()
  current_time = get_timestamp(cur_time)
  if not is_update_needed(conn,current_time):
    debug("UPDATE NOT NEEDED")
    return False
  else:
    debug("UPDATE NEEDED")
  if not history:
    print("update TICK")
    c.execute("INSERT INTO ticks VALUES (?)",[current_time])
  star_systems = fetch_systems("population > 0 ORDER BY population")
  total_systems = len(star_systems)
  current_start_system = 1
  for star_system in star_systems:
    systemName = star_system[0]
    system_info = update_system(systemName)
    sys.stdout.write("Updating System {0} [{1}/{2}]           \r".format(systemName,current_start_system,total_systems))
    current_start_system += 1
    sys.stdout.flush()
    values = [current_time,systemName,system_info['information']['faction'],system_info['information']['security']]
    if not history:
      c.execute("INSERT INTO system_status VALUES (?,?,?,?)",values)
    
    data_factions = get_json_data("factions_{0}.json".format(systemName),
                         "https://www.edsm.net/api-system-v1/factions",
                         {'systemName': systemName,'showHistory':1}, 
                         local)
    if not data_factions['factions']:
      return False
    
    for faction in data_factions['factions']:
      system_faction_entries = []
      active_state_entries = []
      pending_state_entries = []
      recovering_state_entries = []  
      if history:
        for timestamp in faction['stateHistory']:
          state = faction['stateHistory'][timestamp]
          active_state_entries.append([int(timestamp),state,'activeState',faction['name'],systemName,0])
          #print(timestamp,state)
        for timestamp in faction['influenceHistory']:
          system_faction_entries.append([int(timestamp),
            faction['name'],
            systemName,
            faction['influenceHistory'][timestamp]])
        if faction['recoveringStatesHistory']:
          for timestamp,state in faction['recoveringStatesHistory'].items():
            if not state:
              continue
            state = state[0]
            recovering_state_entries.append([int(timestamp),
                                  state['state'],
                                  "recoveringState",
                                  faction['name'],
                                  systemName,
                                  state['trend']])
        if faction['pendingStatesHistory']:
          for timestamp,state in faction['pendingStatesHistory'].items():
            if not state:
              continue
            state = state[0]
            pending_state_entries.append([int(timestamp),
                                  state['state'],
                                  "pendingState",
                                  faction['name'],
                                  systemName,
                                  state['trend']])
      else: 
        system_faction_entries.append([current_time,
                                        faction['name'],
                                        systemName,
                                        faction['influence']])
        active_state_entries.append([current_time,faction['state'],'activeState',faction['name'],systemName,0])
        for state in faction['recoveringStates']:
          pending_state_entries.append([current_time,
                                state['state'],
                                "recoveringState",
                                faction['name'],
                                systemName,
                                state['trend']])
        for state in faction['pendingStates']:
          recovering_state_entries.append([current_time,
                                state['state'],
                                "pendingState",
                                faction['name'],
                                systemName,
                                state['trend']])
      for values in system_faction_entries:
        if history:
          check_query = """
          SELECT * FROM faction_system WHERE
          date={0} AND
          name="{1}" AND
          system="{2}" AND
          influence={3}""".format(*values)
          c.execute(check_query)
          if c.fetchone():
            #debug("ENTRY_ALREADY_EXISTS")
            continue
        c.execute("INSERT INTO faction_system VALUES (?,?,?,?)",values)
        
      for values in active_state_entries:
        c.execute("INSERT INTO faction_system_state VALUES (?,?,?,?,?,?)",values)
      for values in pending_state_entries:
        c.execute("INSERT INTO faction_system_state VALUES (?,?,?,?,?,?)",values)
      for values in recovering_state_entries:
        c.execute("INSERT INTO faction_system_state VALUES (?,?,?,?,?,?)",values)
        
        if history:  
          conn.commit()
  conn.commit()
  return True

def time_functions_test():
  for test_check_time in ["10-02-2018 13:29:00",
                  "10-02-2018 13:30:00",
                  "10-02-2018 13:35:00",
                  "11-02-2018 13:29:00",
                  "11-02-2018 13:30:00",
                  "11-02-2018 13:38:00",
                  "9-02-2018 13:30:00"]:
    debug("UPDATE NEEDED: {0}".format(is_update_needed(get_timestamp(test_check_time))))
    debug('*'*80)