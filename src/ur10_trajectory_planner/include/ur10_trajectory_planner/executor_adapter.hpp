#pragma once

#include "ur10_trajectory_planner/types.hpp"

namespace ur10_trajectory_planner {

class ExecutorAdapter {
public:
  PlaceholderType execute() const;
};

}  // namespace ur10_trajectory_planner
