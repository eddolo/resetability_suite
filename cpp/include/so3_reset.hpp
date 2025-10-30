// cpp/include/so3_reset.hpp
#pragma once
#include <Eigen/Core>
#include <Eigen/Geometry>
#include <vector>
#include <cmath>

namespace so3reset {

struct RotSample { Eigen::Vector3d axis; double angle; double dt; };
struct ResetReport { double lambda; double R; double theta_net; int N; };

inline Eigen::Quaterniond axang_to_quat(const Eigen::Vector3d& n, double th){
  double s = std::sin(th/2.0), c = std::cos(th/2.0);
  Eigen::Vector3d nh = n.normalized();
  return Eigen::Quaterniond(c, s*nh.x(), s*nh.y(), s*nh.z());
}
inline std::pair<Eigen::Vector3d,double> quat_to_axang(const Eigen::Quaterniond& qin){
  Eigen::Quaterniond q = qin.normalized();
  double w = std::clamp(q.w(), -1.0, 1.0);
  double th = 2.0*std::acos(w);
  if (th < 1e-12) return {Eigen::Vector3d::UnitX(), 0.0};
  double s = std::sqrt(std::max(1.0 - w*w, 1e-12));
  return { Eigen::Vector3d(q.x()/s, q.y()/s, q.z()/s), th };
}
inline Eigen::Quaterniond compose_seq(const std::vector<RotSample>& seq){
  Eigen::Quaterniond q(1,0,0,0);
  for (auto& s: seq) q = axang_to_quat(s.axis, s.angle) * q;
  return q.normalized();
}
inline ResetReport estimate_resetability(const std::vector<RotSample>& seq){
  auto qnet = compose_seq(seq);
  auto [_, th] = quat_to_axang(qnet);
  double lam = (th > 1e-12) ? M_PI/th : 1.0;
  std::vector<RotSample> scaled; scaled.reserve(seq.size());
  for (auto& s: seq) scaled.push_back({s.axis, lam*s.angle, s.dt});
  auto q1 = compose_seq(scaled);
  Eigen::Quaterniond qreset = q1*q1; // apply twice
  double R = 1.0 - std::abs(std::clamp(qreset.w(), -1.0, 1.0)); // corrected
  return {lam, R, th, (int)seq.size()};
}
inline Eigen::Quaterniond apply_scaled_twice(const std::vector<RotSample>& seq, double lam){
  std::vector<RotSample> scaled; scaled.reserve(2*seq.size());
  for (auto& s: seq) scaled.push_back({s.axis, lam*s.angle, s.dt});
  for (auto& s: seq) scaled.push_back({s.axis, lam*s.angle, s.dt});
  return compose_seq(scaled);
}

} // namespace so3reset
