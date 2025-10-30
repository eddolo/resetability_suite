#include <rclcpp/rclcpp.hpp>
#include "so3_reset.hpp"
// TODO: add msgs; publish ResetReport & reset_cmd

class ResetEstimatorNode : public rclcpp::Node {
public:
  ResetEstimatorNode(): Node("reset_estimator_node") {
    // subs: /imu, /joint_states
    // pub: reset report, reset command sequence (axis-angle micro-steps)
  }
  // in callback: build sliding window of RotSample, call estimate_resetability(), publish if R<r_thresh
};

int main(int argc, char** argv){
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ResetEstimatorNode>());
  rclcpp::shutdown(); return 0;
}
