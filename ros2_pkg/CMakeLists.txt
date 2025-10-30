cmake_minimum_required(VERSION 3.8)
project(ros2_pkg)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(Eigen3 REQUIRED) # For the C++ math library

# Include your custom so3_reset.hpp library
include_directories(
  ${CMAKE_CURRENT_SOURCE_DIR}/../cpp/include
)

# Define the executable node
add_executable(reset_estimator_node src/reset_estimator_node.cpp)

# Link dependencies
ament_target_dependencies(reset_estimator_node
  "rclcpp"
  "Eigen3"
)

# Install rules
install(TARGETS
  reset_estimator_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()