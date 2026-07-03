--[[
  SnowRunner — TelemetryLogger v9

  ORDEN IMPORTANTE:
    1) Abre SnowRunner, entra al MAPA conduciendo
    2) CE -> File -> Open Process -> SnowRunner.exe
    3) Table -> Show Cheat Table Lua Script -> TelemetryLogger.lua -> Execute
    4) debugTelemetry()

  Si singleton=0 en Lua pero la tabla CE muestra datos:
    attachSnowRunner()  luego  useCheatTablePointers()
]]

local MODULE = "SnowRunner.exe"
local INTERVAL_MS = 500

local TRUCK_CONTROL_OFF = 0x2A8EDD8  -- RTTI TRUCK_CONTROL (build 2026-06-25; antes 0x2A876A8)
local DRIVE_LOGIC_OFF    = 0x2A8EDC8  -- validado mismo build

local OFF_VEH_TRUCK = 0x8
local OFF_VEH_DRIVE = 0x20
local OFF_RB          = 0x5D0  -- era 0x5C8 (Patch 18.0); validado RTTI build 2026
local OFF_VX          = 0x230
local OFF_VY          = 0x234
local OFF_VZ          = 0x238
local OFF_YAW         = 0x244
local OFF_POS_Y       = 0x1A4  -- altitud mundo (hkTransform Y)
local OFF_ID          = 0xD10  -- era 0xCE8; ptr -> s_chevrolet_ck1500
local OFF_ADDON       = 0x48   -- era 0x58; addon manager
local OFF_FUEL        = 0x568
local OFF_FUEL_MAX    = 0x570

local BASE_DIR = os.getenv("USERPROFILE") .. "/Documents/My Games/SnowRunner/base/"
local LOG_PRIMARY = BASE_DIR .. "telemetria_ce_log.csv"
local LOG_FALLBACK = "C:/Users/doski/snowrunner real/cheat_engine/telemetria_ce_log.csv"
local STATUS_PATH = BASE_DIR .. "telemetria_ce_status.txt"

local SPAWN_ARRAY_OFF = 0x2E6FC40
local OFF_SPAWN_VEH0 = 0x40
local OFF_SPAWN_VEH_STEP = 0x8

local CT_ID_SINGLETON = 687
local CT_ID_VEH = 688
local CT_ID_VEL_X = 722

local timer, t0, headerWritten, logPath, failStreak, lastDiagPrint
local cachedVeh, cachedRb, cachedChain
local lastVehicleId
local useCTMode = false
local singletonDead = false

local function writeStatus(msg)
  local f = io.open(STATUS_PATH, "w")
  if f then f:write(os.date("%Y-%m-%d %H:%M:%S") .. "\n" .. msg .. "\n"); f:close() end
end

local function pickLogPath()
  for _, p in ipairs({ LOG_PRIMARY, LOG_FALLBACK }) do
    local f = io.open(p, "a")
    if f then f:close(); return p end
  end
  return nil
end

local function moduleBase()
  local b = getAddress(MODULE)
  if b and b ~= 0 then return b end
  b = getAddressSafe(MODULE)
  if b and b ~= 0 then return b end
  pcall(function()
    local ml = enumModules()
    for i = 0, ml.Count - 1 do
      local n = ml.getString(i):lower()
      if n:find("snowrunner.exe", 1, true) then
        b = getAddress(ml.getString(i))
      end
    end
  end)
  return b
end

local function readQwordSafe(addr)
  if not addr or addr == 0 then return 0 end
  local ok, p = pcall(function() return readPointer(addr) end)
  if ok and type(p) == "number" and p ~= 0 then return p end
  if readQword then
    ok, p = pcall(function() return readQword(addr) end)
    if ok and type(p) == "number" and p ~= 0 then return p end
  end
  ok, p = pcall(function() return readInteger(addr) end)
  if ok and type(p) == "number" then return p end
  return 0
end

function attachSnowRunner()
  local pid = getProcessIDFromProcessName("SnowRunner.exe")
  if not pid or pid == 0 then
    print("[CE] SnowRunner.exe no esta corriendo")
    return false
  end
  openProcess(pid)
  print("[CE] Adjuntado PID", pid, "| abierto:", getOpenedProcessID())
  return true
end

local function readVehicleId(veh)
  if not veh or veh == 0 then return "" end
  local ok, id = pcall(function()
    local p = readPointer(veh + OFF_ID)
    if p and p ~= 0 then return readString(p, 64, true) or readString(p, 64) or "" end
    return readString(veh + OFF_ID, 64, true) or ""
  end)
  return (ok and id) or ""
end

local function readFuelPct(veh)
  if not veh or veh == 0 then return "" end
  local addon = readPointer(veh + OFF_ADDON)
  if not addon or addon == 0 then return "" end
  local c, m = readFloat(addon + OFF_FUEL), readFloat(addon + OFF_FUEL_MAX)
  if not c or not m or m <= 0 then return "" end
  return string.format("%.1f", (c / m) * 100)
end

local function speedKmh(rb)
  local vx = readFloat(rb + OFF_VX) or 0
  local vz = readFloat(rb + OFF_VZ) or 0
  return math.sqrt(vx * vx + vz * vz) * 3.6
end

local function mrResolvedAddr(mr)
  if mr == nil then return nil end
  local ok, a = pcall(function()
    if mr.CurrentAddress and mr.CurrentAddress ~= 0 then return mr.CurrentAddress end
    if mr.getCurrentAddress then
      local ca = mr.getCurrentAddress()
      if ca and ca ~= 0 then return ca end
    end
    if mr.Address and mr.Address ~= "" then return getAddress(mr.Address) end
    return nil
  end)
  return ok and a or nil
end

function listCTEntries(filter)
  local al = getAddressList()
  if al == nil then print("[CE] sin address list"); return end
  filter = filter and filter:lower() or nil
  print("=== listCTEntries ===")
  for i = 0, al.Count - 1 do
    local mr = al.getMemoryRecord(i)
    local desc = mr.Description or ""
    if not filter or desc:lower():find(filter, 1, true) then
      local addr = mrResolvedAddr(mr)
      print(string.format("id=%d desc=%s addr=%s", mr.ID, desc, addr and string.format("%X", addr) or "nil"))
    end
  end
end

local function findMemrecById(id)
  local al = getAddressList()
  if al == nil then return nil end
  for i = 0, al.Count - 1 do
    local mr = al.getMemoryRecord(i)
    if mr.ID == id then return mr end
  end
  return nil
end

local function findMemrec(needle)
  local al = getAddressList()
  if al == nil then return nil end
  local best = nil
  for i = 0, al.Count - 1 do
    local mr = al.getMemoryRecord(i)
    local d = (mr.Description or ""):lower()
    if d:find(needle:lower(), 1, true) then
      best = mr
      if d == needle:lower() then return mr end
    end
  end
  return best
end

local function refreshFromCT(verbose)
  local singMr = findMemrecById(CT_ID_SINGLETON) or findMemrec("TRUCK_CONTROL singleton")
  local vehMr = findMemrecById(CT_ID_VEH) or findMemrec("current veh obj")
  local velMr = findMemrecById(CT_ID_VEL_X) or findMemrec("linear velocity x")

  if verbose then
    print("[CE] refreshFromCT:")
    print("  sing rec:", singMr and (singMr.Description .. " id=" .. tostring(singMr.ID)) or "NO")
    print("  veh rec:", vehMr and (vehMr.Description .. " id=" .. tostring(vehMr.ID)) or "NO")
    print("  vel rec:", velMr and (velMr.Description .. " id=" .. tostring(velMr.ID)) or "NO")
  end

  if singMr then
    local slot = mrResolvedAddr(singMr)
    if not slot or slot == 0 then
      local base = moduleBase()
      if base then slot = base + TRUCK_CONTROL_OFF end
    end
    if slot and slot ~= 0 then
      local singleton = readQwordSafe(slot)
      if verbose then print(string.format("  singleton slot %X -> %X", slot, singleton)) end
      if singleton ~= 0 then
        local veh = readQwordSafe(singleton + OFF_VEH_TRUCK)
        if veh ~= 0 then
          cachedVeh = veh
          cachedRb = readPointer(veh + OFF_RB) or 0
          cachedChain = "CT:singleton"
          if verbose then print(string.format("  veh=%X rb=%X", cachedVeh, cachedRb or 0)) end
        end
      end
    end
  end

  if velMr then
    local vxAddr = mrResolvedAddr(velMr)
    if vxAddr and vxAddr ~= 0 then
      cachedRb = vxAddr - OFF_VX
      cachedChain = "CT:velX"
      if verbose then
        print(string.format("  rb=%X (velX @ %X)", cachedRb, vxAddr))
      end
    end
  end

  if vehMr then
    local field = mrResolvedAddr(vehMr)
    if field and field ~= 0 then
      local veh = readQwordSafe(field)
      if veh ~= 0 then
        cachedVeh = veh
        if not cachedRb or cachedRb == 0 then
          cachedRb = readPointer(veh + OFF_RB) or 0
        end
        cachedChain = "CT:veh"
        if verbose then
          print(string.format("  veh=%X rb=%X", cachedVeh, cachedRb or 0))
        end
      elseif verbose then
        print(string.format("  field@%X pero veh=0", field))
      end
    elseif verbose then
      print("  veh memrec sin direccion resuelta (¿tabla activa en mapa?)")
    end
  end

  return cachedRb and cachedRb ~= 0
end

function useCheatTablePointers()
  useCTMode = true
  cachedVeh, cachedRb, cachedChain = nil, nil, nil
  if refreshFromCT(true) then
    writeStatus("CT OK rb=" .. string.format("%X", cachedRb))
    print("[CE] CT OK km/h=", string.format("%.1f", speedKmh(cachedRb)))
    return true
  end
  print("[CE] Sin datos en tabla. Carga debug.CT, conduce en mapa, reintenta.")
  return false
end

function bindVeh(hexVeh)
  local veh = tonumber(hexVeh, 16) or getAddress(hexVeh)
  if not veh or veh == 0 then return false end
  local rb = readPointer(veh + OFF_RB)
  if not rb or rb == 0 then print("rb=0 en veh", string.format("%X", veh)); return false end
  cachedVeh, cachedRb = veh, rb
  cachedChain = "MANUAL:veh"
  useCTMode = true
  print(string.format("[CE] bindVeh OK veh=%X rb=%X km/h=%.1f", veh, rb, speedKmh(rb)))
  return true
end

function bindRb(hexRb)
  local rb = tonumber(hexRb, 16) or getAddress(hexRb)
  if not rb or rb == 0 then return false end
  cachedRb = rb
  cachedVeh = nil
  cachedChain = "MANUAL:rb"
  useCTMode = true
  print(string.format("[CE] bindRb OK rb=%X km/h=%.1f", rb, speedKmh(rb)))
  return true
end

local function chainSingleton(off, vehOff, tag)
  local base = moduleBase()
  if not base or base == 0 then return nil, nil, tag .. ": sin modulo" end
  local slot = base + off
  local singleton = readQwordSafe(slot)
  if not singleton or singleton == 0 then
    return nil, nil, string.format("%s: singleton=0 @ %X", tag, slot)
  end
  local veh = readQwordSafe(singleton + vehOff)
  if not veh or veh == 0 then return nil, nil, tag .. ": veh=0" end
  local rb = readPointer(veh + OFF_RB)
  if not rb or rb == 0 then return veh, nil, tag .. ": rb=0" end
  return veh, rb, tag
end

local function terrainHint(speed_kmh, vel_y)
  -- Marcha reducida (2-16 km/h): no distingue asfalto vs barro solo por velocidad.
  if speed_kmh < 2 then return "idle"
  elseif speed_kmh > 28 then return "hard_fast"
  elseif speed_kmh < 16 and vel_y < -0.12 then return "crawl_deep"
  elseif speed_kmh < 16 then return "crawl"
  else return "cruise" end
end

local function resolveFromSingleton()
  local veh, rb, chain = chainSingleton(TRUCK_CONTROL_OFF, OFF_VEH_TRUCK, "TRUCK_CONTROL")
  if rb then return veh, rb, chain end
  return chainSingleton(DRIVE_LOGIC_OFF, OFF_VEH_DRIVE, "DRIVE_LOGIC")
end

local function getVehiclePointers()
  -- Siempre re-leer singleton: al cambiar de camion TRUCK_CONTROL+8 apunta al nuevo vehiculo.
  local veh, rb, chain = resolveFromSingleton()
  if rb then
    cachedVeh, cachedRb, cachedChain = veh, rb, chain
    return veh, rb, chain
  end

  if cachedRb and cachedRb ~= 0 and readFloat(cachedRb + OFF_VX) ~= nil then
    return cachedVeh, cachedRb, cachedChain
  end

  refreshFromCT(false)
  if cachedRb and cachedRb ~= 0 then
    useCTMode = true
    return cachedVeh, cachedRb, cachedChain
  end

  return nil, nil, chain or "singleton=0 (menu/garaje?)"
end

function forceVehicleRescan()
  cachedVeh, cachedRb, cachedChain = nil, nil, nil
  lastVehicleId = nil
  singletonDead = false
  print("[CE] Cache borrada.")
end

function debugTelemetry()
  print("=== debugTelemetry v9 ===")
  print("PID abierto:", getOpenedProcessID(), "| PID juego:", getProcessIDFromProcessName("SnowRunner.exe"))
  local base = moduleBase()
  print("Module base:", base and string.format("%X", base) or "NO")

  if base then
    local slot = base + TRUCK_CONTROL_OFF
    local raw = readQwordSafe(slot)
    print(string.format("  [%X] TRUCK_CONTROL slot %X -> %X", TRUCK_CONTROL_OFF, slot, raw))
    slot = base + DRIVE_LOGIC_OFF
    print(string.format("  [%X] DRIVE_LOGIC   slot %X -> %X", DRIVE_LOGIC_OFF, slot, readQwordSafe(slot)))
  end

  forceVehicleRescan()
  useCTMode = false
  local veh, rb, chain = getVehiclePointers()
  print("Cadena:", chain or "?")

  if veh then
    print("  veh=", string.format("%X", veh), "id=", readVehicleId(veh))
  end
  if rb then
    print("  rb =", string.format("%X", rb), "km/h=", string.format("%.1f", speedKmh(rb)))
    writeStatus(string.format("OK %s km/h=%.1f", chain, speedKmh(rb)))
  else
    print("  rb=0")
    print("  SIGUIENTE:")
    print("    1) Carga debug.CT  2) attachSnowRunner()  3) useCheatTablePointers()")
    print("    O copia veh hex de la tabla: bindVeh(\"HEX\")")
    writeStatus("singleton=0. Carga debug.CT + useCheatTablePointers()")
  end
end

local function logLine()
  local veh, rb, chain
  local ok, err = pcall(function()
    veh, rb, chain = getVehiclePointers()
  end)
  if not ok then
    print("[CE] Error logLine:", err)
    return
  end
  if not rb then
    failStreak = (failStreak or 0) + 1
    if os.clock() - (lastDiagPrint or 0) > 8 then
      lastDiagPrint = os.clock()
      print(string.format("[CE] Sin datos (%d). useCheatTablePointers()", failStreak))
    end
    return
  end

  failStreak = 0
  if not logPath then logPath = pickLogPath(); if logPath then print("[CE] Logging -> " .. logPath) end end
  if not logPath then return end

  local vx = readFloat(rb + OFF_VX) or 0
  local vy = readFloat(rb + OFF_VY) or 0
  local vz = readFloat(rb + OFF_VZ) or 0
  local spd = speedKmh(rb)
  local vehId = veh and readVehicleId(veh):gsub("[\t\r\n,]", " ") or ""
  local event = ""
  if vehId ~= "" then
    if lastVehicleId and lastVehicleId ~= vehId then
      event = "vehicle_change"
      print(string.format("[CE] Cambio camion: %s -> %s", lastVehicleId, vehId))
    end
    lastVehicleId = vehId
  end

  local f = io.open(logPath, headerWritten and "a" or "w")
  if not f then return end
  if not headerWritten then
    f:write("t_s,speed_kmh,vel_x,vel_y,vel_z,ang_yaw,pos_y,fuel_pct,vehicle_id,terrain_hint,event,chain\n")
    headerWritten, t0 = true, os.clock()
    writeStatus("OK logging -> " .. logPath)
  end

  f:write(string.format("%.2f,%.2f,%.4f,%.4f,%.4f,%.4f,%.4f,%s,%s,%s,%s,%s\n",
    os.clock() - t0, spd, vx, vy, vz,
    readFloat(rb + OFF_YAW) or 0, readFloat(rb + OFF_POS_Y) or 0,
    veh and readFuelPct(veh) or "", vehId,
    terrainHint(spd, vy), event, chain or ""))
  f:close()
end

function startTelemetryLogger()
  if timer then return end
  if not getOpenedProcessID() or getOpenedProcessID() == 0 then attachSnowRunner() end
  logPath, headerWritten, t0 = pickLogPath(), false, nil
  failStreak, lastDiagPrint = 0, 0
  lastVehicleId = nil
  useCTMode = false
  cachedVeh, cachedRb, cachedChain = nil, nil, nil
  singletonDead = false
  timer = createTimer(nil)
  timer.Interval = INTERVAL_MS
  timer.OnTimer = logLine
  print("[CE] TelemetryLogger v9.5 — free roam OK (cambio camion auto)")
  print("[CE] Conduce, cambia camion/mapa; stopTelemetryLogger() al terminar sesion")
end

function stopTelemetryLogger()
  if timer then timer.destroy(); timer = nil end
end

function quickStart()
  stopTelemetryLogger()
  attachSnowRunner()
  local veh, rb, chain = getVehiclePointers()
  if not rb then
    print("[CE] Sin vehiculo aun. Entra al mapa conduciendo y ejecuta quickStart() otra vez.")
    print("[CE] O usa: python grabar_ce.py  (sin Cheat Engine)")
    return false
  end
  print(string.format("[CE] OK %s id=%s km/h=%.1f", chain or "?", veh and readVehicleId(veh) or "?", speedKmh(rb)))
  startTelemetryLogger()
  print("[CE] Grabando. stopTelemetryLogger() al terminar.")
  return true
end

-- No auto-start: quickStart() o startTelemetryLogger() tras debugTelemetry() OK
print("[CE] TelemetryLogger v9.6 — quickStart() | grabar_ce.py sin CE")
