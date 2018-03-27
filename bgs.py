from utils import *

def get_system_status(systemName,timestamp  = None):
  if not timestamp:
    timestamp = get_last_update()
  else:
    timestamp = get_timestamp(timestamp)
  conn = get_database_connection()
  c = conn.cursor()
  c.execute("""SELECT DISTINCT faction_system.date,
                        faction_system.system,
                        faction_system.name,
                        faction_system.influence,
                        faction_system.state,
                        faction_system_state.state_name,
                        faction_system_state.state_type
                  FROM faction_system, faction_system_state
                  WHERE faction_system.system = '{0}'
                  AND faction_system_state.system_name = '{0}'
                  AND faction_system.date = {1}
                  AND faction_system_state.date = {1}""".format(systemName,timestamp))
  return [systemName,c.fetchall()]

def get_system_status_timespan(systemName, initialTimestamp,endTimestamp = None):
  if not endTimestamp:
    endTimestamp = get_time()
  conn = get_database_connection()
  c = conn.cursor()
  query = '''SELECT DISTINCT faction_system.date,
                        faction_system.system,
                        faction_system.name,
                        faction_system.influence,
                        faction_system.state,
                        faction_system.controller,
                        faction_system_state.state_name,
                        faction_system_state.state_type,
                        faction_system_state.trend
                  FROM faction_system, faction_system_state
                  WHERE faction_system.system = "{0}"
                  AND faction_system_state.system_name = "{0}"'''.format(systemName)
  c.execute(query)  
  all_entries = c.fetchall()
  return [systemName,[ entry for entry in all_entries if entry[0] >= initialTimestamp and entry[0] < endTimestamp]]

def get_all_entries():
  conn = get_database_connection()
  c = conn.cursor()
  c.execute("SELECT * FROM faction_system")  
  return c.fetchall()


class Faction:
  def __init__(self,faction_name):
    conn = get_database_connection()
    c = conn.cursor()
    self.name = faction_name
    self.ok = False
    self.json = ""
    if 1:
      c.execute('SELECT allegiance,government,is_player,native_system FROM Factions WHERE faction_name = "{0}"'.format(faction_name))
      self.allegiance, self.government, self.is_player, self.native_system = c.fetchone()
      c.execute('SELECT state_name FROM faction_system_state WHERE faction_name = "{0}" AND date = {1} AND state_type="activeState"'.format(self.name,get_last_update()))
      state_data = c.fetchone()
      if not state_data:
        c.execute('SELECT date,state_name FROM faction_system_state WHERE faction_name = "{0}" AND state_type="activeState"'.format(self.name))
        self.state = max(c.fetchall(),key=lambda x: x[0])[1]
      else:
        self.state = state_data[0]
      self.ok = True
#    except:
#      None
    if self.ok:
      self.json = {"name":self.name,"allegiance":self.allegiance,"government":self.government,"isPlayer":self.is_player,"native_system":self.native_system,"state":self.state}
  def __repr__(self):
    return str(self.json)

  @classmethod
  def get_all_factions(cls,criteria=None):
    criteria_sql = ""
    if criteria:
      if isinstance(criteria, (list,tuple)):
        criteria_sql = " WHERE " + " AND ".join(criteria)
      elif isinstance(criteria,str):
        criteria_sql = " WHERE " + criteria
      else:
        return None
    c = conn.cursor()
    c.execute('SELECT faction_name FROM Factions{0}'.format(criteria_sql))
    factions = c.fetchall()
    factions = [Faction(faction[0]) for faction in factions]
    return factions
  
  def get_retreat_risk(self,threshold = RETREAT_THRESHOLD):
    systems = self.get_systems()
    risked = []
    if systems:
      for system_name in systems:
        influence = self.get_status_in_system(system_name).popitem()[1]['status']['influence']
        if influence > 0.0 and influence < threshold:
          risked.append([system_name,influence])
    return(risked)
  
  def get_expansion_risk(self,threshold = EXPANSION_THRESHOLD):
    systems = self.get_systems()
    risked = []
    if systems:
      for system_name in systems:     
        influence = self.get_status_in_system(system_name).popitem()[1]['status']['influence']
        if influence > threshold:
          risked.append([system_name,influence])
      return(risked)
  
  
  def get_systems(self, start_timestamp = None, end_timestamp = None):
    if not self.ok:
        return None  
    conn = get_database_connection()
    c = conn.cursor()
    if start_timestamp == None:
      start_timestamp = get_last_update()
    else:
      start_timestamp = get_time(start_timestamp)
    if end_timestamp == None:
      end_timestamp = get_last_update()
      
    else:
      end_timestamp = get_time(end_timestamp)
    c.execute('SELECT DISTINCT system FROM faction_system WHERE name = "{0}" AND date >= {1} AND date <= {2}'.format(self.name,start_timestamp,end_timestamp))
    systems = [system[0] for system in c.fetchall() ]
    return(systems)
  
  def get_current_influence_in_system(self,system_requested):
    if not self.ok:
      return None
    if isinstance(system_requested,System):
      system_requested = system_requested.name
    conn = get_database_connection()
    c = conn.cursor()
    c.execute('SELECT influence FROM faction_system WHERE system = "{0}" AND name = "{1}" and date = {2}'.format(system_requested,self.name,get_last_update()))  
    influence_data = c.fetchone()
    if len(influence_data) > 0:
#      print("{0} has {1:.2f}% influence in system {2}".format(self.name,influence_data[0]*100.0,system_requested)) 
      return influence_data[0]
    return None
  
  def get_current_pending_states(self):
    if not self.ok:
        return None
    conn = get_database_connection()
    c = conn.cursor()
    c.execute('SELECT DISTINCT state_name, trend FROM faction_system_state WHERE faction_name = "{0}" AND date ={1} AND state_type="pendingState"'.format(self.name,get_last_update()))
    return c.fetchall()
  
  def get_current_recovering_states(self):
    if not self.ok:
        return None
    conn = get_database_connection()
    c = conn.cursor()
    c.execute('SELECT DISTINCT state_name, trend FROM faction_system_state WHERE faction_name = "{0}" AND date ={1} AND state_type="recoveringState"'.format(self.name,get_last_update()))
    return c.fetchall()
  
  def get_status_in_system(self,system_name, start_timestamp = None, end_timestamp = None):
    if not self.ok:
        return None
    conn = get_database_connection()
    c = conn.cursor()
    if start_timestamp == None:
      start_timestamp = get_last_update()
    else:
      start_timestamp = get_time(start_timestamp)
    if end_timestamp == None:
      end_timestamp = get_last_update()
    else:
      end_timestamp = get_time(end_timestamp)

    timestamps = defaultdict(dict)
    c.execute('SELECT date,influence FROM faction_system WHERE name = "{0}" AND system = "{1}" AND date >= {2} AND date <= {3}'.format(self.name,system_name,start_timestamp,end_timestamp))
    status_entries =  list(c.fetchall())
    c.execute('SELECT date,state_name,state_type,trend FROM faction_system_state WHERE faction_name = "{0}" AND system_name = "{1}" AND date >= {2} AND date <= {3}'.format(self.name,system_name,start_timestamp,end_timestamp))
    state_entries = list(c.fetchall())
    for entry in state_entries:
      timestamp,state_name,state_type,trend = entry
      timestamp = str(int(float(timestamp)))
      timestamps[timestamp][state_type + 's'] = {'state':state_name, 'trend':trend}
    for entry in status_entries:
      timestamp,influence = entry
      timestamp = str(int(float(timestamp)))
      timestamps[timestamp]['status'] = {'influence':influence,'state':state_name}
    return timestamps

  def get_status_history_in_system(self,star_system):
    entries = []
    status_history = self.get_status_in_system(star_system,start_timestamp=0)
    for entry in sorted(status_history):
      entries.append((get_utc_time_from_epoch(entry),status_history[entry]))
    return entries

class System:
  def __init__(self,system_name):
    conn = get_database_connection()
    c = conn.cursor()
    self.name = system_name
    self.ok = False
    self.json = ""
    try:
      c.execute('SELECT population,economy,distance FROM Systems WHERE name = "{0}"'.format(system_name))
      self.population, self.economy, self.distance = c.fetchone()
      self.ok = True
    except:
      None
    if self.ok:
      self.json =  {"name":self.name,"population":self.population,"economy":self.economy,"distance":self.distance}
  
  @classmethod
  def get_all_systems(cls):
    conn = get_database_connection()
    c = conn.cursor()
    c.execute('SELECT name FROM Systems')
    factions = [System(faction[0]) for faction in c.fetchall()]
    return factions
  
  
  def get_controller(self,timestamp = None):
    if not self.ok:
      return None
    conn = get_database_connection()
    c = conn.cursor()
    if not timestamp:
      timestamp = get_last_update()
    c.execute('SELECT controller_faction FROM system_status WHERE system = "{0}" AND date = "{1}"'.format(self.name,timestamp))
    data = c.fetchone()
    if data:
      faction_name =  data[0]
      return Faction(faction_name)
    else:
      return None
    
  def get_war_risk(self,threshold = WAR_THRESHOLD):
    factions = self.get_factions()
    factions_in_risk = []
    if factions:
      for faction1,faction2 in itertools.combinations(factions,2):
        influence1 = faction1.get_current_influence_in_system(self.name)
        influence2 = faction2.get_current_influence_in_system(self.name)
        if influence1 and influence2:
          if abs(influence1 - influence2) < threshold:
            factions_in_risk.append([faction1,faction2])
    return factions_in_risk
      
  def get_factions(self, start_timestamp = None, end_timestamp = None):
    if not self.ok:
      return None
    conn = get_database_connection()
    c = conn.cursor()
    if start_timestamp == None:
      start_timestamp = get_last_update()
    else:
      start_timestamp = get_time(start_timestamp)
    if end_timestamp == None:
      end_timestamp = get_last_update()
    else:
      end_timestamp = get_time(end_timestamp)

    c.execute('SELECT name FROM faction_system WHERE system = "{0}" AND date >= {1} AND date <= {2}'.format(self.name,start_timestamp,end_timestamp))
    factions = [Faction(faction[0]) for faction in c.fetchall()]
    return factions
  
  def get_current_factions(self, start_timestamp = None, end_timestamp = None):
    return self.get_factions(start_timestamp,end_timestamp)
    
  def __repr__(self):
    return str(self.json)

def get_factions_with_retreat_risk(threshold = RETREAT_THRESHOLD):
  ret_risked = []
  for faction in Faction.get_all_factions():
    risked = faction.get_retreat_risk(threshold)
    if risked:
      for system in risked:
        system_name, influence = system
        if not faction.name.startswith(system_name):
          ret_risked.append({"faction":faction.name,"system":system_name,"influence":influence, "state":faction.state})
  return ret_risked

def get_factions_with_expansion_risk(threshold = EXPANSION_THRESHOLD):
  ret_risked = []
  for faction in Faction.get_all_factions():
    risked = faction.get_expansion_risk(threshold)
    if risked:
      for system in risked:
        system_name, influence = system
        if not faction.name.startswith(system_name):
          ret_risked.append({"faction":faction.name,"system":system_name,"influence":influence, "state":faction.state})
  return ret_risked

def get_trend_text(trend):
  if trend == 0:
    return "="
  elif trend > 0:
    return "+"
  else:
    return "-"

def get_retreat_risk_report(threshold = RETREAT_THRESHOLD):
  report = "\n" + "*"*10 + "RETREAT RISK REPORT" + "*"*10 + "\n\n"
  
  report += "The following factions are in risk of enter in state of Retreat:\n"
  for risk in get_factions_with_retreat_risk(threshold):
    pending_states = ", ".join(["{0} ({1})".format(pending_state,get_trend_text(trend)) for pending_state, trend in Faction(risk['faction']).get_current_pending_states()])
    if not pending_states:
      pending_states = "None"
    recovering_states = ", ".join(["{0} ({1})".format(recovering_state,get_trend_text(trend)) for recovering_state, trend in Faction(risk['faction']).get_current_recovering_states()])
    if not recovering_states:
      recovering_states = "None"
  
    report += "'{0}' in system '{1}' (Influence: {2:.3g} %, State: {3}, Pending: {4}, Recovering: {5}, Distance: {6} lys)\n".format(risk['faction'],risk['system'],risk['influence']*100.0,risk['state'], pending_states, recovering_states,System(risk['system']).distance)
  return report

def get_war_risk_report(threshold = WAR_THRESHOLD):
  report = "\n" + "*"*10 + "WAR RISK REPORT" + "*"*10 + "\n"
  report += "The following factions are in risk of enter in state of War:\n"
  for system in System.get_all_systems():
    for faction1, faction2 in system.get_war_risk(threshold):
      report += "'{0}' ({1:.2f}%) versus '{2}' ({3:.2f}%) in '{4}'\n".format(faction1.name, faction1.get_current_influence_in_system(system.name)*100.0,
                                                                  faction2.name,faction2.get_current_influence_in_system(system.name)*100.0,system.name)
  return report

def get_expansion_risk_report(threshold = EXPANSION_THRESHOLD):
  report = "\n" + "*"*10 + "EXPANSION RISK REPORT" + "*"*10 + "\n"
  report += "The following factions are in risk of enter in state of Expansion:\n"
  for risk in get_factions_with_expansion_risk(threshold):
    report += "'{0}' from system '{1}' (Influence: {2:.3g} %, State: {3}, Distance: {4} lys)\n".format(risk['faction'],risk['system'],risk['influence']*100.0,risk['state'], System(risk['system']).distance)
  return report




def fresh_start(system_name):
  clean_fixed_tables()
  clean_updates()
  clean_local_json_path()
  fill_systems_in_bubble(system_name,EXPANSION_RADIUS,local=True)
  update_tick(get_timestamp("23-02-2018 13:30:00"),local = True,history = True)
  


if 0:
  defence = Faction("Defence Party of Naunin")
  print(defence)  
  
  for faction in Faction.get_all_factions(('faction_name LIKE "%Naunin%"')):
    print(faction)
  


  print(System.get_all_systems())
  
  my_system = System("Maopi")
  f = Faction('Naunin Jet Netcoms Incorporated')
  
  kb = Faction("Kupol Bumba Alliance")
  print(kb)
  print(kb.get_current_influence_in_system("Naunin"))
  
  f = Faction('Naunin Jet Netcoms Incorporated')

def get_risk_report():
  print(get_retreat_risk_report(0.025))
  print(get_war_risk_report(0.01))
  print(get_expansion_risk_report(0.7))


def get_player_report():
  report = ""
  factions = defaultdict(list)
  for star_system in System.get_all_systems():
    faction = star_system.get_controller()
    if faction and faction.is_player:
      factions[faction.name].append([star_system.name,star_system.distance,star_system.population,faction.get_current_influence_in_system(star_system.name)])
  
  
  for faction in factions:
    report +='Faction {0} controls {1} systems:\n'.format(faction, len(factions[faction]))
    for controlled_system,distance,population,influence in factions[faction]:
      report += "\t{0} (influence: {1:.1f}%, distance: {2}lys, population: {3})\n".format(controlled_system,influence*100.0,distance,population)
  return report

def get_system_status_history(star_system):
  entries = []
  for faction in System(star_system).get_factions():
    status_history = faction.get_status_in_system(star_system,start_timestamp=0)
    for entry in sorted(status_history):
      print(entry)
      entries.append((get_utc_time_from_epoch(entry),faction,status_history[entry]))
  return entries

update_tick()
history = get_system_status_history("Naunin")
for entry in history:
  if 'status' in entry[2]:
    print(entry[0],entry[1].name,entry[2]['status']['influence'])
    
history = Faction("Kupol Bumba Alliance").get_status_history_in_system("Naunin")
state = "N/A"
for entry in history:
  if 'status' in entry[1]:
    if 'activeStates' in entry[1]:
      state = entry[1]['activeStates']['state']
    print(",".join((entry[0].split(" ")[0],"{0:.8f} {1}".format(entry[1]['status']['influence'],state))))

close_database_connection()

exit(0)

