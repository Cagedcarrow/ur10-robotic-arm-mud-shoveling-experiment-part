/* Software License Agreement (BSD License)
*
* Copyright (c) 2014, Robotiq, Inc.
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions
* are met:
*
* * Redistributions of source code must retain the above copyright
* notice, this list of conditions and the following disclaimer.
* * Redistributions in binary form must reproduce the above
* copyright notice, this list of conditions and the following
* disclaimer in the documentation and/or other materials provided
* with the distribution.
* * Neither the name of Robotiq, Inc. nor the names of its
* contributors may be used to endorse or promote products derived
* from this software without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
* "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
* LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
* FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
* COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
* INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
* BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
* CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
* LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
* ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
* POSSIBILITY OF SUCH DAMAGE.
*
* Copyright (c) 2014, Robotiq, Inc
*/

/*
 *  \file main.c
 *  \date June 18, 2014
 *  \author Jonathan Savoie <jonathan.savoie@robotic.com>
 *  \maintener Nicolas Lauzier <nicolas@robotiq.com>
 */

// ROS
#include "ros/ros.h"
#include "geometry_msgs/WrenchStamped.h"
#include "tf/transform_datatypes.h"
#include "tf/transform_broadcaster.h"

// STL
#include <thread>
#include <iostream>

// Robotiq's code
namespace rq {
    extern "C" {
        #include "rq_sensor_com.h"
        #include "rq_sensor_state.h"
        #include "rq_int.h"
        #include "rq_thread.h"
    }
}  // namespace rq

namespace rq {
    void wait_for_other_connection() {
        using namespace std::chrono_literals;
        rq::INT_8 ret;
        ROS_DEBUG_STREAM("waiting for connection\n");
        while (true) {
            std::this_thread::sleep_for(1s);
            ret = rq::rq_sensor_state();
            if (ret == 0) {
                break;
            }
        }
    }
}

void setup_robotiq() {
    //IF can't connect with the sensor wait for another connection
    rq::INT_8 ret = rq::rq_sensor_state();
    ROS_DEBUG_STREAM("first\n");
    if (ret == -1) {
        rq::wait_for_other_connection();
    }

    //Read high-level informations
    ret = rq::rq_sensor_state();
    ROS_DEBUG_STREAM("second\n");
    if (ret == -1) {
        rq::wait_for_other_connection();
    }

    //Initialize connection with the client
    ret = rq::rq_sensor_state();
    ROS_DEBUG_STREAM("third\n");
    if (ret == -1) {
        rq::wait_for_other_connection();
    }
}

int main(int argc, char** argv) {
    const std::string pub_topic_param = "/ftsensor_node_name";
    const std::string sensor_frame_id_param = "/ftsensor_frame";

    setup_robotiq();

    ros::init(argc, argv, "my_robotiq_ft");
    ros::NodeHandle ros_node;

    std::string node_name;
    std::string frame_id;
    const int queue_size = 10;

    if (!ros_node.getParam(pub_topic_param, node_name)) {
        ROS_ERROR_STREAM(pub_topic_param << " not found in parameter server!\n");
        return -1;
    }
    if (!ros_node.getParam(sensor_frame_id_param, frame_id)) {
        ROS_ERROR_STREAM(sensor_frame_id_param << " not found in parameter server!\n");
        return -1;
    }

    ros::Publisher sensor_pub = ros_node.advertise<geometry_msgs::WrenchStamped>(node_name, queue_size);

    ROS_DEBUG_STREAM("ready!\n");

    while (ros::ok()) {
        rq::INT_8 ret = rq::rq_sensor_state();
        if (ret == -1) {
            rq::wait_for_other_connection();
        }

        if (rq::rq_sensor_get_current_state() == rq::RQ_STATE_RUN) {
            geometry_msgs::WrenchStamped msg;
            msg.header.frame_id = frame_id;
            msg.header.stamp = ros::Time(0);

            msg.wrench.force.x  = rq::rq_state_get_received_data(0);
            msg.wrench.force.y  = rq::rq_state_get_received_data(1);
            msg.wrench.force.z  = rq::rq_state_get_received_data(2);
            msg.wrench.torque.x = rq::rq_state_get_received_data(3);
            msg.wrench.torque.y = rq::rq_state_get_received_data(4);
            msg.wrench.torque.z = rq::rq_state_get_received_data(5);

            sensor_pub.publish(msg);
            ros::spinOnce();
        }

        // ros::Duration(0.1).sleep();
    }
    return 0;
 }
