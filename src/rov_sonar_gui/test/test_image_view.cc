// SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>

#include "../src/ImageView.hh"

namespace
{
gz::msgs::Image Make(gz::msgs::PixelFormatType format, int depth, std::string data, int step = 0)
{
  gz::msgs::Image message;
  message.set_width(2);
  message.set_height(1);
  message.set_step(step ? step : 2 * depth);
  message.set_pixel_format_type(format);
  message.set_data(std::move(data));
  return message;
}
}  // namespace

TEST(ImageView, RgbAndBgr)
{
  const std::string pixels("\x10\x20\x30\x40\x50\x60", 6);
  auto rgb = rov_sonar::ImageView::Convert(Make(gz::msgs::PixelFormatType::RGB_INT8, 3, pixels));
  ASSERT_FALSE(rgb.isNull());
  EXPECT_EQ(rgb.pixel(0, 0), qRgb(0x10, 0x20, 0x30));
  auto bgr = rov_sonar::ImageView::Convert(Make(gz::msgs::PixelFormatType::BGR_INT8, 3, pixels));
  EXPECT_EQ(bgr.pixel(1, 0), qRgb(0x60, 0x50, 0x40));
}

TEST(ImageView, PaddedRowsAndGray)
{
  auto gray = rov_sonar::ImageView::Convert(
    Make(gz::msgs::PixelFormatType::L_INT8, 1, std::string("\x80\xff\x00\x00", 4), 4));
  ASSERT_FALSE(gray.isNull());
  EXPECT_EQ(qGray(gray.pixel(1, 0)), 0xff);
}

TEST(ImageView, RejectsShortOrUnsupportedData)
{
  EXPECT_TRUE(rov_sonar::ImageView::Convert(
    Make(gz::msgs::PixelFormatType::RGB_INT8, 3, std::string(5, '\0'))).isNull());
  EXPECT_TRUE(rov_sonar::ImageView::Convert(
    Make(gz::msgs::PixelFormatType::R_FLOAT32, 4, std::string(8, '\0'))).isNull());
}
