#!/usr/bin/env python

# Copyright (c) 2019 Computer Vision Center (CVC) at the Universitat Autonoma de
# Barcelona (UAB).
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

# Allows controlling a vehicle with a keyboard. For a simpler and more
# documented example, please take a look at tutorial.py.


from __future__ import print_function


# ==============================================================================
# -- find carla module ---------------------------------------------------------
# ==============================================================================


import glob
import os
import sys


try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass


# ==============================================================================
# -- imports -------------------------------------------------------------------
# ==============================================================================


import carla

from carla import ColorConverter as cc

import argparse
import math
import time
try:
    import numpy as np
except ImportError:
    raise RuntimeError('cannot import numpy, make sure numpy package is installed')

from scipy.spatial.transform import Rotation as R


from cyber_py import cyber, cyber_time
#from modules.localization.proto.localization_pb2 import LocalizationEstimate
from modules.canbus.proto.chassis_pb2 import Chassis
from modules.control.proto.control_cmd_pb2 import ControlCommand

# ==============================================================================
# ------- Cyber Nodes ----------------------------------------------------------
# ==============================================================================





class ApolloReader:

    def __init__(self,world):
        cyber.init()
        self.sim_world = world
        self.map = world.get_map()
        self.planned_trajectory = None
        self.player = self.sim_world.get_actors().filter('vehicle.lincoln.mkz*')[0]
        self.node = cyber.Node("carla_control_listener_node")
        self.control_reader = self.node.create_reader('/apollo/control', ControlCommand, self.control_callback)

    def control_callback (self,data):
        self.player.set_simulate_physics(True)

        ##################### get old vehicle control ###################
        old_control = self.player.get_control()

        #################################################################
        vehicle_control = carla.VehicleControl()
        vehicle_control.hand_brake = data.parking_brake
        vehicle_control.brake = data.brake / 100.0 #/2
        vehicle_control.steer = -1 * data.steering_target / 100.0 
        vehicle_control.throttle =  max(old_control.throttle - 0.01 , data.throttle / 100.0) 
        #vehicle_control.throttle = max(vehicle_control.throttle , 0.2)
        vehicle_control.reverse = data.gear_location == Chassis.GearPosition.GEAR_REVERSE
        #print("vehicle reverse: ", vehicle_control.reverse)
        vehicle_control.gear = 1 if vehicle_control.reverse else -1

        self.player.apply_control(vehicle_control)

            

# ==============================================================================
# -- main() --------------------------------------------------------------------
# ==============================================================================


def main():
    argparser = argparse.ArgumentParser(
        description='CARLA Manual Control Client')

    argparser.add_argument(
        '--host',
        metavar='H',
        default='172.17.0.1',
        help='IP of the host server (default: 172.17.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    
    args = argparser.parse_args()

    try:

        client = carla.Client(args.host, args.port)
        client.set_timeout(200.0)
        sim_world = client.get_world()
        sim_world.wait_for_tick(5.0)
        #vehicle = sim_world.get_actors().filter('vehicle.*')[0]
        #print("vehicles are ", vehicle)
        apollo_control_listener = ApolloReader(sim_world)
        print("Applying control commands ...")
        apollo_control_listener.node.spin()
        
    except KeyboardInterrupt:
        print('\nCancelled by user. Bye!')


if __name__ == '__main__':

    main()
