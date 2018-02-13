cmake_minimum_required(VERSION 2.8.3)
project(piksi_multi_rtk_gps)

find_package(catkin_simple REQUIRED)
catkin_simple(ALL_DEPS_REQUIRED)

install(PROGRAMS
  src/piksi_multi.py
  src/UdpHelpers.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(
  DIRECTORY launch/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
  )

install(
  DIRECTORY cfg/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/cfg
  )

cs_export()
