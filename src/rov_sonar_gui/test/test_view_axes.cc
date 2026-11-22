// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>

#include <cmath>

#include "../src/ViewAxes.hh"

namespace
{
QVariantMap Axis(const QVariantList & axes, const QString & label)
{
  for (const auto & entry : axes)
  {
    if (entry.toMap()["label"] == label)
    {
      return entry.toMap();
    }
  }
  return {};
}
}  // namespace

// Camera at the default orientation looks along world +X: X points away from
// the viewer, Y to the screen's left, Z up.
TEST(ViewAxes, IdentityCamera)
{
  const auto axes = rov_sonar::ViewAxes::Project(gz::math::Quaterniond::Identity);
  ASSERT_EQ(axes.size(), 3);
  EXPECT_EQ(axes.front().toMap()["label"], "X");  // Farthest is drawn first.
  EXPECT_NEAR(Axis(axes, "X")["depth"].toDouble(), 1, 1e-9);
  EXPECT_NEAR(Axis(axes, "Y")["x"].toDouble(), -1, 1e-9);
  EXPECT_NEAR(Axis(axes, "Z")["y"].toDouble(), -1, 1e-9);
}

// Looking straight down (pitch +90 degrees): Z points at the viewer and X up.
TEST(ViewAxes, TopDownCamera)
{
  const auto axes = rov_sonar::ViewAxes::Project(gz::math::Quaterniond(0, M_PI / 2, 0));
  EXPECT_NEAR(Axis(axes, "Z")["depth"].toDouble(), -1, 1e-9);
  EXPECT_EQ(axes.back().toMap()["label"], "Z");
  EXPECT_NEAR(Axis(axes, "X")["y"].toDouble(), -1, 1e-9);
  EXPECT_NEAR(Axis(axes, "Y")["x"].toDouble(), -1, 1e-9);
}
