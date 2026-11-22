// The Ogre 1 display uses the water model's ordinary mesh and material.
// Only the GUI loads this replacement; the server retains Wave Sim.
#include <gz/plugin/Register.hh>
#include <gz/sim/System.hh>

namespace posim::parallels
{
class StaticWater final : public gz::sim::System, public gz::sim::ISystemConfigure
{
public:
  void Configure(const gz::sim::Entity &, const std::shared_ptr<const sdf::Element> &,
                 gz::sim::EntityComponentManager &, gz::sim::EventManager &) override
  {
  }
};
}

GZ_ADD_PLUGIN(posim::parallels::StaticWater, gz::sim::System, gz::sim::ISystemConfigure)
GZ_ADD_PLUGIN_ALIAS(posim::parallels::StaticWater, "gz::sim::systems::WavesVisual")
