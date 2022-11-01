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
from modules.planning.proto.planning_pb2 import ADCTrajectory

# ==============================================================================
# ------- Cyber Nodes ----------------------------------------------------------
# ==============================================================================

first_call = True
old_theta = 0
old_x = 0
old_y = 0
old_relative_time = 0

def check_relative_position(x,y,theta,t):
    global old_theta 
    global old_x 
    global old_y 
    global old_relative_time

    if theta >= 0 and theta < 1.571 :
        if x > old_x and y > old_y:
            return True
    elif theta >= 1.571 and theta < 3.149 :
        if y > old_y and x < old_x :
            return True
    elif theta < 0 and theta > -1.571 :
        if x > old_x and y < old_y:
            return True
    elif theta <= -1.571 and theta > -3.149 :
        if y < old_y and x < old_x : 
            return True
    return False

class ApolloReader:

    def __init__(self,world):
        cyber.init()
        self.sim_world = world
        self.map = world.get_map()
        self.planned_trajectory = None
        self.player = self.sim_world.get_actors().filter('vehicle.lincoln.mkz*')[0]
        self.node = cyber.Node("carla_planning_listener_node")
        self.planning_reader = self.node.create_reader('/apollo/planning', ADCTrajectory, self.planning_callback)


    def planning_callback(self, msg):
        global first_call 
        global old_theta 
        global old_x 
        global old_y 
        global old_relative_time 
        
        self.planned_trajectory = ADCTrajectory()
        self.planned_trajectory.CopyFrom(msg)
        #print("message received.")
        self.player.set_simulate_physics(False)
        
        old_trans = self.player.get_transform()
        old_loc = old_trans.location
        old_rot = old_trans.rotation
        
        dx_nearest_to_vehicle = self.planned_trajectory.trajectory_point[0].path_point.x - old_loc.x 
        dy_nearest_to_vehicle = self.planned_trajectory.trajectory_point[0].path_point.y - (-old_loc.y)
        nearest_dist = math.sqrt(dx_nearest_to_vehicle * dx_nearest_to_vehicle + dy_nearest_to_vehicle * dy_nearest_to_vehicle)
        nearest_idx = 0

        i=0
        for tp in self.planned_trajectory.trajectory_point:
            dx_current_to_vehicle = self.planned_trajectory.trajectory_point[i].path_point.x - old_loc.x 
            dy_current_to_vehicle = self.planned_trajectory.trajectory_point[i].path_point.y - (-old_loc.y)
            current_dist_to_vehicle = math.sqrt(dx_current_to_vehicle * dx_current_to_vehicle 
                                  + dy_current_to_vehicle * dy_current_to_vehicle)
            if current_dist_to_vehicle < nearest_dist :
                nearest_dist = current_dist_to_vehicle
                nearest_idx = i
        
            i+=1
        
        nearest_r_time = self.planned_trajectory.trajectory_point[nearest_idx+1].relative_time
        nearest_point = self.planned_trajectory.trajectory_point[nearest_idx+1].path_point
        print("nearest idx: ",nearest_idx , " , nearest t : ", nearest_r_time )
        new_loc = carla.Location(x=nearest_point.x,y=-nearest_point.y,z=old_loc.z)
        new_rot = old_rot
        #print("yaw in carla: ", new_rot.yaw, " theta in apollo: ",current_point.theta)
        new_rot.yaw = - math.degrees(nearest_point.theta)
        transf = carla.Transform(new_loc,new_rot)
        self.player.set_transform(transf)

        """
        counter = 0
        for tp in self.planned_trajectory.trajectory_point:
            #print(tp.relative_time)
            current_point = tp.path_point
            if first_call :
                first_call = False
                old_theta = current_point.theta
                old_x = current_point.x
                old_y = current_point.y
                old_relative_time =  tp.relative_time
            if  tp.relative_time > -0.01 and check_relative_position(current_point.x,current_point.y,current_point.theta, tp.relative_time) :
                counter +=1
                if counter < 2:
                    #old_point = tp.path_point
                    continue
                else:
                    
                    #print ("current x : ",tp.path_point.x,"current y : ", -tp.path_point.y, "current z : ",tp.path_point.z)

                    
                    
                    new_loc = carla.Location(x=current_point.x,y=-current_point.y,z=old_loc.z)
                    new_rot = old_rot
                    #print("yaw in carla: ", new_rot.yaw, " theta in apollo: ",current_point.theta)
                    new_rot.yaw = - math.degrees(current_point.theta)
                    transf = carla.Transform(new_loc,new_rot)
                    self.player.set_transform(transf)

                    first_call = False
                    old_theta = current_point.theta
                    old_x = current_point.x
                    old_y = current_point.y
                    old_relative_time =  tp.relative_time
                    print("First trajectory call")
                    break
        
           # else:
                if check_relative_position(current_point.x,current_point.y,current_point.theta, tp.relative_time):
                    old_trans = self.player.get_transform()
                    old_loc = old_trans.location
                    old_rot = old_trans.rotation
                    
                    new_loc = carla.Location(x=current_point.x,y=-current_point.y,z=old_loc.z)
                    new_rot = old_rot
                    #print("yaw in carla: ", new_rot.yaw, " theta in apollo: ",current_point.theta)
                    new_rot.yaw = - math.degrees(current_point.theta)
                    transf = carla.Transform(new_loc,new_rot)
                    self.player.set_transform(transf)

                    #first_call = False
                    old_theta = current_point.theta
                    old_x = current_point.x
                    old_y = current_point.y
                    old_relative_time =  tp.relative_time
                    break
        """    
        #print("old x , y , t : " , old_x," , ", old_y , " , ", old_relative_time)
       # print(self.planned_trajectory.trajectory_point[0])


    
            

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
        apollo_planning_listener = ApolloReader(sim_world)
        print("Applying planned trajectory ...")
        apollo_planning_listener.node.spin()

    except KeyboardInterrupt:
        print('\nCancelled by user. Bye!')


if __name__ == '__main__':

    main()
