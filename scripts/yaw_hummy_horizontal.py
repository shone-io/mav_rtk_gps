#!/usr/bin/env python

#
#  Title:        yaw_hummy_horizontal.py
#  Description:  ROS module to calculate yaw angle from magnetometer data, when the MAV is placed
#                horizontally, i.e. WITH pitch == roll == 0 (or at leaset very small)
#

import rospy
import tf.transformations as tf
from std_msgs.msg import Float64
from geometry_msgs.msg import Pose, Vector3Stamped, Quaternion
from rovio.srv import SrvResetToPose
import numpy as np
import math

def magnetic_field_callback(magMsg):

    global num_magnetometer_reads
    global number_samples_average
    global array_yaw

    # Correct magnetic filed
    raw_mag = np.array([magMsg.vector.x,
                        magMsg.vector.y,
                        magMsg.vector.z])

    # corrected_mag = compensation * (raw_mag - offset)
    corrected_mag = np.dot(mag_compensation, raw_mag - mag_offset)

    # compute yaw angle using corrected magnetometer measurements
    # and ASSUMING ZERO pitch and roll of the magnetic sensor!
    # adapted from
    # https://github.com/KristofRobot/razor_imu_9dof/blob/indigo-devel/src/Razor_AHRS/Compass.ino
    corrected_mag = corrected_mag / np.linalg.norm(corrected_mag)
    mag_yaw = math.atan2(corrected_mag[1], -corrected_mag[0]);

    # add declination
    mag_yaw = mag_yaw + mag_declination

    # publish unfiltered yaw
    pub_yaw_raw.publish(Float64(math.degrees(mag_yaw)))  

    # compute mean 
    array_yaw[num_magnetometer_reads] = mag_yaw
    num_magnetometer_reads += 1

    if num_magnetometer_reads >= number_samples_average:
        num_magnetometer_reads = 0 # delte oldest samples

    yaw_avg = mitsuta_mean(array_yaw)

    # WARNING: we assume zero roll and zero pitch!
    q_avg = tf.quaternion_from_euler(0.0, 0.0, yaw_avg);
    q_msg = Quaternion()
    q_msg.w = q_avg[3]
    q_msg.x = q_avg[0]
    q_msg.y = q_avg[1]
    q_msg.z = q_avg[2]

    pub_yaw_avg.publish(Float64(math.degrees(yaw_avg)))
    pub_q_avg.publish(q_msg)

    # debug
    if print_debug:
        rospy.loginfo(rospy.get_name() + " yaw_avg (deg): " +
                      str(math.degrees(yaw_avg)))
    
        


# Mitsuta mean used to average angles. This is necessary in order to avoid
# misleading behaviours. For example, if the measurements are swtiching between 
# -180 and +180 (they are the same angle, just with differente representation)
# then a normal mean algorithm would give you 0, which is completely wrong.
# Code adapted from:
# https://github.com/SodaqMoja/Mitsuta/blob/master/mitsuta.py
def mitsuta_mean(angles_array):
    # Function meant to work with degress, covert inputs
    # from radiants to degrees and output from degrees to radiants
    D = math.degrees(angles_array[0])
    mysum = D
    for val in angles_array[1:]:
        val = math.degrees(val)
        delta = val - D
        if delta < -180:
            D = D + delta + 360
        elif delta < 180:
            D = D + delta
        else:
            D = D + delta - 360
        mysum = mysum + D
    m = mysum / len(angles_array)

    avg = math.radians((m + 360) % 360)
    # make sure avg is between -pi and pi
    if avg > math.pi:
        avg = avg - 2 * math.pi
    elif avg < -math.pi:
        avg = avg + 2 * math.pi

    return avg



if __name__ == '__main__':

    rospy.init_node('yaw_hummy_horizontal')
    rospy.loginfo(rospy.get_name() + " start")
    
    # Read Settings
    # Magnetometer
    if not rospy.has_param('~magnetometer/declination'):
        declination = 0.0
    else:
        declination = rospy.get_param('~magnetometer/declination')

    if not rospy.has_param('~magnetometer/declination'):
        mag_declination = 0.0
    else:
        mag_declination = rospy.get_param('~magnetometer/declination')

    if not rospy.has_param('~magnetometer/offset'):
        mag_offset = np.array([0.0, 0.0, 0.0])
    else:
        mag_offset = np.array(rospy.get_param('~magnetometer/offset'))
        if mag_offset.size != 3:
            rospy.logerr("param 'magnetometer/offset' must be an array with 3 elements.")
            mag_offset = np.array([0.0, 0.0, 0.0])

    if not rospy.has_param('~magnetometer/compensation'):
        mag_compensation = np.array([0.0, 0.0, 0.0],
                                    [0.0, 0.0, 0.0],
                                    [0.0, 0.0, 0.0])
    else:
        mag_compensation = np.array(rospy.get_param('~magnetometer/compensation'))
        if mag_compensation.size != 9:
            rospy.logerr("param 'magnetometer/compensation' must be an array with 9 elements")
            mag_compensation = np.array([0.0, 0.0, 0.0],
                                        [0.0, 0.0, 0.0],
                                        [0.0, 0.0, 0.0])
        else:
            # create matrix from array
            mag_compensation = mag_compensation.reshape(3,3)

    # Other Settings
    if not rospy.has_param('~number_samples_average'):
        number_samples_average = 10
    else:
        number_samples_average = rospy.get_param('~number_samples_average')

    num_magnetometer_reads = 0
    array_yaw = np.zeros(shape = (number_samples_average,1)) 


    # Debug
    if not rospy.has_param('~print_debug'):
        print_debug = False
    else:
        print_debug = rospy.get_param('~print_debug')

    if print_debug:
        rospy.loginfo(rospy.get_name() +
                      " magnetometer declination: " + str(declination))
        rospy.loginfo(rospy.get_name() +
                      " magnetometer offset: " + str(mag_offset))
        rospy.loginfo(rospy.get_name() +
                      " magnetometer compensation: \n" + str(mag_compensation))

    # Subscribe to magnetometer topic
    rospy.Subscriber("magnetic_field", Vector3Stamped, magnetic_field_callback)

    # Publishers
    pub_yaw_raw = rospy.Publisher(rospy.get_name() + '/yaw_raw', Float64, queue_size = 10)
    pub_yaw_avg = rospy.Publisher(rospy.get_name() + '/yaw_avg', Float64, queue_size = 10)
    pub_q_avg = rospy.Publisher(rospy.get_name() + '/q_avg', Quaternion, queue_size = 10)

    # Spin
    rospy.spin()



