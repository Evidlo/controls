#!/usr/bin/env python
# Evan Widloski - 2017-09-03
# Glue logic for controlling drone and triggering radio measurement

from dronekit import VehicleMode, connect, Command
from nav_commands import goto_absolute_nea, takeoff, delay
from pymavlink import mavutil
from radio import log_test
import logging
import time
import sys

log = logging.getLogger()
log.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# log to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
# log to file
handler = logging.FileHandler('main.log')
handler.setFormatter(formatter)

# -------------------- Connect to pixhawk -----------------------

connections = []
# try to connect to simulator
connections.append('tcp:localhost:14551')
# try to connect to pixhawk over serial port
preferred_list=['*FTDI*', "*Arduino_Mega_2560*", "*3D_Robotics*", "*USB_to_UART*", '*PX4*', '*FMU*']
connections.append(str(mavutil.auto_detect_serial(preferred_list)[0]))
for connection in connections:
    try:
        vehicle = connect(connection, wait_ready=True)
        print("Connection to {} succeeded".format(connection))
        break
    except Exception as e:
        print("Connection to {} failed".format(connection))
else:
     logging.error("Could not connect to Pixhawk")

# --------------------- Load mission --------------------------

# @vehicle.on_message('*')
@vehicle.on_message('MISSION_ITEM_REACHED')
def on_waypoint(self, name, message):
    # if not name in ('VIBRATION', 'EKF_STATUS_REPORT', 'ATTITUDE', 'SYSTEM_TIME', 'TERRAIN_REPORT', 'BATTERY_STATUS', 'HWSTATUS', 'AHRS', 'VFR_HUD', 'RC_CHANNELS', 'GLOBAL_POSITION_INT', 'NAV_CONTROLLER_OUTPUT', 'POWER_STATUS', 'MEMINFO', 'GPS_RAW_INT', 'SYS_STATUS', 'HEARTBEAT', 'SCALED_IMU', 'SCALED_PRESSURE', 'RAW_IMU', 'SIMSTATE', 'AHRS2', 'AHRS3', 'RC_CHANNELS_RAW', 'SCALED_IMU2', 'LOCAL_POSITION_NED', 'SERVO_OUTPUT_RAW', 'MISSION_CURRENT', 'SENSOR_OFFSETS', 'MISSION_ITEM'):
        # print "*****", name, ":", message
    print("Reached waypoint #{}. Taking a measurement".format(message.seq - 1))
    log_test.measure('waypoint_{}.dat'.format(message.seq - 1)).run()

    # if message.seq == self.commands.count:
    #     logging.info("Mission complete, returning to land")
    #     vehicle.mode = VehicleMode('RTL')
    #     vehicle.close()
    #     sys.exit()

print("Starting mission")

altitude = .5

vehicle.mode = VehicleMode("GUIDED")
vehicle.commands.clear()
print("Building mission at altitude {}".format(altitude))
# ArduCopter burns the first command for whatever reason - https://discuss.dronekit.io/t/solved-dronekit-plane-takeoff/966/2
# add takeoff command
vehicle.commands.add(goto_absolute_nea(0, 0, 0))
vehicle.commands.add(takeoff(altitude))
with open('mission.txt') as commands:
    for lat, lon in (latlon.split(' ') for latlon in commands):
        vehicle.commands.add(goto_absolute_nea(float(lat), float(lon), altitude))
        vehicle.commands.add(delay(10))


vehicle.commands.upload()

print "there are {} commands".format(vehicle.commands.count)
print "Basic pre-arm checks"
# Don't let the user try to arm until autopilot is ready
while not vehicle.is_armable:
    print " Waiting for vehicle to initialise..."
    time.sleep(1)

vehicle.armed = True

while not vehicle.armed:
    print "waiting for vehicle to arm"
    time.sleep(1)

# initiating takeoff manually is necessary for simulator where we can't set throttle with a controller
vehicle.simple_takeoff(.5)
vehicle.mode = VehicleMode("AUTO")

vehicle.commands.next = 0

while True:
    time.sleep(1)
